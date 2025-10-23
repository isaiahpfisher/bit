import os

class Index:
    """Manages the staging area (the index file)."""

    def __init__(self, path):
        self.path = path
        
    def load_as_list(self):
        """Load the index file into a list of file paths."""
        entries = []
        if os.path.exists(self.path) and os.path.getsize(self.path) > 0:
            with open(self.path, 'r', encoding='utf-8') as f:
                for line in f:
                    hash, path = line.strip().split(' ', 1)
                    entries.append(path)
        return entries

    def load_as_dict(self):
        """Load the index file into a dictionary of {path: hash}."""
        entries = {}
        if os.path.exists(self.path) and os.path.getsize(self.path) > 0:
            with open(self.path, 'r', encoding='utf-8') as f:
                for line in f:
                    hash, path = line.strip().split(' ', 1)
                    entries[path] = hash
        return entries
    
    def write(self, entries_dict):
        """Write a dictionary of {path: hash} to the index file."""
        # Convert dict to list format for sorting and writing
        entries_list = [{'path': p, 'hash': h} for p, h in entries_dict.items()]
        entries_list.sort(key=lambda e: e['path'])
        
        with open(self.path, 'w', encoding='utf-8') as f:
            for entry in entries_list:
                f.write(f"{entry['hash']} {entry['path']}\n")
    
    def remove(self, path):
        entries = self.load_as_dict()
        if path in entries:
            del entries[path]
            self.write(entries)
          
    def clear(self):
        """Clear the index file."""
        open(self.path, 'w').close()

    def is_empty(self):
        """Check if the index is empty."""
        if not os.path.exists(self.path):
            return True
        return os.path.getsize(self.path) == 0

