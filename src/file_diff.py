from .formatter import Formatter

class FileDiff:
    def __init__(self, path, status, lines, hash_a, hash_b):
        self.path = path
        self.status = status
        self.lines = lines
        self.hash_a = hash_a
        self.hash_b = hash_b
    
    def format_file_header(self):
        """Formats the header lines for the diff."""
        header_lines = []

        if self.status == 'added':
            from_file = "/dev/null"
            to_file = f"b/{self.path}"
            header_lines.append(f"{Formatter.BOLD}diff --git {from_file} {to_file}")
            header_lines.append(f"new file mode") 
            header_lines.append(f"--- {from_file}")
            header_lines.append(f"+++ {to_file}{Formatter.RESET}")
        elif self.status == 'deleted':
            from_file = f"a/{self.path}"
            to_file = "/dev/null"
            header_lines.append(f"{Formatter.BOLD}diff --git {from_file} {to_file}")
            header_lines.append(f"deleted file mode") 
            header_lines.append(f"--- {from_file}")
            header_lines.append(f"+++ {to_file}{Formatter.RESET}")
        elif self.status == 'modified':
            from_file = f"a/{self.path}"
            to_file = f"b/{self.path}"
            header_lines.append(f"{Formatter.BOLD}diff --git {from_file} {to_file}")
            if self.hash_a and self.hash_b:
                 header_lines.append(f"index {self.hash_a[:7]}..{self.hash_b[:7]}")
            header_lines.append(f"--- {from_file}")
            header_lines.append(f"+++ {to_file}{Formatter.RESET}")
            
        return "\n".join(header_lines)

    def format_diff_lines(self):
        """Formats the unified diff lines with appropriate colors."""
        if not self.lines:
            return ""
            
        formatted = []
        for line in self.lines:
            line_no_newline = line.rstrip('\n') 
            
            if line.startswith("@@"):
                formatted.append(f"{Formatter.CYAN}{line_no_newline}{Formatter.RESET}")
            elif line.startswith("+"):
                formatted.append(f"{Formatter.GREEN}{line_no_newline}{Formatter.RESET}")
            elif line.startswith("-"):
                formatted.append(f"{Formatter.RED}{line_no_newline}{Formatter.RESET}")
            else:
                formatted.append(line_no_newline) 
                
        return "\n".join(formatted)
