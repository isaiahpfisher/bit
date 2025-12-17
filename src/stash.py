import os
from .ref import Ref
from .commit import Commit
from .tree import Tree
from .merge import Merge
from exceptions.merge_conflict import MergeConflict

class Stash:
    def __init__(self, repo):
        self.repo = repo
        self.stash_ref_path = os.path.join(repo.bit_dir, 'refs', 'stash')
        self.stash_ref = Ref(repo, self.stash_ref_path)

    def push(self, message=None):
        """
        Snapshots the worktree and index, then resets to a clean HEAD.
        """
        status = self.repo.status()
        if status.is_clean():
            raise Exception("No local changes to save")

        original_index = self.repo.index.load_as_dict()
        self.repo.add_all()
        worktree_tree = Tree.build_from_index(self.repo.index, self.repo.db)
        
        head_hash = Ref.from_symbol(self.repo, 'HEAD').read_hash()
        prev_stash = self.stash_ref.read_hash()
        
        parent_hashes = [head_hash]
        if prev_stash:
            parent_hashes.append(prev_stash)
            
        msg = message if message else f"WIP on {self.repo.current_branch()}"
        stash_commit = Commit(worktree_tree.hash, parent_hashes, msg)
        stash_hash = self.repo.db.store(stash_commit.serialize())
        
        self.stash_ref.update(stash_hash)
        
        self.repo.index.write(original_index)
        self.repo.reset(head_hash, mode="--hard")
        
        return stash_hash

    def pop(self):
        """
        Applies the most recent stash and removes it from the stack.
        """
        stash_hash = self.stash_ref.read_hash()
        if not stash_hash:
            raise Exception("No stash found.")
        
        status = self.repo.status()
        if not status.is_clean():
            raise Exception(f"Please stash or commit your current changes before popping the stash.")
            
        stash_commit = Commit.parse(self.repo.db.read(stash_hash))
        head_ref = Ref.from_symbol(self.repo, "HEAD")
        other_ref = Ref(self.repo, self.stash_ref_path)
        merge_engine = Merge(self.repo, head_ref, other_ref)
        
        # Override the base for the merge to be the commit we stashed
        merge_engine.base_hash = stash_commit.parent_hashes[0]
        
        modify_conflicts, delete_conflicts = merge_engine.get_conflicts()
        if modify_conflicts or delete_conflicts:
             raise MergeConflict(modify_conflicts, delete_conflicts)
        
        merge_engine.resolve_automatic_merge()
        
        # Remove the MERGE_HEAD created by resolve_automatic_merge
        merge_head_path = os.path.join(self.repo.bit_dir, 'MERGE_HEAD')
        if os.path.exists(merge_head_path):
            os.remove(merge_head_path)

        if len(stash_commit.parent_hashes) > 1:
            self.stash_ref.update(stash_commit.parent_hashes[1])
        else:
            if os.path.exists(self.stash_ref_path):
                os.remove(self.stash_ref_path)

    def list_all(self):
        """
        Traverses the stash stack and returns summaries.
        """
        stashes = []
        curr_hash = self.stash_ref.read_hash()
        
        index = 0
        while curr_hash:
            commit = Commit.parse(self.repo.db.read(curr_hash))
            stashes.append({
                "index": index,
                "hash": curr_hash,
                "message": commit.message
            })
            curr_hash = commit.parent_hashes[1] if len(commit.parent_hashes) > 1 else None
            index += 1
        return stashes