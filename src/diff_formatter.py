from .formatter import Formatter
from .file_diff import FileDiff

class DiffFormatter:
    """Formats the raw diff results into a user-readable string."""

    @staticmethod
    def format(diffs: list[FileDiff]):
        """
        Takes a list of file diffs (from DiffCalculator) and returns
        a single formatted string ready for printing.
        """
        output_parts = []
        for file_diff in diffs:
            header = file_diff.format_file_header()
            body = file_diff.format_diff_lines()
            
            output_parts.append(header)
            if body:
                output_parts.append(body)
                
        final_output = "\n".join(output_parts)
        return final_output + "\n" if final_output else ""