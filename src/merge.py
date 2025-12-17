from collections import deque
from .commit import Commit
from .tree import Tree
from .ref import Ref
from .diff_calculator import DiffCalculator
from exceptions.merge_conflict import MergeConflict
import os

class Merge:
    
    def __init__(self, repo, head_ref: Ref, other_ref: Ref):
        self.repo = repo
        self.head_ref = head_ref
        self.other_ref = other_ref
        self.base_hash = self.find_common_ancestor()
        
    def attempt(self):
        head_hash = self.head_ref.read_hash()
        other_hash = self.other_ref.read_hash()

        if self.base_hash == other_hash:
            return "ALREADY_UP_TO_DATE"

        if self.base_hash == head_hash:
            self.fast_forward()
            return "FAST_FORWARD"

        modify_conflicts, delete_conflicts = self.get_conflicts()
        
        if modify_conflicts or delete_conflicts:
            raise MergeConflict(modify_conflicts, delete_conflicts)
            
        commit_hash = self.resolve_automatic_merge()
        return f"MERGE_SUCCESS:{commit_hash}"
            
    def fast_forward(self):
        self.head_ref.update(self.other_ref.read_hash())
        self.repo.checkout(self.head_ref.name, force=True)
        
    def resolve_automatic_merge(self):
      base_entries = Tree.get_entries_from_commit(self.repo.db, self.base_hash)
      head_entries = Tree.get_entries_from_commit(self.repo.db, self.head_ref.read_hash())
      other_entries = Tree.get_entries_from_commit(self.repo.db, self.other_ref.read_hash())
      
      all_paths = set(base_entries.keys()) | set(head_entries.keys()) | set(other_entries.keys())
      merged_entries = {}

      for path in all_paths:
          base = base_entries.get(path)
          head = head_entries.get(path)
          other = other_entries.get(path)

          if head == other:
              if head: merged_entries[path] = head
          elif base == head:
              if other: merged_entries[path] = other
          elif base == other:
              if head: merged_entries[path] = head

      self.repo.index.write(merged_entries)
      for path, hash_val in merged_entries.items():
          content = self.repo.db.read(hash_val)
          self.repo.worktree.write_file(path, content)
      
      for path in head_entries:
          if path not in merged_entries:
              self.repo.worktree.remove_file(path)

      # Record MERGE_HEAD so Repository.commit knows to add the second parent
      merge_head_path = os.path.join(self.repo.bit_dir, 'MERGE_HEAD')
      with open(merge_head_path, 'w') as f:
          f.write(self.other_ref.read_hash())
      
      merge_msg = f"Merge branch '{self.other_ref.name}'"
      return self.repo.commit(merge_msg)
        
    # ----- UTILS -----
    def find_common_ancestor(self):
        head_hash = self.head_ref.read_hash()
        other_hash = self.other_ref.read_hash()
        
        def parents_of(commit_hash):
            commit = Commit.parse(self.repo.db.read(commit_hash))
            return commit.parent_hashes or []

        # BFS backwards from head to get all reachable ancestors in DAG
        head_ancestors = set()
        queue = deque([head_hash])
        
        while queue:
            curr = queue.popleft()
            if curr in head_ancestors:
                continue
            head_ancestors.add(curr)
            queue.extend(parents_of(curr))

        # BFS from other until we hit something in head_ancestors
        queue = deque([other_hash])
        visited = set()

        while queue:
            curr = queue.popleft()
            if curr in head_ancestors:
                return curr
            if curr in visited:
                continue
            visited.add(curr)
            queue.extend(parents_of(curr))

        return None


    def get_conflicts(self):
        base_entries = Tree.get_entries_from_commit(self.repo.db, self.base_hash)
        head_entries = Tree.get_entries_from_commit(self.repo.db, self.head_ref.read_hash())
        other_entries = Tree.get_entries_from_commit(self.repo.db, self.other_ref.read_hash())
        
        all_paths = set(base_entries.keys()) | set(head_entries.keys()) | set(other_entries.keys())
        modify_conflicts = []
        delete_conflicts = []
        
        for path in sorted(all_paths):
            in_base = base_entries.get(path)
            in_head = head_entries.get(path)
            in_other = other_entries.get(path)
            
            # check for different changes in both branches
            if in_base and in_head and in_other and in_head != in_other:
                head_diff = DiffCalculator.calculate_file_vs_file(self.repo, path, in_base, in_head, n=0)
                other_diff = DiffCalculator.calculate_file_vs_file(self.repo, path, in_base, in_other, n=0)
                if head_diff.conflicts_with(other_diff):
                    modify_conflicts.append({ "head": head_diff, "other": other_diff })
            
            if (in_base and in_head and in_base != in_head and not in_other) or (in_base and in_other and in_other != in_head and not in_head):
                delete_conflicts.append({ "modified": self.head_ref.name if in_head else self.other_ref.name, "deleted": self.head_ref.name if not in_head else self.head_ref.name })
        
        return modify_conflicts, delete_conflicts