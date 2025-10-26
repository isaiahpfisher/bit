from .base import BaseCommand
from pager import Pager 

class BranchCommand(BaseCommand):
    def __init__(self, repo, args):
        super().__init__(repo, args)
        self.pager = Pager()
        
    def run(self):        
        if not self._check_repo_exists():
            return

        if len(self.args) == 0:
            for branch in self.repo.list_branches():
                self.pager.append_line(branch)
                
            self.pager.display()
        else:
            self.repo.branch(self.args[0])