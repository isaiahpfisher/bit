import sys
from .base import BaseCommand

class StatusCommand(BaseCommand):
    def run(self):
        if not self._check_repo_exists():
            return
        
        status = self.repo.status()
        print(status.format_output(self.repo.current_branch()))
