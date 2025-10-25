import sys
from .base import BaseCommand

class AddCommand(BaseCommand):
    def run(self):
        if len(self.args) < 1:
            sys.stderr.write("Usage: bit add <file1> [<file2> ...] | .\n")
            return
        
        if not self._check_repo_exists():
            return

        paths_to_add = self.args

        try:
            if paths_to_add == ['.']:
                staged_count = self.repo.add_all()
            else:
                staged_count = self.repo.add(paths_to_add)
        except FileNotFoundError as e:
            sys.stderr.write(f"Error: {e}\n")
            return
                
        if staged_count > 0:
            print(f"Staged {staged_count} file(s).")
        else:
            print("No changes to stage.")