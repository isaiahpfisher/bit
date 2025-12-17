import sys
from .base import BaseCommand

class RestoreCommand(BaseCommand):
    def run(self):
        if not self._check_repo_exists():
            return

        if len(self.args) < 1:
            sys.stderr.write("Usage: bit restore [--staged] <file1> [<file2> ...]\n")
            return

        is_staged = False
        paths = self.args[:]

        if "--staged" in paths:
            is_staged = True
            paths.remove("--staged")
            
        if not paths:
            sys.stderr.write("Error: you must specify at least one file to restore.\n")
            return

        try:
            self.repo.restore(paths, staged=is_staged)
        except FileNotFoundError as e:
            sys.stderr.write(f"Error: {e}\n")