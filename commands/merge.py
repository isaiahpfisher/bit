import sys
import os
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
            self.repo.merge(branch_name)
        except MergeConflict as e:
            print(e.format_output())