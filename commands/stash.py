import sys
from .base import BaseCommand

class StashCommand(BaseCommand):
    def run(self):
        if not self._check_repo_exists():
            return

        subcommand = "push"
        if len(self.args) > 0 and self.args[0] in ["push", "pop", "list"]:
            subcommand = self.args[0]
            args = self.args[1:]
        else:
            args = self.args

        try:
            if subcommand == "push":
                message = args[0] if len(args) > 0 else None
                self.repo.stash_push(message)
                print("Saved working directory and index state WIP")
            elif subcommand == "pop":
                self.repo.stash_pop()
                print("Dropped refs/stash@{0}")
            elif subcommand == "list":
                stashes = self.repo.stash_list()
                if not stashes:
                    print("No stashes found.")
                for i, stash in enumerate(stashes):
                    print(f"stash@{{{i}}}: {stash['hash'][:7]} {stash['message']}")
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")