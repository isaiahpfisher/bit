import unittest
import os
import shutil
import tempfile

# Adjust the Python path to import from the 'src' directory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.repository import Repository
from src.commit import Commit # Needed for log tests
from src.ref import Ref       # Needed for branch tests
# Need FileDiff to check results
from src.file_diff import FileDiff 

class TestRepository(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        os.chdir(self.test_dir)
        self.repo = Repository(self.test_dir)
        self.repo.init() 

    def tearDown(self):
        os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        shutil.rmtree(self.test_dir)

    # ----- HELPER METHODS -----
    def _write_file(self, path, content=""):
        parent_dir = os.path.dirname(path)
        if parent_dir: os.makedirs(parent_dir, exist_ok=True)
        # Write as bytes for consistency
        with open(path, "wb") as f: f.write(content.encode('utf-8'))

    def _read_object(self, hash_val):
        """ Reads object as bytes """
        path = os.path.join(self.repo.db.path, hash_val)
        if not os.path.exists(path): return None # Handle missing object case
        with open(path, 'rb') as f:
            return f.read()
            
    def _read_object_str(self, hash_val):
        """ Reads object as bytes and decodes for string assertions. """
        content_bytes = self._read_object(hash_val)
        return content_bytes.decode('utf-8', errors='replace') if content_bytes is not None else None

    def _read_worktree_file(self, path):
        """ Reads a file from the test worktree as bytes. Returns None if not found. """
        # Ensure path uses OS separator for lookup
        full_path = os.path.join(self.test_dir, path.replace('/', os.sep))
        try:
            with open(full_path, 'rb') as f:
                 return f.read()
        except FileNotFoundError:
            return None
            
    def _read_worktree_file_str(self, path):
         """ Reads a file from the test worktree as string. Returns None if not found. """
         content_bytes = self._read_worktree_file(path)
         return content_bytes.decode('utf-8', errors='replace') if content_bytes is not None else None


    def _get_commit_hash(self, commit_obj: Commit) -> str:
        # Use bytes directly for hashing
        return self.repo.db.store(commit_obj.serialize().encode('utf-8')) 
        
    def _get_branch_hash(self, branch_name):
        # Handle nested branches in path
        ref_path = os.path.join(self.repo.bit_dir, 'refs', 'heads', *branch_name.split('/'))
        if os.path.exists(ref_path):
            with open(ref_path, 'r') as f:
                return f.read().strip()
        return None
        
    def _read_head_branch(self):
        head_path = os.path.join(self.repo.bit_dir, 'HEAD')
        if not os.path.exists(head_path): return None
        with open(head_path, 'r') as f: content = f.read().strip()
        if content.startswith("ref: refs/heads/"):
             # Handle nested branches correctly
             return '/'.join(content.split('/')[2:]) 
        return None # Detached HEAD or invalid

    # ----- INIT TESTS (Unchanged) -----
    def test_init_creates_repository_structure(self):      
        self.assertTrue(os.path.isdir(self.repo.bit_dir))
        self.assertTrue(os.path.isdir(os.path.join(self.repo.bit_dir, 'objects')))
        self.assertEqual("master", self._read_head_branch())
        self.assertTrue(self.repo.index.is_empty())

    # ----- ADD / RM / ADD_ALL / COMMIT (Unchanged) -----
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
        hash_b_v2 = self.repo.db.store(b"b_v2") # Store raw bytes
        self.assertEqual(hash_b_v2, index_entries["file_b.txt"])

    def test_commit_creates_initial_commit(self):
        self._write_file("README.md", "Welcome!")
        self.repo.add(["README.md"])
        commit_hash = self.repo.commit("Initial commit")
        self.assertFalse(self.repo.index.is_empty()) 
        commit_content = self._read_object_str(commit_hash) # Use str helper
        self.assertIn("\n\nInitial commit", commit_content)
        self.assertNotIn("parent ", commit_content)
            
    def test_commit_creates_subsequent_commit(self):
        self._write_file("file1.txt", "first")
        self.repo.add(["file1.txt"])
        commit1_hash = self.repo.commit("First commit")
        self._write_file("file2.txt", "second")
        self.repo.add(["file2.txt"])
        commit2_hash = self.repo.commit("Second commit")
        commit2_content = self._read_object_str(commit2_hash) # Use str helper
        self.assertIn(f"parent {commit1_hash}", commit2_content)

    # ----- STATUS TESTS (Unchanged) -----
    def test_status_clean(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        status = self.repo.status()
        self.assertTrue(status.is_clean())

    def test_status_staged_new_file(self):
        self._write_file("new_file.txt", "new")
        self.repo.add(["new_file.txt"])
        status = self.repo.status()
        self.assertIn("new_file.txt", status.staged)
        self.assertEqual("new file", status.staged["new_file.txt"])

    def test_status_staged_modified_file(self):
        self._write_file("file.txt", "v1")
        self.repo.add(["file.txt"])
        self.repo.commit("Commit v1")
        self._write_file("file.txt", "v2")
        self.repo.add(["file.txt"])
        status = self.repo.status()
        self.assertIn("file.txt", status.staged)
        self.assertEqual("modified", status.staged["file.txt"])

    def test_status_staged_deleted_file(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        self.repo.rm("file.txt")
        status = self.repo.status()
        self.assertIn("file.txt", status.staged)
        self.assertEqual("deleted", status.staged["file.txt"])
        
    def test_status_unstaged_modified_file(self):
        self._write_file("file.txt", "v1")
        self.repo.add(["file.txt"])
        self.repo.commit("Commit v1")
        self._write_file("file.txt", "v2")
        status = self.repo.status()
        self.assertIn("file.txt", status.unstaged)
        self.assertEqual("modified", status.unstaged["file.txt"])

    def test_status_unstaged_deleted_file(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        os.remove("file.txt")
        status = self.repo.status()
        self.assertIn("file.txt", status.unstaged)
        self.assertEqual("deleted", status.unstaged["file.txt"])

    def test_status_untracked_file(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        self._write_file("new.txt", "new")
        status = self.repo.status()
        self.assertIn("new.txt", status.untracked)

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
    
    # ----- LOG TESTS (Unchanged) -----
    def test_log_empty_repo(self):
        shutil.rmtree(self.repo.bit_dir) 
        self.repo.init() 
        logs = self.repo.log()
        self.assertEqual([], logs)

    def test_log_initial_commit(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        commit_hash = self.repo.commit("Initial commit")
        logs = self.repo.log()
        self.assertEqual(1, len(logs))
        log_entry = logs[0]
        self.assertEqual(commit_hash, log_entry.hash)
        self.assertIsNone(log_entry.commit.parent_hash)
        current_branch = self._read_head_branch()
        self.assertEqual("master", current_branch) 
        self.assertIn("master", log_entry.refs)
        self.assertIsNotNone(log_entry.head_ref)
        self.assertEqual("master", log_entry.head_ref.name)

    def test_log_multiple_commits(self):
        self._write_file("file1.txt", "first")
        self.repo.add(["file1.txt"])
        commit1_hash = self.repo.commit("First commit")
        self._write_file("file2.txt", "second")
        self.repo.add(["file2.txt"])
        commit2_hash = self.repo.commit("Second commit")
        logs = self.repo.log()
        self.assertEqual(2, len(logs))
        self.assertEqual(commit2_hash, logs[0].hash)
        self.assertEqual(commit1_hash, logs[1].hash)
        self.assertEqual(commit1_hash, logs[0].commit.parent_hash)
        self.assertIsNone(logs[1].commit.parent_hash)
        current_branch = self._read_head_branch()
        self.assertEqual("master", current_branch)
        self.assertIn("master", logs[0].refs) 
        self.assertEqual([], logs[1].refs)
        self.assertIsNotNone(logs[0].head_ref)
        self.assertEqual("master", logs[0].head_ref.name)

    # ----- BRANCH TESTS (Unchanged) -----
    def test_branch_list_initial(self):
        self._write_file("init.txt", "go")
        self.repo.add(["init.txt"])
        self.repo.commit("Initial")
        branches = self.repo.list_branches()
        self.assertEqual(['master'], branches) 

    def test_branch_create_new(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        commit_hash = self.repo.commit("Initial commit")
        self.repo.branch("develop")
        branches = self.repo.list_branches()
        self.assertCountEqual(['master', 'develop'], branches) 
        develop_hash = self._get_branch_hash("develop")
        self.assertEqual(commit_hash, develop_hash)
        master_hash = self._get_branch_hash("master")
        self.assertEqual(commit_hash, master_hash)

    def test_branch_create_existing_raises_error(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        self.repo.branch("develop") 
        with self.assertRaisesRegex(Exception, "already exists"):
            self.repo.branch("develop")

    def test_branch_create_before_first_commit_raises_error(self):
        shutil.rmtree(self.repo.bit_dir)
        self.repo.init() 
        with self.assertRaisesRegex(Exception, "Not a valid object name"):
            self.repo.branch("develop")

    def test_branch_list_multiple(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        self.repo.branch("develop")
        self.repo.branch("feature-x") # Use hyphen instead of slash
        branches = self.repo.list_branches()
        self.assertCountEqual(['master', 'develop', 'feature-x'], branches)
        
    def test_branch_name_with_slash_raises_error(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        with self.assertRaisesRegex(ValueError, "Branch names cannot contain forward slashes"):
            self.repo.branch("feature/x")

    # ----- CHECKOUT TESTS (Unchanged) -----
    # ... (all existing checkout tests remain the same) ...
    def test_checkout_updates_head(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        self.repo.branch("develop")
        self.repo.checkout("develop")
        self.assertEqual("develop", self._read_head_branch())

    def test_checkout_updates_index_and_worktree(self):
        self._write_file("file_a.txt", "a_v1")
        self._write_file("file_b.txt", "b_v1")
        self.repo.add_all()
        commit1_hash = self.repo.commit("v1")
        self.repo.branch("develop")
        self._write_file("file_a.txt", "a_v2")
        self.repo.add(["file_a.txt"])
        commit2_hash = self.repo.commit("v2 on master")
        self.assertEqual("master", self._read_head_branch()) 
        self.repo.checkout("develop")
        self.assertEqual("develop", self._read_head_branch())
        index_entries = self.repo.index.load_as_dict()
        self.assertEqual(2, len(index_entries))
        self.assertIn("file_a.txt", index_entries)
        self.assertIn("file_b.txt", index_entries)
        hash_a_v1 = self.repo.db.store(b"a_v1") 
        self.assertEqual(hash_a_v1, index_entries["file_a.txt"])
        self.assertEqual("a_v1", self._read_worktree_file_str("file_a.txt"))
        self.assertEqual("b_v1", self._read_worktree_file_str("file_b.txt"))

    def test_checkout_handles_file_deletion(self):
        self._write_file("file_a.txt", "a")
        self._write_file("file_b.txt", "b")
        self.repo.add_all()
        self.repo.commit("v1")
        self.repo.branch("develop")
        self.repo.checkout("develop") 
        self.repo.rm("file_b.txt")
        self.repo.commit("Removed b on develop")
        self.repo.checkout("master")
        self.assertTrue(os.path.exists(os.path.join(self.test_dir,"file_b.txt"))) 
        self.repo.checkout("develop")
        self.assertFalse(os.path.exists(os.path.join(self.test_dir,"file_b.txt")))
        index_entries = self.repo.index.load_as_dict()
        self.assertNotIn("file_b.txt", index_entries)
        self.assertIn("file_a.txt", index_entries) 

    def test_checkout_handles_file_addition(self):
        self._write_file("file_a.txt", "a")
        self.repo.add_all()
        self.repo.commit("v1")
        self.repo.branch("develop")
        self.repo.checkout("develop")
        self._write_file("file_b.txt", "b")
        self.repo.add(["file_b.txt"])
        self.repo.commit("Added b on develop")
        self.repo.checkout("master")
        self.assertFalse(os.path.exists(os.path.join(self.test_dir,"file_b.txt")))
        self.repo.checkout("develop")
        self.assertTrue(os.path.exists(os.path.join(self.test_dir,"file_b.txt")))
        self.assertEqual("b", self._read_worktree_file_str("file_b.txt"))
        index_entries = self.repo.index.load_as_dict()
        self.assertIn("file_b.txt", index_entries)
        self.assertIn("file_a.txt", index_entries)

    def test_checkout_handles_nested_directories(self):
        self._write_file("dir/file1.txt", "one")
        self.repo.add_all()
        self.repo.commit("v1")
        self.repo.branch("develop")
        self.repo.checkout("develop")
        self._write_file("dir/subdir/file2.txt", "two")
        self.repo.rm("dir/file1.txt") 
        self.repo.add(["dir/subdir/file2.txt"]) 
        self.repo.commit("develop changes")
        self.repo.checkout("master")
        self.assertTrue(os.path.exists(os.path.join(self.test_dir,"dir/file1.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir,"dir/subdir/file2.txt")))
        # Check if empty dir removal logic worked during checkout from develop->master
        self.assertFalse(os.path.exists(os.path.join(self.test_dir,"dir/subdir"))) 
        self.assertTrue(os.path.exists(os.path.join(self.test_dir,"dir"))) 
        self.repo.checkout("develop")
        self.assertFalse(os.path.exists(os.path.join(self.test_dir,"dir/file1.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir,"dir/subdir/file2.txt")))
        self.assertEqual("two", self._read_worktree_file_str("dir/subdir/file2.txt"))
        index_entries = self.repo.index.load_as_dict()
        self.assertNotIn("dir/file1.txt", index_entries)
        self.assertIn("dir/subdir/file2.txt", index_entries)

    def test_checkout_current_branch_raises_error(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        with self.assertRaisesRegex(Exception, "Already on branch 'master'"):
            self.repo.checkout("master")

    def test_checkout_nonexistent_branch_raises_error(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        with self.assertRaises(FileNotFoundError): 
            self.repo.checkout("no-such-branch")

    def test_checkout_with_unstaged_changes_raises_error(self):
        self._write_file("file.txt", "v1")
        self.repo.add(["file.txt"])
        self.repo.commit("v1")
        self.repo.branch("develop")
        self._write_file("file.txt", "v2") 
        with self.assertRaisesRegex(Exception, "Please stash or commit your changes"):
            self.repo.checkout("develop")

    def test_checkout_with_staged_changes_raises_error(self):
        self._write_file("file.txt", "v1")
        self.repo.add(["file.txt"])
        self.repo.commit("v1")
        self.repo.branch("develop")
        self._write_file("file.txt", "v2")
        self.repo.add(["file.txt"]) 
        with self.assertRaisesRegex(Exception, "Please stash or commit your changes"):
            self.repo.checkout("develop")

    # ----- DIFF TESTS -----
    def test_diff_no_changes(self):
        """Tests 'diff' when index and worktree match."""
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        # No commit needed, index matches worktree
        
        diff_results = self.repo.diff()
        self.assertEqual([], diff_results, "Should be no diffs if index matches worktree")

    def test_diff_unstaged_modification(self):
        """Tests 'diff' for a modified file not staged."""
        self._write_file("file.txt", "v1")
        self.repo.add(["file.txt"])
        self.repo.commit("v1") # Commit v1
        
        self._write_file("file.txt", "v2") # Modify in worktree
        
        diff_results = self.repo.diff()
        
        self.assertEqual(1, len(diff_results))
        file_diff = diff_results[0]
        self.assertEqual("file.txt", file_diff.path)
        self.assertEqual("modified", file_diff.status)
        self.assertIsNotNone(file_diff.lines)
        self.assertTrue(len(file_diff.lines) > 0)
        # Check hashes - a should be index (v1), b should be worktree (v2)
        hash_v1 = self.repo.db.store(b"v1")
        hash_v2 = self.repo.db.store(b"v2")
        self.assertEqual(hash_v1, file_diff.hash_a)
        self.assertEqual(hash_v2, file_diff.hash_b)

    def test_diff_unstaged_deletion(self):
        """Tests 'diff' for a deleted file not staged."""
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("v1") # Commit the file
        hash_v1 = self.repo.db.store(b"content")

        os.remove("file.txt") # Delete from worktree, but don't 'rm'
        
        diff_results = self.repo.diff()

        self.assertEqual(1, len(diff_results))
        file_diff = diff_results[0]
        self.assertEqual("file.txt", file_diff.path)
        self.assertEqual("deleted", file_diff.status)
        self.assertIsNotNone(file_diff.lines) # Diff lib produces lines for deletion too
        self.assertEqual(hash_v1, file_diff.hash_a)
        self.assertIsNone(file_diff.hash_b)
        
    def test_diff_ignores_untracked_files(self):
        """Tests 'diff' ignores untracked files."""
        self._write_file("tracked.txt", "v1")
        self.repo.add(["tracked.txt"])
        self.repo.commit("v1")

        self._write_file("untracked.txt", "new") # Untracked file
        
        diff_results = self.repo.diff()
        self.assertEqual([], diff_results, "Default diff should ignore untracked files")

    # --- Tests for diff --staged ---

    def test_diff_staged_no_changes(self):
        """Tests 'diff --staged' when HEAD and index match."""
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("v1")
        # HEAD and index are identical after commit
        
        diff_results = self.repo.diff_staged()
        self.assertEqual([], diff_results)

    def test_diff_staged_new_file(self):
        """Tests 'diff --staged' for a newly staged file."""
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"]) # Stage the new file
        hash_v1 = self.repo.db.store(b"content")

        diff_results = self.repo.diff_staged() # Compare HEAD (None) vs Index (file.txt)
        self.assertEqual(1, len(diff_results))
        file_diff = diff_results[0]
        self.assertEqual("file.txt", file_diff.path)
        self.assertEqual("added", file_diff.status)
        self.assertIsNotNone(file_diff.lines)
        self.assertTrue(len(file_diff.lines) > 0)
        self.assertIsNone(file_diff.hash_a) # No hash in HEAD
        self.assertEqual(hash_v1, file_diff.hash_b) # Hash from Index

    def test_diff_staged_modification(self):
        """Tests 'diff --staged' for a staged modification."""
        self._write_file("file.txt", "v1")
        self.repo.add(["file.txt"])
        commit1_hash = self.repo.commit("v1")
        hash_v1 = self.repo.db.store(b"v1")

        self._write_file("file.txt", "v2")
        self.repo.add(["file.txt"]) # Stage v2
        hash_v2 = self.repo.db.store(b"v2")

        diff_results = self.repo.diff_staged() # Compare HEAD (v1) vs Index (v2)

        self.assertEqual(1, len(diff_results))
        file_diff = diff_results[0]
        self.assertEqual("file.txt", file_diff.path)
        self.assertEqual("modified", file_diff.status)
        self.assertIsNotNone(file_diff.lines)
        self.assertTrue(len(file_diff.lines) > 0)
        self.assertEqual(hash_v1, file_diff.hash_a) # Hash from HEAD
        self.assertEqual(hash_v2, file_diff.hash_b) # Hash from Index

    def test_diff_staged_deletion(self):
        """Tests 'diff --staged' for a staged deletion."""
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        commit1_hash = self.repo.commit("v1")
        hash_v1 = self.repo.db.store(b"content")
        
        self.repo.rm("file.txt") # Stage the deletion

        diff_results = self.repo.diff_staged() # Compare HEAD (file.txt) vs Index (empty)

        self.assertEqual(1, len(diff_results))
        file_diff = diff_results[0]
        self.assertEqual("file.txt", file_diff.path)
        self.assertEqual("deleted", file_diff.status)
        self.assertIsNotNone(file_diff.lines)
        self.assertEqual(hash_v1, file_diff.hash_a) # Hash from HEAD
        self.assertIsNone(file_diff.hash_b) # No hash in Index
        
if __name__ == '__main__':
    unittest.main()

