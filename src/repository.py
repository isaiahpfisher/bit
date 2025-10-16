import os
import time
from .database import Database
from .index import Index

class Repository:
    """Represents a Bit repository."""
    
    def __init__(self, worktree):
        self.worktree = worktree
        self.bit_dir = os.path.join(worktree, '.bit')
        self.db = Database(os.path.join(self.bit_dir, 'objects'))
        self.index = Index(os.path.join(self.bit_dir, 'index'))
        
    def init(self):
        """Initialize a new repository."""
        if os.path.exists(self.bit_dir):
            raise FileExistsError
        
        os.makedirs(self.db.path)
        os.makedirs(os.path.join(self.bit_dir, 'refs', 'heads'))
        
        with open(os.path.join(self.bit_dir, "HEAD"), "w") as f:
            f.write("ref: refs/heads/master\n")
            
        self.index.clear()
    
    def add(self, file_path):
        """Add a file to the index."""
        normalized_path = self._normalize_path(file_path)
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        file_hash = self.db.store(content)
        self.index.add(normalized_path, file_hash)
    
    def commit(self, message):
        """Create a new commit."""
        
        if self.index.is_empty():
            return None
        
        root_tree_hash = self._build_tree()
        parent_hash = self._get_parent_hash()
        
        timestamp = int(time.time())
        timezone = time.strftime('%z')
        author = f"Isaiah Fisher <isaiahpfisher@gmail.com> {timestamp} {timezone}"
        
        lines = [f"tree {root_tree_hash}"]
        if parent_hash:
            lines.append(f"parent {parent_hash}")
        lines.append(f"author {author}")
        lines.append(f"committer {author}")
        lines.append(f"\n{message}")
        
        commit_content = "\n".join(lines)
        commit_hash = self.db.store(commit_content)
        
        head_path = os.path.join(self.bit_dir, 'refs', 'heads', 'master')
        os.makedirs(os.path.dirname(head_path), exist_ok=True)
        
        with open(head_path, 'w') as f:
            f.write(commit_hash)
            
        self.index.clear()
        return commit_hash
        
    def _normalize_path(self, path):
        """Convert a path to be relative to the worktree root."""
        relative_path = os.path.relpath(os.path.abspath(path), self.worktree)
        return relative_path.replace(os.sep, '/')
    
    def _get_parent_hash(self):
        """Get the hash of the parent commit."""
        head_ref_path = os.path.join(self.bit_dir, 'refs', 'heads', 'master')
        if os.path.exists(head_ref_path):
            with open(head_ref_path, 'r') as f:
                return f.read().strip()
        return None

    def _build_tree(self):
        """Builds tree objects from the index and returns the root tree hash."""
        index_entries = self.index.load()
        file_structure = {}
        for entry in index_entries:
            path_components = entry['path'].split('/')
            current_level = file_structure
            for component in path_components[:-1]:
                current_level = current_level.setdefault(component, {})
            current_level[path_components[-1]] = {'type': 'blob', 'hash': entry['sha1']}
            
        return self._write_tree_objects(file_structure)
    
    def _write_tree_objects(self, tree_data):
      """Recursively writes tree objects."""
      entries = []
      for name, data in sorted(tree_data.items()):
          if 'type' in data and data['type'] == 'blob':
              entries.append(f"blob {data['hash']} {name}")
          else:
              subtree_hash = self._write_tree_objects(data)
              entries.append(f"tree {subtree_hash} {name}")
      
      tree_content = "\n".join(entries)
      print(tree_content)
      return self.db.store(tree_content)