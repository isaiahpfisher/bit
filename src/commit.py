import time

class Commit:
    """Represents a commit object."""
    
    def __init__(self, tree_hash, parent_hash, message):
        self.tree_hash = tree_hash
        self.parent_hash = parent_hash
        self.message = message
        self.author = "Isaiah Fisher"
        self.email = "isaiahpfisher@gmail.com"
        self.timestamp = int(time.time())
        self.timezone = time.strftime('%z')

    def serialize(self):
      lines = [f"tree {self.tree_hash}"]
      if self.parent_hash:
          lines.append(f"parent {self.parent_hash}")
      lines.append(f"author {self.author} <{self.email}> {self.timestamp} {self.timezone}")
      lines.append(f"committer {self.author} <{self.email}> {self.timestamp} {self.timezone}")
      
      metadata = "\n".join(lines)
      return f"{metadata}\n\n{self.message}"

    @classmethod
    def parse(cls, raw_data):
        # This class method takes raw bytes from the database
        # and returns a new Commit object.
        pass