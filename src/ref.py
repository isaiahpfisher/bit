import os

class Ref:
    """Represents a ref."""
    
    def __init__(self, repo, path):
        self.repo = repo
        self.path = path
        self.name = path.split('/')[-1]
        
    def read_hash(self):
        """Reads the hash from the ref file, returning None if it doesn't exist."""
        if os.path.exists(self.path):
          with open(self.path, 'r') as f:
            return f.read().strip()
        return None

    def update(self, new_hash):
        """Updates the ref file with a new hash."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w') as f:
            f.write(new_hash)
            
    @classmethod
    def from_symbol(cls, repo, symbol):
        """Creates a Ref object by resolving a symbolic ref like 'HEAD'."""
        symbol_path = os.path.join(repo.bit_dir, symbol)
        
        if not os.path.exists(symbol_path):
            return None 
        
        with open(symbol_path, 'r') as f:
            ref_content = f.read().strip()
        
        if ref_content.startswith("ref:"):
            direct_path_str = ref_content.split(" ", 1)[1]
            return Ref(repo, os.path.join(repo.bit_dir, direct_path_str))
        
        return Ref(repo, symbol_path)
    
    @classmethod
    def for_branch(cls, repo, branch, hash):
        """Creates a Ref object in refs/heads for the given branch."""
        path = os.path.join(repo.bit_dir, 'refs', 'heads', branch)
        
        if (os.path.exists(path)):
            raise FileExistsError("Branch already exists")
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(hash)
            
    @staticmethod
    def list_all(repo):
        refs_dir = os.path.join(repo.bit_dir, 'refs', 'heads')
        refs = []
        
        if os.path.isdir(refs_dir):
          for dir in os.listdir(refs_dir):
              refs.append(dir)
        else:
            raise FileNotFoundError
        
        return refs

    @classmethod
    def load_all_as_dict(cls, repo):
        refs_dir = os.path.join(repo.bit_dir, 'refs', 'heads')
        refs = {}
        
        if os.path.isdir(refs_dir):
          for dir in os.listdir(refs_dir):
              ref = Ref(repo, os.path.join(refs_dir, dir))
              refs[dir] = ref.read_hash()
        else:
            raise FileNotFoundError
        
        return refs