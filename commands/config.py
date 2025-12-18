import sys
from .base import BaseCommand
from src.config import Config

class ConfigCommand(BaseCommand):
    def run(self):
        if not self.args:
            sys.stderr.write("Usage: bit config [--global] section.key [value]\n")
            return

        is_global = "--global" in self.args
        if is_global:
            self.args.remove("--global")

        if not self.args:
            sys.stderr.write("Error: section.key required.\n")
            return

        key_path = self.args[0]
        if "." not in key_path:
            sys.stderr.write("Error: key must be in 'section.key' format.\n")
            return

        section, key = key_path.split(".", 1)
        
        config_manager = Config(self.repo)

        # SET
        if len(self.args) > 1:
            value = self.args[1]
            try:
                config_manager.set(section, key, value, global_flag=is_global)
            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")
        
        # GET
        else:
            value = config_manager.get(section, key)
            if value:
                print(value)