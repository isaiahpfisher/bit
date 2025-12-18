import sys
import os
import shutil
from .base import BaseCommand
from src.repository import Repository

class CloneCommand(BaseCommand):
    def run(self):
        if len(self.args) < 1:
            sys.stderr.write("Usage: bit clone <source_path> [<destination_path>]\n")
            return

        source_path = os.path.abspath(self.args[0])
        source_bit_dir = os.path.join(source_path, '.bit')
        
        if not os.path.exists(source_bit_dir):
            sys.stderr.write(f"Error: '{self.args[0]}' does not appear to be a bit repository.\n")
            return

        if len(self.args) > 1:
            dest_path = self.args[1]
        else:
            dest_path = os.path.basename(source_path)

        if os.path.exists(dest_path):
            sys.stderr.write(f"Error: destination path '{dest_path}' already exists.\n")
            return

        try:
            print(f"Cloning into '{dest_path}'...")
            
            dest_bit_dir = os.path.join(dest_path, '.bit')
            shutil.copytree(source_bit_dir, dest_bit_dir)

            new_repo = Repository(os.path.abspath(dest_path))
            current_branch = new_repo.current_branch()
            new_repo.checkout(current_branch, force=True)
            
            print("Done.")
            
        except Exception as e:
            sys.stderr.write(f"Error during clone: {e}\n")