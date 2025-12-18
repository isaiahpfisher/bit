import os
import configparser

class Config:
    def __init__(self, repo=None):
        self.repo = repo
        self.local_path = os.path.join(repo.bit_dir, 'config') if repo else None
        self.global_path = os.path.expanduser('~/.bitconfig')

    def get(self, section, key, default=None):
        """Reads config, prioritizing local over global."""
        parser = configparser.ConfigParser()
        paths = []
        if os.path.exists(self.global_path):
            paths.append(self.global_path)
        if self.local_path and os.path.exists(self.local_path):
            paths.append(self.local_path)
            
        parser.read(paths)
        return parser.get(section, key, fallback=default)

    def set(self, section, key, value, global_flag=False):
        """Writes a specific key to either global or local config."""
        path = self.global_path if global_flag else self.local_path
        
        if not path:
            raise Exception("Cannot set local config: Not in a bit repository.")

        if global_flag:
            os.makedirs(os.path.dirname(path), exist_ok=True)

        parser = configparser.ConfigParser()
        if os.path.exists(path):
            parser.read(path)
        
        if section not in parser.sections():
            parser.add_section(section)
            
        parser.set(section, key, value)
        
        with open(path, 'w') as f:
            parser.write(f)