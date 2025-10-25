from .formatter import Formatter

class Status:
    def __init__(self):
        self.staged = {}      # {path: 'added' | 'modified' | 'deleted'}
        self.unstaged = {}    # {path: 'modified' | 'deleted'}
        self.untracked = []   # [path]

    def is_clean(self):
        """Checks if there are any changes to report."""
        return not self.staged and not self.unstaged and not self.untracked

    def format_output(self):
        """Generates the user-friendly string for the console."""
        output = ["On branch master"] # TODO

        if self.is_clean():
            output.append("Nothing to commit, working tree clean")
            return "\n".join(output)

        if self.staged:
            output.append("\nChanges to be committed:")
            output.append("  (use \"bit restore --staged <file>...\" to unstage)") # TODO
            # Keep output order consistent
            for path, change_type in sorted(self.staged.items()):
                output.append(f"{Formatter.GREEN}\t{change_type}:   {path}{Formatter.RESET}")

        if self.unstaged:
            output.append("\nChanges not staged for commit:")
            output.append("  (use \"bit add <file>...\" to update what will be committed)")
            output.append("  (use \"bit restore <file>...\" to discard changes in working directory)") # TODO
            for path, change_type in sorted(self.unstaged.items()):
                output.append(f"{Formatter.RED}\t{change_type}:   {path}{Formatter.RESET}")

        if self.untracked:
            output.append("\nUntracked files:")
            output.append("  (use \"bit add <file>...\" to include in what will be committed)")
            for path in sorted(self.untracked):
                output.append(f"{Formatter.RED}\t{path}{Formatter.RESET}")
        
        if len(self.staged) == 0:
          output.append("\nNo changes added to commit (use \"bit add\")")
        
        output.append("")
        return "\n".join(output)