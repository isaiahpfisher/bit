import sys
from .base import BaseCommand

class StatusCommand(BaseCommand):
    def run(self):
        if not self._check_repo_exists():
            return
        
        try:
            status = self.repo.status()
            print(status.format_output())
        except Exception as e:
            sys.stderr.write(f"Error getting status: {e}\n")
