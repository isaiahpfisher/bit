import unittest
import os
import shutil
import tempfile

# Adjust the Python path to import from the 'src' directory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.repository import Repository

class TestRepository(unittest.TestCase):

    def setUp(self):
        """Called before every test function to create a fresh repository."""
        self.test_dir = tempfile.mkdtemp()
        os.chdir(self.test_dir)
        self.repo = Repository(self.test_dir)

    def tearDown(self):
        """Called after every test function to clean up."""
        os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        shutil.rmtree(self.test_dir)
    
    # ----- INIT TESTS -----
    def test_init_creates_repository_structure(self):      
        """Tests that init creates the correct directories and files."""
        self.repo.init()
        self.assertTrue(os.path.isdir(self.repo.bit_dir))
        self.assertTrue(os.path.isdir(os.path.join(self.repo.bit_dir, 'objects')))
        with open(os.path.join(self.repo.bit_dir, 'HEAD'), 'r') as f:
            self.assertEqual("ref: refs/heads/master\n", f.read())
        self.assertTrue(self.repo.index.is_empty())

    # ----- ADD TESTS -----
    def test_add_stages_a_single_file(self):
        """Tests adding a single file to an empty index."""
        self.repo.init()
        with open("hello.txt", "w") as f: f.write('hello world')
        
        staged_count = self.repo.add(["hello.txt"])
        self.assertEqual(1, staged_count, "Should stage 1 new file.")
        
        index_entries = self.repo.index.load_as_dict()
        self.assertEqual(1, len(index_entries))
        self.assertIn("hello.txt", index_entries)
    
    def test_add_returns_zero_for_unchanged_files(self):
        """Tests that re-adding an unmodified file stages 0 files."""
        self.repo.init()
        with open("hello.txt", "w") as f: f.write('content')
        self.repo.add(["hello.txt"])
        
        staged_count = self.repo.add(["hello.txt"])
        self.assertEqual(0, staged_count)

    def test_add_maintains_snapshot_across_multiple_calls(self):
        """Tests that adding does not overwrite index."""
        self.repo.init()
        with open("file1.txt", "w") as f: f.write("one")
        with open("file2.txt", "w") as f: f.write("two")

        self.repo.add(["file1.txt"])
        index_entries = self.repo.index.load_as_dict()
        self.assertEqual(1, len(index_entries), "Index should have one file after first add.")
        self.assertIn("file1.txt", index_entries)

        self.repo.add(["file2.txt"])
        index_entries = self.repo.index.load_as_dict()
        self.assertEqual(2, len(index_entries), "Index should have two files after second add.")
        self.assertIn("file1.txt", index_entries, "Index should still contain file1.txt.")
        self.assertIn("file2.txt", index_entries, "Index should now also contain file2.txt.")

    # ----- COMMIT TESTS -----       
    def test_commit_creates_initial_commit(self):
        """Tests that a commit clears the index and creates a valid commit object."""
        self.repo.init()
        with open("README.md", "w") as f: f.write("Welcome!")
        self.repo.add(["README.md"])
        commit_hash = self.repo.commit("Initial commit")

        self.assertTrue(self.repo.index.is_empty(), "Index should be empty after commit.")
        
        commit_content = self._read_object(commit_hash)
        self.assertIn("\n\nInitial commit", commit_content)
        self.assertNotIn("parent ", commit_content, "Initial commit should not have a parent.")
            
    def test_commit_creates_subsequent_commit(self):
        """Tests that a second commit correctly links to the first."""
        self.repo.init()
        with open("file1.txt", "w") as f: f.write("first")
        self.repo.add(["file1.txt"])
        commit1_hash = self.repo.commit("First commit")

        with open("file2.txt", "w") as f: f.write("second")
        self.repo.add(["file2.txt"])
        commit2_hash = self.repo.commit("Second commit")
        
        commit2_content = self._read_object(commit2_hash)
        self.assertIn(f"parent {commit1_hash}", commit2_content, "Second commit should point to first.")
        
    # ----- HELPER METHODS -----
    def _read_object(self, hash_val):
      """Helper to read an object file from the test repo's database."""
      path = os.path.join(self.repo.db.path, hash_val)
      with open(path, 'rb') as f:
          return f.read().decode('utf-8')
        
if __name__ == '__main__':
    unittest.main()

