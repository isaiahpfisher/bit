import os
from .database import Database
from .index import Index
from.commit import Commit
from.ref import Ref
from.tree import Tree
from.worktree import Worktree

class Repository:
    """Represents a Bit repository."""
    
    def __init__(self, worktree_path):
        self.worktree = Worktree(worktree_path)
        self.bit_dir = os.path.join(worktree_path, '.bit')
        self.db = Database(os.path.join(self.bit_dir, 'objects'))
        self.index = Index(os.path.join(self.bit_dir, 'index'))

    def init(self):
        """Initialize a new repository."""
        
        os.makedirs(self.db.path)
        os.makedirs(os.path.join(self.bit_dir, 'refs', 'heads'))
        
        with open(os.path.join(self.bit_dir, "HEAD"), "w") as f:
            f.write("ref: refs/heads/master\n")
            
        self.index.clear()

    def add(self, file_path):
        """Add a file to the index."""
        normalized_path = self.worktree.normalize_path(file_path)
        content = self.worktree.read_file(normalized_path)
        file_hash = self.db.store(content)
        self.index.add(normalized_path, file_hash)

    def commit(self, message):
        """Create a new commit."""
        
        if self.index.is_empty():
            return None
        
        root_tree_hash = Tree.build_from_index(self.index, self.db).hash
        head_ref = Ref.from_symbol(self, 'HEAD')
        parent_hash = head_ref.read_hash()
        
        commit = Commit(root_tree_hash, parent_hash, message)
        commit_content = commit.serialize()
        commit_hash = self.db.store(commit_content)
        
        head_ref.update(commit_hash)
            
        self.index.clear()
        return commit_hash