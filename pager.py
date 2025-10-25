import os
import sys
import subprocess

class Pager:
    """Handles displaying text content through a pager like 'less'."""

    def __init__(self, use_pager=True):
        self.pager_command = self._find_pager()
        self.use_pager = use_pager
        self.content = []

    def _find_pager(self):
        """Determines the pager command to use."""
        pager_cmd = os.environ.get('PAGER', 'less').split()
        if 'less' in pager_cmd:
            # -R: Handle color codes
            # -F: Quit if content fits on one screen
            if '-R' not in pager_cmd: pager_cmd.append('-R')
            if '-F' not in pager_cmd: pager_cmd.append('-F')
        return pager_cmd
    
    def append_line(self, line):
        self.content.append(line)

    def display(self):
        content = '\n'.join(self.content)
        """Displays the given content using the pager if possible."""
        # Only use pager if output is to a real terminal
        if not self.use_pager or not sys.stdout.isatty():
            print(content)
            return

        try:
            pager_proc = subprocess.Popen(self.pager_command, stdin=subprocess.PIPE, stdout=sys.stdout)
            try:
                # Pipe the content to the pager
                pager_proc.stdin.write(content.encode('utf-8'))
            except (IOError, BrokenPipeError):
                # Happens if the user quits the pager early (e.g., 'q')
                pass
            
            pager_proc.stdin.close()
            pager_proc.wait()

        except FileNotFoundError:
            # Pager command not found, fall back to simple printing
            print("ERROR")
            print(content)
        except KeyboardInterrupt:
            # User pressed Ctrl-C
            pass
        finally:
            # Ensure stdin is properly closed if something went wrong
            if 'pager_proc' in locals() and pager_proc.stdin:
                 try:
                     pager_proc.stdin.close()
                 except (IOError, BrokenPipeError):
                     pass # Already closed or broken pipe
    
    def clear(self):
        self.content = []
