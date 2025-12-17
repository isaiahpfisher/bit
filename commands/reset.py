import sys
from .base import BaseCommand

class ResetCommand(BaseCommand):
    def run(self):
        if not self._check_repo_exists():
            return

        mode = "--mixed"
        target = "HEAD"

        args = self.args[:]
        if "--soft" in args:
            mode = "--soft"
            args.remove("--soft")
        elif "--hard" in args:
            mode = "--hard"
            args.remove("--hard")
        elif "--mixed" in args:
            mode = "--mixed"
            args.remove("--mixed")

        if len(args) > 0:
            target = args[0]

        try:
            self.repo.reset(target, mode)
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")