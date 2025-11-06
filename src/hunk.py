import re

class Hunk:
    def __init__(self, file_diff, lines, old_start, old_count, new_start, new_count):
        self.file_diff = file_diff
        self.lines = lines
        self.old_start = old_start
        self.old_count = old_count
        self.new_start = new_start
        self.new_count = new_count
      
    @classmethod
    def parse_diff_lines(cls, file_diff, lines):
        header_pattern = r"""^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@"""
        header = lines[0]
        m = re.match(header_pattern, header)
        if not m:
            raise ValueError(f"Invalid hunk header: {header}")
        old_start = int(m.group(1))
        old_count = int(m.group(2)) if m.group(2) is not None else 1
        new_start = int(m.group(3))
        new_count = int(m.group(4)) if m.group(4) is not None else 1
        return cls(file_diff, lines, old_start, old_count, new_start, new_count)
        
    def conflits_with(self, other: 'Hunk'):
        if self.file_diff.path != other.file_diff.path:
            return False
        
        end_self = self.old_start + self.old_count - 1;
        end_other = other.old_start + other.old_count - 1;
        return not (end_self < other.old_start or end_other < self.old_start)
    