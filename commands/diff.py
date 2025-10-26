from .base import BaseCommand
from src.diff_formatter import DiffFormatter
from pager import Pager 

class DiffCommand(BaseCommand):
    def __init__(self, repo, args):
        super().__init__(repo, args)
        self.pager = Pager()
        
    def run(self):
        if not self._check_repo_exists():
            return
        
        if len(self.args) > 0 and self.args[0] == '--staged':
            diffs = self.repo.diff_staged()
            self.pager.display(DiffFormatter.format(diffs))
        else:
            diffs = self.repo.diff()
            self.pager.display(DiffFormatter.format(diffs))
        
