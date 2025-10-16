import os
import hashlib

class Database:
    """Handles reading and writing to the object store."""
    
    def __init__(self, path):
        self.path = path

    def store(self, content):
      """Store content in the db and return its SHA-1 hash."""
      
      content_bytes = self._encode_content(content)

      hash = hashlib.sha1(content_bytes).hexdigest()
      object_path = os.path.join(self.path, hash)
      if not os.path.exists(object_path):
            with open(object_path, 'wb') as f:
                f.write(content_bytes)
      return hash
  
    def _encode_content(self, content):
        """Encodes the content only if it's not already encoded."""
        return content.encode('utf-8') if isinstance(content, str) else content
        