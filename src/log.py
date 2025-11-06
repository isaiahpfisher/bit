from .formatter import Formatter

class Log:
    def __init__(self, hash, commit, head_ref, refs):
        self.hash = hash
        self.commit = commit
        self.head_ref = head_ref
        self.refs = refs
        
    def format(self):
        lines = []
        lines.append(f"{Formatter.YELLOW}commit {self.hash} {self._decorate()}{Formatter.RESET}")
        if len(self.commit.parent_hashes) > 1:
            print("Merge:", " ".join(self.commit.parent_hashes))
        lines.append(f"Author: {self.commit.author}")
        lines.append(f"Date: {Formatter.format_timestamp(self.commit.timestamp)}")
        lines.append(f"\n    {self.commit.message}\n")
        
        return "\n".join(lines)
    
    
    # ----- UTILS -----
    def _decorate(self):
        decorators = []
        separator = f"{Formatter.NORMAL_WEIGHT}{Formatter.YELLOW},{Formatter.BOLD}{Formatter.GREEN} "
    
        for ref in self.refs:
            if ref == self.head_ref.name:
                decorators.insert(0, f"{Formatter.BOLD}{Formatter.CYAN}HEAD -> {Formatter.GREEN}{self.head_ref.name}")
            else:
                decorators.append(f"{Formatter.BOLD}{Formatter.GREEN}{ref}")
                
        if self.refs:
            decoration = separator.join(decorators)
            return f"({decoration}{Formatter.NORMAL_WEIGHT}{Formatter.YELLOW})"
        else: 
            return ''
            