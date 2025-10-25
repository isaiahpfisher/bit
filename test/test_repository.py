import unittest
import os
import shutil
import tempfile

# Adjust the Python path to import from the 'src' directory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.repository import Repository
from src.commit import Commit # Needed for log tests

class TestRepository(unittest.TestCase):

    def setUp(self):
        """Called before every test function to create a fresh repository."""
        self.test_dir = tempfile.mkdtemp()
        os.chdir(self.test_dir)
        self.repo = Repository(self.test_dir)
        self.repo.init() # Initialize a clean repo for every test

    def tearDown(self):
        """Called after every test function to clean up."""
        os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        shutil.rmtree(self.test_dir)

    # ----- HELPER METHODS -----
    def _write_file(self, path, content=""):
        """Helper to create a file with content."""
        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _read_object(self, hash_val):
      """Helper to read an object file from the test repo's database."""
      path = os.path.join(self.repo.db.path, hash_val)
      with open(path, 'rb') as f:
          return f.read().decode('utf-8')
          
    def _get_commit_hash(self, commit_obj: Commit) -> str:
        """Helper to calculate the hash of a Commit object."""
        return self.repo.db.store(commit_obj.serialize())

    # ----- INIT TESTS -----
    def test_init_creates_repository_structure(self):      
        self.assertTrue(os.path.isdir(self.repo.bit_dir))
        self.assertTrue(os.path.isdir(os.path.join(self.repo.bit_dir, 'objects')))
        with open(os.path.join(self.repo.bit_dir, 'HEAD'), 'r') as f:
            self.assertEqual("ref: refs/heads/master\n", f.read())
        self.assertTrue(self.repo.index.is_empty())

    # ----- ADD TESTS -----
    def test_add_stages_a_single_file(self):
        self._write_file("hello.txt", "hello world")
        staged_count = self.repo.add(["hello.txt"])
        self.assertEqual(1, staged_count)
        index_entries = self.repo.index.load_as_dict()
        self.assertEqual(1, len(index_entries))
        self.assertIn("hello.txt", index_entries)
    
    def test_add_returns_zero_for_unchanged_files(self):
        self._write_file("hello.txt", "content")
        self.repo.add(["hello.txt"])
        staged_count = self.repo.add(["hello.txt"])
        self.assertEqual(0, staged_count)

    def test_add_maintains_snapshot_across_multiple_calls(self):
        self._write_file("file1.txt", "one")
        self._write_file("file2.txt", "two")
        self.repo.add(["file1.txt"])
        self.repo.add(["file2.txt"])
        index_entries = self.repo.index.load_as_dict()
        self.assertEqual(2, len(index_entries))
        self.assertIn("file1.txt", index_entries)
        self.assertIn("file2.txt", index_entries)

    def test_add_stages_deletion_when_path_is_passed(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("commit file")
        os.remove("file.txt")
        staged_count = self.repo.add(["file.txt"])
        self.assertEqual(1, staged_count)
        index_entries = self.repo.index.load_as_dict()
        self.assertNotIn("file.txt", index_entries)

    def test_add_raises_error_for_untracked_nonexistent_file(self):
        with self.assertRaises(FileNotFoundError):
            self.repo.add(["nonexistent.txt"])

    # ----- RM TEST -----
    def test_rm_stages_deletion_and_removes_file(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("commit file")
        self.repo.rm("file.txt")
        self.assertFalse(os.path.exists("file.txt"))
        index_entries = self.repo.index.load_as_dict()
        self.assertNotIn("file.txt", index_entries)

    def test_rm_raises_error_for_untracked_file(self):
        self._write_file("file.txt", "content")
        with self.assertRaises(FileNotFoundError):
            self.repo.rm("file.txt")

    # ----- ADD_ALL TEST -----
    def test_add_all_stages_new_modified_and_deleted(self):
        self._write_file("file_a.txt", "a_v1")
        self._write_file("file_b.txt", "b_v1")
        self._write_file("file_c.txt", "c_v1")
        self.repo.add_all()
        self.repo.commit("v1")
        self._write_file("file_b.txt", "b_v2")
        os.remove("file_c.txt")
        self._write_file("file_d.txt", "d_v1")
        staged_count = self.repo.add_all()
        self.assertEqual(3, staged_count)
        index_entries = self.repo.index.load_as_dict()
        self.assertIn("file_a.txt", index_entries)
        self.assertIn("file_b.txt", index_entries)
        self.assertNotIn("file_c.txt", index_entries)
        self.assertIn("file_d.txt", index_entries)
        hash_b_v2 = self.repo.db.store(b"b_v2")
        self.assertEqual(hash_b_v2, index_entries["file_b.txt"])

    # ----- COMMIT TESTS -----       
    def test_commit_creates_initial_commit(self):
        self._write_file("README.md", "Welcome!")
        self.repo.add(["README.md"])
        commit_hash = self.repo.commit("Initial commit")
        self.assertFalse(self.repo.index.is_empty()) # Index should match commit
        commit_content = self._read_object(commit_hash)
        self.assertIn("\n\nInitial commit", commit_content)
        self.assertNotIn("parent ", commit_content)
            
    def test_commit_creates_subsequent_commit(self):
        self._write_file("file1.txt", "first")
        self.repo.add(["file1.txt"])
        commit1_hash = self.repo.commit("First commit")
        self._write_file("file2.txt", "second")
        self.repo.add(["file2.txt"])
        commit2_hash = self.repo.commit("Second commit")
        commit2_content = self._read_object(commit2_hash)
        self.assertIn(f"parent {commit1_hash}", commit2_content)
        
    # ----- STATUS TESTS -----
    def test_status_clean(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        status = self.repo.status()
        self.assertTrue(status.is_clean())

    # ... other status tests remain the same ...
    def test_status_staged_new_file(self):
        self._write_file("new_file.txt", "new")
        self.repo.add(["new_file.txt"])
        status = self.repo.status()
        self.assertIn("new_file.txt", status.staged)
        self.assertEqual("new file", status.staged["new_file.txt"])
        self.assertFalse(status.unstaged)
        self.assertFalse(status.untracked)

    def test_status_staged_modified_file(self):
        self._write_file("file.txt", "v1")
        self.repo.add(["file.txt"])
        self.repo.commit("Commit v1")
        self._write_file("file.txt", "v2")
        self.repo.add(["file.txt"])
        status = self.repo.status()
        self.assertIn("file.txt", status.staged)
        self.assertEqual("modified", status.staged["file.txt"])
        self.assertFalse(status.unstaged)

    def test_status_staged_deleted_file(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        self.repo.rm("file.txt")
        status = self.repo.status()
        self.assertIn("file.txt", status.staged)
        self.assertEqual("deleted", status.staged["file.txt"])
        self.assertFalse(status.unstaged)
        
    def test_status_unstaged_modified_file(self):
        self._write_file("file.txt", "v1")
        self.repo.add(["file.txt"])
        self.repo.commit("Commit v1")
        self._write_file("file.txt", "v2")
        status = self.repo.status()
        self.assertIn("file.txt", status.unstaged)
        self.assertEqual("modified", status.unstaged["file.txt"])
        self.assertFalse(status.staged)

    def test_status_unstaged_deleted_file(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        os.remove("file.txt")
        status = self.repo.status()
        self.assertIn("file.txt", status.unstaged)
        self.assertEqual("deleted", status.unstaged["file.txt"])
        self.assertFalse(status.staged)

    def test_status_untracked_file(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        self._write_file("new.txt", "new")
        status = self.repo.status()
        self.assertIn("new.txt", status.untracked)
        self.assertFalse(status.staged)
        self.assertFalse(status.unstaged)

    def test_status_complex_scenario(self):
        self._write_file("file_a.txt", "a_v1")
        self._write_file("file_b.txt", "b_v1")
        self._write_file("file_c.txt", "c_v1")
        self._write_file("file_d.txt", "d_v1")
        self.repo.add_all()
        self.repo.commit("Initial commit")
        self._write_file("file_a.txt", "a_v2")
        self.repo.add(["file_a.txt"])
        self._write_file("file_b.txt", "b_v2")
        self.repo.rm("file_c.txt")
        os.remove("file_d.txt")
        self._write_file("file_e.txt", "e_v1")
        status = self.repo.status()
        self.assertIn("file_a.txt", status.staged); self.assertEqual("modified", status.staged["file_a.txt"])
        self.assertIn("file_c.txt", status.staged); self.assertEqual("deleted", status.staged["file_c.txt"])
        self.assertIn("file_b.txt", status.unstaged); self.assertEqual("modified", status.unstaged["file_b.txt"])
        self.assertIn("file_d.txt", status.unstaged); self.assertEqual("deleted", status.unstaged["file_d.txt"])
        self.assertIn("file_e.txt", status.untracked)

    # ----- LOG TESTS -----
    def test_log_empty_repo(self):
        """Tests that log returns an empty list for a repo with no commits."""
        logs = self.repo.log()
        self.assertEqual([], logs)

    def test_log_initial_commit(self):
        """Tests log output after the first commit."""
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        commit_hash = self.repo.commit("Initial commit")
        
        logs = self.repo.log()
        
        self.assertEqual(1, len(logs))
        log_entry = logs[0]
        
        self.assertEqual(commit_hash, log_entry.hash)
        self.assertIsNone(log_entry.commit.parent_hash)
        self.assertEqual("Initial commit", log_entry.commit.message)
        self.assertEqual("master", log_entry.head_ref.name)
        self.assertIn("master", log_entry.refs)

    def test_log_multiple_commits(self):
        """Tests log output order and parent links for multiple commits."""
        self._write_file("file1.txt", "first")
        self.repo.add(["file1.txt"])
        commit1_hash = self.repo.commit("First commit")
        
        self._write_file("file2.txt", "second")
        self.repo.add(["file2.txt"])
        commit2_hash = self.repo.commit("Second commit")

        logs = self.repo.log()

        self.assertEqual(2, len(logs))
        
        # Check order (latest commit first)
        self.assertEqual(commit2_hash, logs[0].hash)
        self.assertEqual(commit1_hash, logs[1].hash)
        
        # Check parent link
        self.assertEqual(commit1_hash, logs[0].commit.parent_hash)
        self.assertIsNone(logs[1].commit.parent_hash)
        
        # Check refs (HEAD and master should point to commit 2)
        self.assertEqual("master", logs[0].head_ref.name)
        self.assertIn("master", logs[0].refs)
        self.assertEqual([], logs[1].refs) # Commit 1 should have no refs pointing to it now

        
if __name__ == '__main__':
    unittest.main()

