import os
from .database import Database
from .index import Index
from .commit import Commit
from .ref import Ref
from .tree import Tree
from .worktree import Worktree
from .status import Status

class Repository:
    """Represents a Bit repository."""
    
    def __init__(self, worktree_path):
        self.worktree = Worktree(worktree_path)
        self.bit_dir = os.path.join(worktree_path, '.bit')
        self.db = Database(os.path.join(self.bit_dir, 'objects'))
        self.index = Index(os.path.join(self.bit_dir, 'index'))

    def init(self):
        """Initialize a new repository. Raises FileExistsError if it already exists."""
        if os.path.exists(self.bit_dir):
            raise FileExistsError
        
        os.makedirs(self.db.path)
        os.makedirs(os.path.join(self.bit_dir, 'refs', 'heads'))
        with open(os.path.join(self.bit_dir, "HEAD"), "w") as f:
            f.write("ref: refs/heads/master\n")
        self.index.clear()
    
    def rm(self, path):
        """Stages a file deletion."""

        normalized_path = self.worktree.normalize_path(path)
        
        current_entries = self.index.load_as_dict()
        
        if normalized_path not in current_entries:
             raise FileNotFoundError()
        
        self.index.remove(normalized_path)
        
        full_path = os.path.join(self.worktree.path, path)
        if os.path.exists(full_path):
            os.remove(full_path)

    def add(self, paths):
        """
        Add one or more files to the index, creating a full snapshot.
        Returns the number of files actually staged (changed).
        """
        current_entries = self.index.load_as_dict()
        
        staged_count = 0
        for path in paths:
            full_path = os.path.join(self.worktree.path, path)
            normalized_path = self.worktree.normalize_path(path)
            
            if not os.path.exists(full_path):
                self.index.remove(normalized_path)
                if normalized_path in current_entries:
                  del current_entries[normalized_path]
                  staged_count += 1
                else:
                    raise FileNotFoundError()
            else:
              content = self.worktree.read_file(normalized_path)
              file_hash = self.db.store(content)
              
              if current_entries.get(normalized_path) != file_hash:
                  staged_count += 1
              
              current_entries[normalized_path] = file_hash

        self.index.write(current_entries)
        return staged_count

    def add_all(self):
        """
        "Syncs" the worktree to the index.
        Stages new files, modifications, and deletions.
        """
        
        worktree_paths = set(self.worktree.list_files())
        index_paths = set(self.index.load_as_dict().keys())
        
        all_paths_to_check = list(worktree_paths | index_paths)
        
        return self.add(all_paths_to_check)

    def commit(self, message):
        """Create a new commit. Returns the commit hash or None."""
        if self.index.is_empty():
            return None
        
        root_tree = Tree.build_from_index(self.index, self.db)
        
        head_ref = Ref.from_symbol(self, 'HEAD')
        parent_hash = head_ref.read_hash()
        
        commit = Commit(root_tree.hash, parent_hash, message)
        commit_content = commit.serialize()
        commit_hash = self.db.store(commit_content)
        
        head_ref.update(commit_hash)
            
        self._prepare_index()
        return commit_hash
    
    def status(self):
        """Compares HEAD, index, and worktree. Returns a Status object."""
        status = Status()
        
        
        last_commit_hash = Ref.from_symbol(self, 'HEAD').read_hash()
        head_entries = Tree.get_entries_from_commit(self.db, last_commit_hash)
        worktree_entries = self.worktree.list_and_hash_files()
        index_entries = self.index.load_as_dict()
        
        all_paths = set(head_entries.keys()) | set(index_entries.keys()) | set(worktree_entries.keys())
        
        if 'unique_file.txt' in all_paths:
            print("unique_file.txt" in index_entries)
            print("unique_file.txt" in head_entries)
        
        for path in sorted(all_paths):
            in_head = head_entries.get(path)
            in_index = index_entries.get(path)
            in_worktree = worktree_entries.get(path)

            # --- Compare Index to HEAD (Staged Changes) ---
            if in_index and in_index != in_head:
                if not in_head:
                    status.staged[path] = 'new file'
                else:
                    status.staged[path] = 'modified'
            elif not in_index and in_head:
                status.staged[path] = 'deleted'

            # --- Compare Worktree to Index (Unstaged Changes) ---
            if in_index and in_worktree and in_index != in_worktree:
                status.unstaged[path] = 'modified'
            elif in_index and not in_worktree:
                status.unstaged[path] = 'deleted'
            
            # --- Untracked Files ---
            if not in_index and not in_head and in_worktree:
                status.untracked.append(path)
                
        return status
                
    def _prepare_index(self):
        """Prepares the index for add and status."""
        if self.index.is_empty():
            head_ref = Ref.from_symbol(self, 'HEAD')
            head_hash = head_ref.read_hash() if head_ref else None
            current_entries = Tree.get_entries_from_commit(self.db, head_hash)
            self.index.write(current_entries)