import sys
from .base import BaseCommand

class CheckoutCommand(BaseCommand):
    def run(self):     
        
        if len(self.args) < 1:
            sys.stderr.write("Usage: bit checkout <branch_name>\n")
            return
           
        if not self._check_repo_exists():
            return
        
        branch = self.args[0]
        
        self.repo.checkout(branch)