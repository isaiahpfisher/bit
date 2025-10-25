from .base import BaseCommand
from pager import Pager 

class LogCommand(BaseCommand):
    def __init__(self, repo, args):
        super().__init__(repo, args)
        self.pager = Pager()

    def run(self):
        if not self._check_repo_exists():
            return

        logs = self.repo.log()
        
        if not logs:
            print("No commits yet.")
            return

        full_output = ""
        for log_entry in logs:
            full_output += log_entry.format() + '\n'
            
        self.pager.display(full_output)
