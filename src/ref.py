import os

class Ref:
    """Represents a ref."""
    
    def __init__(self, repo, path):
        self.repo = repo
        self.path = path
        
    def read_hash(self):
        if os.path.exists(self.path):
          with open(self.path, 'r') as f:
            return f.read().strip()
        return None

    def update(self, new_hash):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w') as f:
            f.write(new_hash)
            
    @classmethod
    def from_symbol(cls, repo, symbol):
        symbol_path = os.path.join(repo.bit_dir, symbol)
        
        if not os.path.exists(symbol_path):
            raise FileNotFoundError
        
        with open(symbol_path, 'r') as f:
            direct_path_str = f.read().strip().split(" ", 1)[1]
            
        return Ref(repo, os.path.join(repo.bit_dir, direct_path_str))