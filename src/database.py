import os
import hashlib

class Database:
    """Handles reading and writing to the object store."""
    
    def __init__(self, path):
        self.path = path
        
    def read(self, hash):
        """Returns the cont content in the db at the given SHA-1 hash."""
        path = os.path.join(self.path, hash)
        with open(path, 'rb') as f:
          return f.read().decode('utf-8')        

    def store(self, content):
      """Store content in the db and return its SHA-1 hash."""
      
      content_bytes = self.encode_content(content)
      hash = self.hash_content(content)
      object_path = os.path.join(self.path, hash)
      if not os.path.exists(object_path):
            with open(object_path, 'wb') as f:
                f.write(content_bytes)
      return hash
  
    @classmethod
    def hash_content(cls, content):
        content_bytes = cls.encode_content(content)
        return hashlib.sha1(content_bytes).hexdigest()
  
    @classmethod
    def encode_content(cls, content):
        """Encodes the content only if it's not already encoded."""
        return content.encode('utf-8') if isinstance(content, str) else content
        