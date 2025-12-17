import sys
from .base import BaseCommand

class InitCommand(BaseCommand):
    def run(self):
        try:
            self.repo.init()
            print(self.repo.worktree.list_files())
            print(f"Initialized empty Bit repository in {self.repo.bit_dir}")
        except FileExistsError:
            sys.stderr.write(f"Error: Bit repository already exists in {self.repo.bit_dir}.\n")
        except PermissionError:
             sys.stderr.write(f"Error: Permission denied to create repository in {self.repo.worktree.path}.\n")
