# commands/merge.py
import sys
from .base import BaseCommand
from exceptions.merge_conflict import MergeConflict

class MergeCommand(BaseCommand):
    def run(self):     
        if len(self.args) < 1:
            sys.stderr.write("Usage: bit merge <branch_name>\n")
            return
           
        if not self._check_repo_exists():
            return
        
        branch_name = self.args[0]

        try:
            result = self.repo.merge(branch_name)
            
            if result == "ALREADY_UP_TO_DATE":
                print("Already up to date.")
            elif result == "FAST_FORWARD":
                print("Updating via fast-forward...")
            elif result.startswith("MERGE_SUCCESS:"):
                commit_hash = result.split(":")[1]
                print(f"Merge made by the '3-way' strategy.")
                print(f"[{self.repo.current_branch()} {commit_hash[:7]}] Merge branch '{branch_name}'")
                
        except MergeConflict as e:
            print(e.format_output())