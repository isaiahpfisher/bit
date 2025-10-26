import sys
from .base import BaseCommand

class CommitCommand(BaseCommand):
    def run(self):
        if len(self.args) < 2 or self.args[0] != '-m':
            sys.stderr.write("Usage: bit commit -m <message>\n")
            return
        
        if not self._check_repo_exists():
            return
        
        message = self.args[1]
        commit_hash = self.repo.commit(message)
        
        if commit_hash:
            print(f"[{self.repo.current_branch()} {commit_hash[:7]}] {message}") 
        else:
            print("Aborted: No changes staged for commit.")
