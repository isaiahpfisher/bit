import os
import hashlib

class Worktree:
    def __init__(self, path):
        self.path = path

    def normalize_path(self, user_path):
        """
        Normalizes a path to be OS-independent and use forward slashes
        """
        abs_user_path = os.path.abspath(os.path.join(self.path, user_path))
        relative_path = os.path.relpath(abs_user_path, self.path)
        return relative_path.replace(os.sep, '/')

    def read_file(self, path):
        """Reads a file from the worktree."""
        with open(os.path.join(self.path, path), 'rb') as f:
            return f.read()
    
    def write_file(self, path, content):
        """Writes to a file in the worktree."""
        full_path = os.path.join(self.path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
            
    def remove_file(self, path):
        print("Removing:", path)
    
    # ----- UTILS -----
        
    def list_files(self):
        """
        Recursively lists all files in the worktree, ignoring the .bit directory.
        Returns a list of normalized, relative paths.
        """
        files = []
        for root, dirs, filenames in os.walk(self.path):
            if '.bit' in dirs:
                dirs.remove('.bit')
            if '.git' in dirs:
                dirs.remove('.git') # TODO: .bitignore

            for filename in filenames:
                full_path = os.path.join(root, filename)
                files.append(self.normalize_path(full_path))
        return files
    
    def list_and_hash_files(self):
        """
        Recursively lists all files in the worktree, ignoring the .bit directory.
        Returns a dictionary of normalized, relative paths, along with their content hashes.
        """
        files = {}
        for root, dirs, filenames in os.walk(self.path):
            if '.bit' in dirs:
                dirs.remove('.bit')
            if '.git' in dirs:
                dirs.remove('.git') # TODO: .bitignore

            for filename in filenames:
                full_path = self.normalize_path(os.path.join(root, filename))
                content = self.read_file(full_path)
                hash = hashlib.sha1(content).hexdigest()
                files[full_path] = hash
        return files
