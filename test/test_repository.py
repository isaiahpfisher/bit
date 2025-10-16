import unittest
import os
import shutil
import tempfile

# adjust the path to import from the src'directory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.repository import Repository

class TestRepository(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        os.chdir(self.test_dir)
        self.repo = Repository(self.test_dir)

    def tearDown(self):
        os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        shutil.rmtree(self.test_dir)
    
    def test_init_creates_repository_structure(self):      
          
        self.assertFalse(os.path.exists(self.repo.bit_dir))
        self.repo.init()

        # Check for all expected directories and files
        self.assertTrue(os.path.isdir(self.repo.bit_dir))
        self.assertTrue(os.path.isdir(os.path.join(self.repo.bit_dir, 'objects')))
        self.assertTrue(os.path.isdir(os.path.join(self.repo.bit_dir, 'refs', 'heads')))

        # Check that HEAD points to the right place
        head_path = os.path.join(self.repo.bit_dir, 'HEAD')
        self.assertTrue(os.path.exists(head_path))
        with open(head_path, 'r') as f:
            self.assertEqual("ref: refs/heads/master\n", f.read())

        # Check for empty index file
        index_path = os.path.join(self.repo.bit_dir, 'index')
        self.assertTrue(os.path.exists(index_path))
        self.assertEqual(0, os.path.getsize(index_path))

    def test_init_raises_error_if_repository_exists(self):
        # Init once
        self.repo.init()

        # Check that init fails the second time
        with self.assertRaises(FileExistsError):
            self.repo.init()
            
    def test_add_stages_a_file(self):
        # Arrange
        self.repo.init()
        file_content = 'hello world'
        expected_hash = '2aae6c35c94fcfb415dbe95f408b9ce91ee846ed'
        with open("hello.txt", "w", encoding="utf-8") as f:
            f.write(file_content)    
        
        # Act
        self.repo.add("hello.txt")
        
        # Assert
        blob_path = os.path.join(self.repo.db.path, expected_hash)
        self.assertTrue(os.path.exists(blob_path), "Blob object was not created.")
        
        blob_content = self._read_object(expected_hash)
        self.assertEqual(file_content, blob_content, "Blob object contents don't match expected contents.")
            
        index_entries = self.repo.index.load()
        self.assertEqual(1, len(index_entries), "Index should have exactly one entry.")
        
        entry = index_entries[0]
        self.assertEqual(expected_hash, entry['hash'], "Incorrect hash in index.")
        self.assertEqual("hello.txt", entry['path'], "Incorrect file path in index.")
        
    def test_add_stages_nested_file(self):
        # Arrange
        self.repo.init()
        os.makedirs("src")

        file_content = "print('hello from main')"
        expected_hash = "aecef7f7dada210e1460ee137123593005ce8c15"
        file_path = os.path.join("src", "main.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)
            
        # Act
        self.repo.add(file_path)
        
        # Assert
        blob_path = os.path.join(self.repo.db.path, expected_hash)
        self.assertTrue(os.path.exists(blob_path), "Blob object was not created.")
        
        blob_content = self._read_object(expected_hash)
        self.assertEqual(file_content, blob_content, "Blob object contents don't match expected contents.")

        index_entries = self.repo.index.load()
        self.assertEqual(1, len(index_entries), "Index should have exactly one entry.")
        
        entry = index_entries[0]
        self.assertEqual(expected_hash, entry['hash'], "Incorrect hash in index.")
        self.assertEqual("src/main.py", entry['path'], "Incorrect path in index.")
    
    def test_add_updates_existing_entry(self):
        """
        Tests that re-adding a modified file updates its hash in the index.
        """
        # Arrange
        self.repo.init()
        
        file_path = "status.txt"
        original_content = "original"
        modified_content = "modified"
        expected_hash_original = "d73ef92426f2b11dfc4aed4d4bfc41c49ee1087c"
        expected_hash_modified = "99db324742823c55d975b605e1fc22f4253a9b7d"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(original_content)
        self.repo.add(file_path)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(modified_content)
            
        # Act
        self.repo.add(file_path)
        
        # Assert
        modified_blob_path = os.path.join(self.repo.db.path, expected_hash_modified)
        self.assertTrue(os.path.exists(modified_blob_path), "Modified blob content does not exist in database.")
        
        index_entries = self.repo.index.load()
        self.assertEqual(1, len(index_entries), "Index should still only have one entry.")
        
        entry = index_entries[0]
        self.assertEqual(expected_hash_modified, entry['hash'], "Incorrect hash in index. Hash should be the modified hash.")
        self.assertEqual(file_path, entry['path'], "Incorrect path in index.")
        
    def test_commit_creates_initial_commit(self):
        # Arrange
        self.repo.init()

        with open("README.md", "w", encoding="utf-8") as f:
            f.write("Welcome to Bit!\n")
        self.repo.add("README.md")

        # Act
        commit_message = "Initial commit"
        commit_hash = self.repo.commit(commit_message)

        # Assert
        master_ref_path = os.path.join(self.repo.bit_dir, 'refs', 'heads', 'master')
        self.assertTrue(os.path.exists(master_ref_path), "Branch head file was not created.")

        with open(master_ref_path, 'r') as f:
            self.assertEqual(commit_hash, f.read().strip(), "Branch head does not point to the new commit.")

        self.assertTrue(self.repo.index.is_empty(), "Index was not cleared after commit.")
        
        commit_content = self._read_object(commit_hash)
        lines = commit_content.splitlines()

        self.assertTrue(lines[0].startswith("tree "), "Commit object is missing tree reference.")
        self.assertFalse("parent " in commit_content, "Initial commit should not have a parent.") # no parent for first commit
        self.assertTrue(lines[1].startswith("author "), "Commit object is missing author.")
        self.assertTrue(lines[2].startswith("committer "), "Commit object is missing committer.")
        self.assertEqual("", lines[3], "Commit metadata and message should be separated by a blank line.")
        self.assertEqual(commit_message, lines[4], "Commit message is incorrect.")
            
    def test_commit_creates_subsequent_commit(self):
        """
        Tests that a second commit correctly points to the first commit
        as its parent.
        """
        # Arrange
        self.repo.init()
        with open("file1.txt", "w") as f:
            f.write("first")
        self.repo.add("file1.txt")
        commit1_hash = self.repo.commit("First commit")
        self.assertIsNotNone(commit1_hash, 'Commit 1 hash is empty.')

        with open("file2.txt", "w") as f:
            f.write("second")
        self.repo.add("file2.txt")

        # Act
        commit2_message = "Second commit"
        commit2_hash = self.repo.commit(commit2_message)
        self.assertIsNotNone(commit2_hash, 'Commit 2 hash is empty.')
        self.assertNotEqual(commit1_hash, commit2_hash, "Commit hashes should not be the same.") 
        
        # Assert
        master_ref_path = os.path.join(self.repo.bit_dir, 'refs', 'heads', 'master')
        with open(master_ref_path, 'r') as f:
            self.assertEqual(commit2_hash, f.read().strip(), "Branch head should point to the second commit.")
        
        commit2_content = self._read_object(commit2_hash)
        lines = commit2_content.splitlines()
        self.assertEqual(f"parent {commit1_hash}", lines[1], "Second commit's parent is incorrect.")
        self.assertTrue(lines[0].startswith("tree "), "Commit is missing tree reference.")
        self.assertTrue(lines[2].startswith("author "), "Commit is missing author.")
        self.assertEqual(commit2_message, lines[5], "Commit message is incorrect.")
        
    def _read_object(self, hash):
      """Helper to read an object file from the test repo's database."""
      path = os.path.join(self.repo.db.path, hash)
      with open(path, 'rb') as f:
          return f.read().decode('utf-8')
        
if __name__ == '__main__':
    unittest.main() 