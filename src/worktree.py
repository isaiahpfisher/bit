import os
import sys
import hashlib
import re

class Worktree:
    def __init__(self, path):
        self.path = path
        self.ignore_path = os.path.join(self.path, '.bitignore')

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
    
    def write_file(self, path, content_bytes):
        """Writes to a file in the worktree."""
        full_path = os.path.join(self.path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(content_bytes)
            
    def remove_file(self, path):
        """Removes a file and any newly empty parent directories up to the root."""
        full_path = os.path.join(self.path, path.replace('/', os.sep))
        parent_dir = os.path.dirname(full_path)
        
        if not os.path.exists(full_path):
            return
        
        try:
            os.remove(full_path)
            while parent_dir != self.path and os.path.exists(parent_dir):
                if not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
                    parent_dir = os.path.dirname(parent_dir)
                else:
                    break
        except FileNotFoundError:
             pass 
        except OSError as e:
            print(f"Warning: Could not remove file {full_path}: {e}", file=sys.stderr)
    
    # ----- UTILS -----
        
    def list_files(self):
        """
        Recursively lists all files in the worktree, respecting .bitignore.
        """
        files = []
        ignore_patterns = self.get_ignore_patterns()
        for root, dirs, filenames in os.walk(self.path):
            rel_root = self.normalize_path(root)
            if rel_root == ".":
                rel_root = ""
            
            if '.bit' in dirs:
                dirs.remove('.bit')
            if '.git' in dirs:
                dirs.remove('.git')

            dirs[:] = [d for d in dirs if not self.is_ignored(os.path.join(rel_root, d), ignore_patterns)]

            for filename in filenames:
                rel_path = os.path.join(rel_root, filename)
                
                if not self.is_ignored(rel_path, ignore_patterns):
                    files.append(rel_path)
        return files
    
    def list_and_hash_files(self):
      files = {}
      ignore_patterns = self.get_ignore_patterns()
      
      for root, dirs, filenames in os.walk(self.path):
          rel_root = self.normalize_path(root)
          if rel_root == ".":
              rel_root = ""
          
          if '.bit' in dirs:
              dirs.remove('.bit')

          dirs[:] = [d for d in dirs if not self.is_ignored(os.path.join(rel_root, d), ignore_patterns)]

          for filename in filenames:
              rel_path = os.path.join(rel_root, filename)
              
              if self.is_ignored(rel_path, ignore_patterns):
                  continue
                  
              content = self.read_file(rel_path)
              file_hash = hashlib.sha1(content).hexdigest()
              files[rel_path] = file_hash
              
      return files

    def get_ignore_patterns(self):
        """Returns a list of ignore rules for the current worktree."""
        regex_patterns = []
        
        if os.path.exists(self.ignore_path):
            with open(self.ignore_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        regex_patterns.append(self.compile_pattern(line))
        
        return regex_patterns

    def compile_pattern(self, pattern):
        """Converts a single .bitignore pattern into a regex."""
        is_dir_only = pattern.endswith('/')
        if is_dir_only:
            pattern = pattern[:-1]

        if pattern.startswith('/'):
            anchored = True
            pattern = pattern[1:]
        else:
            anchored = False

        regex = re.escape(pattern).replace(r'\*', '.*').replace(r'\?', '.')

        if anchored:
            regex = '^' + regex
        else:
            # Match start of path or after any directory separator
            regex = '(^|.*/)' + regex

        if is_dir_only:
            regex += '(/.*)?$'
        else:
            regex += '$'

        return re.compile(regex)

    def is_ignored(self, path, compiled_patterns):
        """Checks if a normalized path matches any of the compiled patterns."""
        return any(p.match(path) for p in compiled_patterns)