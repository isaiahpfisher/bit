import time
from .formatter import Formatter

class Commit:
    """Represents a commit object."""
    
    def __init__(self, tree_hash, parent_hashes, message, author="Isaiah Fisher", email="isaiahpfisher@gmail.com", timestamp=None, timezone=None, committer_name=None, committer_email=None):
        self.tree_hash = tree_hash
        self.parent_hashes = parent_hashes
        self.message = message
        self.author = author
        self.email = email
        self.timestamp = timestamp if timestamp is not None else int(time.time())
        self.timezone = timezone if timezone is not None else time.strftime('%z')
        self.committer_name = committer_name if committer_name is not None else self.author
        self.committer_email = committer_email if committer_email is not None else self.email

    def serialize(self):
      lines = [f"tree {self.tree_hash}"]
      if self.parent_hashes:
          for hash in self.parent_hashes:
            lines.append(f"parent {hash}")
      lines.append(f"author {self.author} <{self.email}> {self.timestamp} {self.timezone}")
      lines.append(f"committer {self.committer_name} <{self.committer_email}> {self.timestamp} {self.timezone}")
      
      metadata = "\n".join(lines)
      return f"{metadata}\n\n{self.message}"

    @classmethod
    def parse(cls, raw_data_bytes):
        raw_data = raw_data_bytes.decode('utf-8')

        try:
            header, message = raw_data.split('\n\n', 1)
        except ValueError:
            header = raw_data
            message = ""

        tree_hash = None
        parent_hashes = []
        author_line = None
        committer_line = None

        for line in header.splitlines():
            key, value = line.split(' ', 1)

            if key == "tree":
                tree_hash = value
            elif key == "parent":
                parent_hashes.append(value)
            elif key == "author":
                author_line = value
            elif key == "committer":
                committer_line = value

        author, email, timestamp, timezone = cls._parse_person_line(author_line)
        committer_name, committer_email, _, _ = cls._parse_person_line(committer_line)

        return cls(
            tree_hash=tree_hash,
            parent_hashes=parent_hashes,   # ✅ Correct list argument
            message=message,
            author=author,
            email=email,
            timestamp=timestamp,
            timezone=timezone,
            committer_name=committer_name,
            committer_email=committer_email
        )

    
    # ----- UTILS -----
    @staticmethod
    def _parse_person_line(line):
        """Helper to parse an author or committer line."""
        email_start = line.find('<')
        email_end = line.find('>')
        
        name = line[:email_start].strip()
        email = line[email_start + 1:email_end]
        
        rest = line[email_end + 1:].strip()
        timestamp_str, timezone = rest.split(' ', 1)
        timestamp = int(timestamp_str)
        
        return name, email, timestamp, timezone
