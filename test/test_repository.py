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
        self.repo.init() # Initialize a clean repo for every test

    def tearDown(self):
        """Called after every test function to clean up."""
        # Change back to the original directory before removing the temp directory
        os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        shutil.rmtree(self.test_dir)

    # ----- HELPER METHODS -----
    def _write_file(self, path, content=""):
        """Helper to create a file with content."""
        # Ensure parent directory exists
        parent_dir = os.path.dirname(path)
        
        # Only call makedirs if parent_dir is not an empty string
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
            
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _read_object(self, hash_val):
      """Helper to read an object file from the test repo's database."""
      path = os.path.join(self.repo.db.path, hash_val)
      with open(path, 'rb') as f:
          return f.read().decode('utf-8')
    
    # ----- INIT TESTS -----
    def test_init_creates_repository_structure(self):      
        """Tests that init (called in setUp) creates the correct structure."""
        self.assertTrue(os.path.isdir(self.repo.bit_dir))
        self.assertTrue(os.path.isdir(os.path.join(self.repo.bit_dir, 'objects')))
        with open(os.path.join(self.repo.bit_dir, 'HEAD'), 'r') as f:
            self.assertEqual("ref: refs/heads/master\n", f.read())
        self.assertTrue(self.repo.index.is_empty())

    # ----- ADD TESTS -----
    def test_add_stages_a_single_file(self):
        """Tests adding a single file to an empty index."""
        self._write_file("hello.txt", "hello world")
        staged_count = self.repo.add(["hello.txt"])
        
        self.assertEqual(1, staged_count, "Should stage 1 new file.")
        index_entries = self.repo.index.load_as_dict()
        self.assertEqual(1, len(index_entries))
        self.assertIn("hello.txt", index_entries)
    
    def test_add_returns_zero_for_unchanged_files(self):
        """Tests that re-adding an unmodified file stages 0 files."""
        self._write_file("hello.txt", "content")
        self.repo.add(["hello.txt"])
        
        staged_count = self.repo.add(["hello.txt"])
        self.assertEqual(0, staged_count)

    def test_add_maintains_snapshot_across_multiple_calls(self):
        """Tests that adding does not overwrite index (the amnesia bug)."""
        self._write_file("file1.txt", "one")
        self._write_file("file2.txt", "two")

        self.repo.add(["file1.txt"])
        self.repo.add(["file2.txt"])
        
        index_entries = self.repo.index.load_as_dict()
        self.assertEqual(2, len(index_entries), "Index should have two files after second add.")
        self.assertIn("file1.txt", index_entries)
        self.assertIn("file2.txt", index_entries)

    def test_add_stages_deletion_when_path_is_passed(self):
        """Tests that 'add <file>' stages a deletion if file is missing."""
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("commit file")
        
        os.remove("file.txt")
        staged_count = self.repo.add(["file.txt"]) # Explicitly add deleted path
        
        self.assertEqual(1, staged_count, "Staging a deletion should count as 1 change.")
        index_entries = self.repo.index.load_as_dict()
        self.assertNotIn("file.txt", index_entries, "File should be removed from index.")

    def test_add_raises_error_for_untracked_nonexistent_file(self):
        """Tests that adding a nonexistent, untracked file fails."""
        with self.assertRaises(FileNotFoundError):
            self.repo.add(["nonexistent.txt"])

    # ----- RM TEST -----
    def test_rm_stages_deletion_and_removes_file(self):
        """Tests that 'rm <file>' stages a deletion and removes the file."""
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("commit file")
        
        self.repo.rm("file.txt") # Use the rm command
        
        self.assertFalse(os.path.exists("file.txt"), "File should be deleted from worktree.")
        index_entries = self.repo.index.load_as_dict()
        self.assertNotIn("file.txt", index_entries, "File should be removed from index.")

    # ----- ADD_ALL TEST -----
    def test_add_all_stages_new_modified_and_deleted(self):
        """Tests that 'add_all' (for 'add .') correctly syncs the index."""
        # 1. Commit initial state
        self._write_file("file_a.txt", "a_v1") # Will stay unchanged
        self._write_file("file_b.txt", "b_v1") # Will be modified
        self._write_file("file_c.txt", "c_v1") # Will be deleted
        self.repo.add_all()
        self.repo.commit("v1")

        # 2. Make changes to the worktree
        self._write_file("file_b.txt", "b_v2") # Modified
        os.remove("file_c.txt")                # Deleted
        self._write_file("file_d.txt", "d_v1") # New
        
        # 3. Act
        staged_count = self.repo.add_all()

        # 4. Assert
        self.assertEqual(3, staged_count, "Should stage 3 changes (modified, deleted, new).")
        
        index_entries = self.repo.index.load_as_dict()
        self.assertIn("file_a.txt", index_entries, "Unchanged file should remain.")
        self.assertIn("file_b.txt", index_entries, "Modified file should be in index.")
        self.assertNotIn("file_c.txt", index_entries, "Deleted file should be removed from index.")
        self.assertIn("file_d.txt", index_entries, "New file should be added to index.")
        
        # Verify hash of modified file is correct
        hash_b_v2 = self.repo.db.store(b"b_v2")
        self.assertEqual(hash_b_v2, index_entries["file_b.txt"])

    # ----- COMMIT TESTS -----       
    def test_commit_creates_initial_commit(self):
        self._write_file("README.md", "Welcome!")
        self.repo.add(["README.md"])
        commit_hash = self.repo.commit("Initial commit")

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
        """Tests status on a clean repository."""
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        
        status = self.repo.status()
        self.assertTrue(status.is_clean())

    def test_status_staged_new_file(self):
        """Tests status with a single staged new file."""
        self._write_file("new_file.txt", "new")
        self.repo.add(["new_file.txt"])
        
        status = self.repo.status()
        self.assertIn("new_file.txt", status.staged)
        self.assertEqual("new file", status.staged["new_file.txt"])
        self.assertFalse(status.unstaged)
        self.assertFalse(status.untracked)

    def test_status_staged_modified_file(self):
        """Tests status with a staged modification."""
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
        """Tests status with a staged deletion."""
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        
        self.repo.rm("file.txt") # Use our rm command to stage the deletion
        
        status = self.repo.status()
        self.assertIn("file.txt", status.staged)
        self.assertEqual("deleted", status.staged["file.txt"])
        self.assertFalse(status.unstaged)
        
    def test_status_unstaged_modified_file(self):
        """Tests status with an unstaged modification."""
        self._write_file("file.txt", "v1")
        self.repo.add(["file.txt"])
        self.repo.commit("Commit v1")
        
        self._write_file("file.txt", "v2") # Modify but do not add
        
        status = self.repo.status()
        self.assertIn("file.txt", status.unstaged)
        self.assertEqual("modified", status.unstaged["file.txt"])
        self.assertFalse(status.staged)

    def test_status_unstaged_deleted_file(self):
        """Tests status with an unstaged deletion (manual rm)."""
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        
        os.remove("file.txt") # Manually delete but do not 'rm'
        
        status = self.repo.status()
        self.assertIn("file.txt", status.unstaged)
        self.assertEqual("deleted", status.unstaged["file.txt"])
        self.assertFalse(status.staged)

    def test_status_untracked_file(self):
        """Tests status with a new untracked file."""
        self._write_file("file.txt", "content")
        self.repo.commit("Initial commit")
        
        self._write_file("new.txt", "new") # Write new file, but don't add
        
        status = self.repo.status()
        self.assertIn("new.txt", status.untracked)
        self.assertFalse(status.staged)
        self.assertFalse(status.unstaged)

    def test_status_complex_scenario(self):
        """Tests a mix of all statuses at once."""
        # 1. Commit 'file_a' and 'file_b'
        self._write_file("file_a.txt", "a_v1") # Will be staged-modified
        self._write_file("file_b.txt", "b_v1") # Will be unstaged-modified
        self._write_file("file_c.txt", "c_v1") # Will be staged-deleted
        self._write_file("file_d.txt", "d_v1") # Will be unstaged-deleted
        self.repo.add_all()
        self.repo.commit("Initial commit")

        # 2. Stage 'file_a' modification
        self._write_file("file_a.txt", "a_v2")
        self.repo.add(["file_a.txt"])
        
        # 3. Modify 'file_b', do not stage it
        self._write_file("file_b.txt", "b_v2")
        
        # 4. Stage deletion of 'file_c'
        self.repo.rm("file_c.txt")
        
        # 5. Manually delete 'file_d'
        os.remove("file_d.txt")
        
        # 6. Create new 'file_e', do not stage it (untracked)
        self._write_file("file_e.txt", "e_v1")
        
        # --- Assert Status ---
        status = self.repo.status()
        
        # Staged
        self.assertIn("file_a.txt", status.staged)
        self.assertEqual("modified", status.staged["file_a.txt"])
        self.assertIn("file_c.txt", status.staged)
        self.assertEqual("deleted", status.staged["file_c.txt"])
        
        # Unstaged
        self.assertIn("file_b.txt", status.unstaged)
        self.assertEqual("modified", status.unstaged["file_b.txt"])
        self.assertIn("file_d.txt", status.unstaged)
        self.assertEqual("deleted", status.unstaged["file_d.txt"])
        
        # Untracked
        self.assertIn("file_e.txt", status.untracked)
        
if __name__ == '__main__':
    unittest.main()

