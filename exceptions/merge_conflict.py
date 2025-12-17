from src.formatter import Formatter
from src.diff_formatter import DiffFormatter


class MergeConflict(Exception):
    def __init__(self, modify_conflicts, delete_conflicts):
        self.modify_conflicts = modify_conflicts
        self.delete_conflicts = delete_conflicts
        
    def format_output(self):
        output = []
        
        output.append(f"Merge aborted due to conflicts. Please resolve the conflicts in the following files and try again:\n")
        
        output.append(f"{Formatter.RED}{Formatter.BOLD}Conflicts:{Formatter.RESET}")
        
        if self.modify_conflicts:
            for conflict in self.modify_conflicts:
                output.append(f"\t- {conflict['head'].path}")
                
        if self.delete_conflicts:
            for conflict in self.delete_conflicts:
                output.append(f"\t- {conflict['modified']}")
                
        return "\n".join(output)