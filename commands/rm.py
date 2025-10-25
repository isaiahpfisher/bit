import sys
from .base import BaseCommand

class RmCommand(BaseCommand):
    def run(self):
        if len(self.args) != 1:
            sys.stderr.write("Usage: bit rm <file>\n")
            return
            
        if not self._check_repo_exists():
            return

        file_path = self.args[0]
        
        try:
            self.repo.rm(file_path)
            print(f"File removed: {file_path}.")
        except FileNotFoundError as e:
             sys.stderr.write(f"Error: pathspec '{file_path}' did not match any files known to bit\n")
