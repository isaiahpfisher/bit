import os

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
