import time

class Commit:
    """Represents a commit object."""
    
    def __init__(self, tree_hash, parent_hash, message, author="Isaiah Fisher", email="isaiahpfisher@gmail.com", timestamp=None, timezone=None, committer_name=None, committer_email=None):
        self.tree_hash = tree_hash
        self.parent_hash = parent_hash
        self.message = message
        self.author = author
        self.email = email
        self.timestamp = timestamp if timestamp is not None else int(time.time())
        self.timezone = timezone if timezone is not None else time.strftime('%z')
        self.committer_name = committer_name if committer_name is not None else self.author
        self.committer_email = committer_email if committer_email is not None else self.email

    def serialize(self):
      lines = [f"tree {self.tree_hash}"]
      if self.parent_hash:
          lines.append(f"parent {self.parent_hash}")
      lines.append(f"author {self.author} <{self.email}> {self.timestamp} {self.timezone}")
      lines.append(f"committer {self.committer_name} <{self.committer_email}> {self.timestamp} {self.timezone}")
      
      metadata = "\n".join(lines)
      return f"{metadata}\n\n{self.message}"

    @classmethod
    def parse(cls, raw_data):
        
        try:
            header, message = raw_data.split('\n\n', 1)
        except ValueError:
            header = raw_data
            message = ""
            
        header_data = {}
        for line in header.splitlines():
            key, value = line.split(' ', 1)
            header_data[key] = value
            
        tree_hash = header_data.get('tree')
        parent_hash = header_data.get('parent')
        author, email, timestamp, timezone = cls._parse_person_line(header_data.get('author'))
        committer_name, committer_email, _, _ = cls._parse_person_line(header_data.get('committer'))
        
        return cls(
            tree_hash=tree_hash,
            parent_hash=parent_hash,
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