import sys
from .base import BaseCommand

class MergeCommand(BaseCommand):
    def run(self):     
        if len(self.args) < 1:
            sys.stderr.write("Usage: bit merge <branch_name>\n")
            return
           
        if not self._check_repo_exists():
            return
        
        branch_name = self.args[0]

        self.repo.merge(branch_name)