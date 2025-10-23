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
        full_path = os.path.join(self.worktree.path, path)
        if os.path.exists(full_path):
            os.remove(full_path)
            self.index.remove(self.worktree.normalize_path(full_path))
        else:
            raise FileNotFoundError

    def add(self, paths):
        """
        Add one or more files to the index, creating a full snapshot.
        Returns the number of files actually staged (changed).
        """
        self._prepare_index()
        current_entries = self.index.load_as_dict()
        
        staged_count = 0
        for path in paths:
            full_path = os.path.join(self.worktree.path, path)
            if not os.path.exists(full_path):
                self.index.remove(self.worktree.normalize_path(full_path))

            normalized_path = self.worktree.normalize_path(path)
            content = self.worktree.read_file(normalized_path)
            file_hash = self.db.store(content)
            
            if current_entries.get(normalized_path) != file_hash:
                staged_count += 1
            
            current_entries[normalized_path] = file_hash

        self.index.write(current_entries)
        return staged_count

    def add_all(self):
        """Stage all files in the worktree."""
        # return self.add(self.worktree.list_files())
        staged_count = 0
        worktree_paths = self.worktree.list_files()
        index_paths = self.index.load_as_list()
        
        new_files = list(set(worktree_paths) - set(index_paths))
        deleted_files = list(set(index_paths) - set(worktree_paths))
        potentially_modified_files = list(set(worktree_paths) & set(index_paths))
        
        staged_count += self.add(new_files)
        staged_count += self.add(potentially_modified_files)
        staged_count += len(deleted_files)
        
        for file in deleted_files:
            self.index.remove(file)
        
        return staged_count

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
            
        self.index.clear()
        return commit_hash
    
    def status(self):
        """Displays the status of the repository."""
        status = Status()
        self._prepare_index()
        
        last_commit_hash = Ref.from_symbol(self, 'HEAD').read_hash()
        head_entries = Tree.get_entries_from_commit(self.db, last_commit_hash) # files from last commit
        worktree_entries = self.worktree.list_and_hash_files() # actual working directory
        index_entries = self.index.load_as_dict() # staging area
        
        
        for file, hash in worktree_entries.items():
            if file not in index_entries:
                status.untracked.append(file)
        
        for file, hash in index_entries.items():
            if file in worktree_entries and hash != worktree_entries[file]:
                status.unstaged[file] = 'modified'
            elif file not in worktree_entries:
                status.unstaged[file] = 'deleted'
            elif file not in head_entries:
                status.staged[file] = 'added'
            elif file in head_entries and hash != head_entries[file]:
                status.staged[file] = 'modified'
        
        for file, hash in head_entries.items():
            if file not in index_entries:
                status.staged[file] = 'deleted'
                
        return status
                
    def _prepare_index(self):
        """Prepares the index for add and status."""
        if self.index.is_empty():
            head_ref = Ref.from_symbol(self, 'HEAD')
            head_hash = head_ref.read_hash() if head_ref else None
            current_entries = Tree.get_entries_from_commit(self.db, head_hash)
            self.index.write(current_entries)