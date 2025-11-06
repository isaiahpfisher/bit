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
            current_branch = self.repo.current_branch()
            for branch in self.repo.list_branches():
                if branch != current_branch:
                  self.pager.append_line(f"  {branch}")
                else:
                    self.pager.append_line(f"* {branch}")
                
            self.pager.display()
        else:
            self.repo.branch(self.args[0])