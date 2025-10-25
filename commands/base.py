import sys
import os
from src.repository import Repository
from abc import ABC, abstractmethod

class BaseCommand(ABC):
    def __init__(self, repo: Repository, args):
        self.repo = repo
        self.args = args

    @abstractmethod
    def run(self):
        """Execute the command."""
        pass

    def _check_repo_exists(self):
        if not os.path.exists(self.repo.bit_dir):
            sys.stderr.write("Error: Not a Bit repository. Run 'bit init' first.\n")
            return False
        return True