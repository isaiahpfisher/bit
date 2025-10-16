import os

class Index:
    """Manages the staging area (the index file)."""

    def __init__(self, path):
        self.path = path

    def load(self):
        """Load the index file into a list of dictionaries."""
        entries = []
        if os.path.exists(self.path) and os.path.getsize(self.path) > 0:
            with open(self.path, 'r', encoding='utf-8') as f:
                for line in f:
                    hash, path = line.strip().split(' ', 1)
                    entries.append({'path': path, 'hash': hash})
        return entries
    
    def add(self, path, hash):
        """Add or update an entry in the index."""
        entries = self.load()
        
        new_entries = [e for e in entries if e['path'] != path]
        new_entries.append({'path': path, 'hash': hash})
        new_entries.sort(key=lambda e: e['path'])
        self._write(new_entries)
        
        return len(new_entries) - len(entries)

    def clear(self):
        """Clear the index file."""
        open(self.path, 'w').close()

    def is_empty(self):
        """Check if the index is empty."""
        if not os.path.exists(self.path):
            return True
        return os.path.getsize(self.path) == 0

    def _write(self, entries):
        """Write a list of entries to the index file."""
        with open(self.path, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(f"{entry['hash']} {entry['path']}\n")
