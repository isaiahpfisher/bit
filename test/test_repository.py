import unittest
import os
import shutil
import tempfile

# Adjust the Python path to import from the 'src' directory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.repository import Repository
from src.commit import Commit # Needed for log tests
from src.config import Config
# Need FileDiff to check results

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

    # ----- INIT TESTS -----
    def test_init_creates_repository_structure(self):      
        self.assertTrue(os.path.isdir(self.repo.bit_dir))
        self.assertTrue(os.path.isdir(os.path.join(self.repo.bit_dir, 'objects')))
        self.assertEqual("master", self._read_head_branch())
        self.assertTrue(self.repo.index.is_empty())

    # ----- ADD / RM / ADD_ALL / COMMIT -----
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
        commit_content = self._read_object_str(commit_hash)
        self.assertIn("\n\nInitial commit", commit_content)
        self.assertNotIn("parent ", commit_content)
            
    def test_commit_creates_subsequent_commit(self):
        self._write_file("file1.txt", "first")
        self.repo.add(["file1.txt"])
        commit1_hash = self.repo.commit("First commit")
        self._write_file("file2.txt", "second")
        self.repo.add(["file2.txt"])
        commit2_hash = self.repo.commit("Second commit")
        commit2_content = self._read_object_str(commit2_hash)
        self.assertIn(f"parent {commit1_hash}", commit2_content)

    # ----- STATUS TESTS -----
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

    # ----- LOG TESTS -----
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
        self.assertEqual([], log_entry.commit.parent_hashes)
        current_branch = self._read_head_branch()
        self.assertEqual("master", current_branch) 
        self.assertIn("master", log_entry.refs)

    # ----- BRANCH TESTS -----
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

    # ----- CHECKOUT TESTS -----
    def test_checkout_updates_head(self):
        self._write_file("file.txt", "content")
        self.repo.add(["file.txt"])
        self.repo.commit("Initial commit")
        self.repo.branch("develop")
        self.repo.checkout("develop")
        self.assertEqual("develop", self._read_head_branch())

    # ----- MERGE TESTS -----
    def test_merge_fast_forward(self):
        """Tests that a merge is handled as a fast-forward when possible."""
        self._write_file("file.txt", "initial")
        self.repo.add_all()
        self.repo.commit("initial")
        self.repo.branch("feature")
        
        self.repo.checkout("feature")
        self._write_file("file.txt", "feature change")
        self.repo.add_all()
        feature_hash = self.repo.commit("feature commit")
        
        self.repo.checkout("master")
        self.repo.merge("feature")
        
        # In fast-forward, master should now point to feature's commit
        self.assertEqual(feature_hash, self._get_branch_hash("master"))
        self.assertEqual("feature change", self._read_worktree_file_str("file.txt"))

    def test_merge_automatic_3way_success(self):
        """Tests a non-conflicting 3-way merge that creates an automatic commit."""
        self._write_file("common.txt", "base content")
        self.repo.add_all()
        self.repo.commit("base commit")
        self.repo.branch("side")
        
        # Change file A on master
        self._write_file("master_only.txt", "master")
        self.repo.add_all()
        master_parent = self.repo.commit("master change")
        
        # Change file B on side
        self.repo.checkout("side")
        self._write_file("side_only.txt", "side")
        self.repo.add_all()
        side_parent = self.repo.commit("side change")
        
        # Merge side into master
        self.repo.checkout("master")
        self.repo.merge("side")
        
        # Verify automatic commit creation
        head_hash = self._get_branch_hash("master")
        commit_bytes = self.repo.db.read(head_hash)
        merge_commit = Commit.parse(commit_bytes)
        
        # Verify the merge commit has exactly two parents
        self.assertEqual(len(merge_commit.parent_hashes), 2)
        self.assertIn(master_parent, merge_commit.parent_hashes)
        self.assertIn(side_parent, merge_commit.parent_hashes)
        
        # Verify files from both branches are present
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "master_only.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "side_only.txt")))

    def test_merge_conflict_aborts(self):
        """Tests that a conflict at the hunk level raises an exception and doesn't modify state."""
        self._write_file("conflict.txt", "line1\nline2\n")
        self.repo.add_all()
        self.repo.commit("base")
        self.repo.branch("side")
        
        # Modify line 1 on master
        self._write_file("conflict.txt", "master change\nline2\n")
        self.repo.add_all()
        self.repo.commit("master edit")
        
        # Modify line 1 on side (Hunk conflict)
        self.repo.checkout("side")
        self._write_file("conflict.txt", "side change\nline2\n")
        self.repo.add_all()
        self.repo.commit("side edit")
        
        self.repo.checkout("master")
        from exceptions.merge_conflict import MergeConflict
        
        # The merge should raise the custom Exception and NOT create a commit
        with self.assertRaises(MergeConflict):
            self.repo.merge("side")
            
        # Verify MERGE_HEAD was not left behind (atomic abort)
        self.assertFalse(os.path.exists(os.path.join(self.repo.bit_dir, 'MERGE_HEAD')))
        # Verify the worktree is still at the 'master edit' state
        self.assertEqual("master change\nline2\n", self._read_worktree_file_str("conflict.txt"))

    def test_merge_log_display(self):
        """Tests that logs correctly identify and format merge commits."""
        self._write_file("a.txt", "base")
        self.repo.add_all()
        self.repo.commit("base")
        self.repo.branch("side")
        
        self._write_file("b.txt", "master")
        self.repo.add_all()
        self.repo.commit("master commit")
        
        self.repo.checkout("side")
        self._write_file("c.txt", "side")
        self.repo.add_all()
        self.repo.commit("side commit")
        
        self.repo.checkout("master")
        self.repo.merge("side")
        
        logs = self.repo.log()
        # The first log entry should be the merge commit
        merge_log_text = logs[0].format()
        self.assertIn("Merge:", merge_log_text)
        self.assertIn("Merge branch 'side'", merge_log_text)
        
    def test_merge_content_no_conflict(self):
        """Tests that two different changes to the same file are merged automatically."""
        # 1. Setup a file with several lines
        initial_content = "Line 1: Header\nLine 2: Middle\nLine 3: Footer\n"
        self._write_file("file.txt", initial_content)
        self.repo.add_all()
        self.repo.commit("base")
        self.repo.branch("side")
        
        # 2. Master branch modifies the Header (Line 1)
        master_content = "Line 1: MASTER EDIT\nLine 2: Middle\nLine 3: Footer\n"
        self._write_file("file.txt", master_content)
        self.repo.add_all()
        self.repo.commit("master edit")
        
        # 3. Side branch modifies the Footer (Line 3)
        self.repo.checkout("side")
        side_content = "Line 1: Header\nLine 2: Middle\nLine 3: SIDE EDIT\n"
        self._write_file("file.txt", side_content)
        self.repo.add_all()
        self.repo.commit("side edit")
        
        # 4. Perform the merge on Master
        self.repo.checkout("master")
        result = self.repo.merge("side")
        
        # 5. Verify Success status and automatic commit
        self.assertTrue(result.startswith("MERGE_SUCCESS:"))
        
        # 6. Check that the final file content has BOTH edits
        # Note: Depending on your diff implementation, it might or might not have trailing newlines
        expected_merged = "Line 1: MASTER EDIT\nLine 2: Middle\nLine 3: SIDE EDIT\n"
        actual_content = self._read_worktree_file_str("file.txt")
        self.assertEqual(actual_content, expected_merged)

    def test_merge_identical_changes(self):
        """Tests that if both branches make the EXACT same change, it merges cleanly."""
        self._write_file("file.txt", "base content\n")
        self.repo.add_all()
        self.repo.commit("base")
        self.repo.branch("side")
        
        # Master changes content
        self._write_file("file.txt", "new content\n")
        self.repo.add_all()
        self.repo.commit("master change")
        
        # Side makes the exact same change
        self.repo.checkout("side")
        self._write_file("file.txt", "new content\n")
        self.repo.add_all()
        self.repo.commit("side change")
        
        self.repo.checkout("master")
        result = self.repo.merge("side")
        
        self.assertTrue(result.startswith("MERGE_SUCCESS:"))
        self.assertEqual("new content\n", self._read_worktree_file_str("file.txt"))

    def test_merge_complex_content_stitching(self):
        """Tests merging multiple non-overlapping hunks from both sides."""
        base_lines = [f"Line {i}\n" for i in range(1, 11)] # 10 lines
        self._write_file("big_file.txt", "".join(base_lines))
        self.repo.add_all()
        self.repo.commit("base")
        self.repo.branch("side")
        
        # Master modifies lines 1 and 10
        master_lines = base_lines[:]
        master_lines[0] = "MASTER 1\n"
        master_lines[9] = "MASTER 10\n"
        self._write_file("big_file.txt", "".join(master_lines))
        self.repo.add_all()
        self.repo.commit("master")
        
        # Side modifies line 5
        self.repo.checkout("side")
        side_lines = base_lines[:]
        side_lines[4] = "SIDE 5\n"
        self._write_file("big_file.txt", "".join(side_lines))
        self.repo.add_all()
        self.repo.commit("side")
        
        self.repo.checkout("master")
        self.repo.merge("side")
        
        # Result should have all three modifications
        final_content = self._read_worktree_file_str("big_file.txt")
        self.assertIn("MASTER 1\n", final_content)
        self.assertIn("SIDE 5\n", final_content)
        self.assertIn("MASTER 10\n", final_content)
        self.assertIn("Line 3\n", final_content) # Unchanged line
        
    def test_reset_soft(self):
        self._write_file("file.txt", "v1")
        self.repo.add_all()
        commit1_hash = self.repo.commit("v1")
        
        self._write_file("file.txt", "v2")
        self.repo.add_all()
        commit2_hash = self.repo.commit("v2")
        
        self.repo.reset(commit1_hash, mode="--soft")
        
        self.assertEqual(commit1_hash, self._get_branch_hash("master"))
        
        index_entries = self.repo.index.load_as_dict()
        hash_v2 = self.repo.db.store(b"v2")
        self.assertEqual(hash_v2, index_entries["file.txt"])
        
        self.assertEqual("v2", self._read_worktree_file_str("file.txt"))

    def test_reset_mixed(self):
        self._write_file("file.txt", "v1")
        self.repo.add_all()
        commit1_hash = self.repo.commit("v1")
        
        self._write_file("file.txt", "v2")
        self.repo.add_all()
        commit2_hash = self.repo.commit("v2")
        
        self.repo.reset(commit1_hash, mode="--mixed")
        
        self.assertEqual(commit1_hash, self._get_branch_hash("master"))
        
        index_entries = self.repo.index.load_as_dict()
        hash_v1 = self.repo.db.store(b"v1")
        self.assertEqual(hash_v1, index_entries["file.txt"])
        
        self.assertEqual("v2", self._read_worktree_file_str("file.txt"))

    def test_reset_hard(self):
        self._write_file("file.txt", "v1")
        self.repo.add_all()
        commit1_hash = self.repo.commit("v1")
        
        self._write_file("file.txt", "v2")
        self.repo.add_all()
        commit2_hash = self.repo.commit("v2")
        
        self.repo.reset(commit1_hash, mode="--hard")
        
        self.assertEqual(commit1_hash, self._get_branch_hash("master"))
        
        index_entries = self.repo.index.load_as_dict()
        hash_v1 = self.repo.db.store(b"v1")
        self.assertEqual(hash_v1, index_entries["file.txt"])
        
        self.assertEqual("v1", self._read_worktree_file_str("file.txt"))

    def test_reset_to_branch_name(self):
        self._write_file("file.txt", "base")
        self.repo.add_all()
        self.repo.commit("base")
        self.repo.branch("other")
        
        self._write_file("file.txt", "master_change")
        self.repo.add_all()
        self.repo.commit("master_change")
        
        self.repo.reset("other", mode="--hard")
        
        other_hash = self._get_branch_hash("other")
        self.assertEqual(other_hash, self._get_branch_hash("master"))
        self.assertEqual("base", self._read_worktree_file_str("file.txt"))

    def test_reset_hard_removes_new_files(self):
        self._write_file("file1.txt", "v1")
        self.repo.add_all()
        commit1_hash = self.repo.commit("v1")
        
        self._write_file("file2.txt", "v2")
        self.repo.add_all()
        self.repo.commit("v2")
        
        self.repo.reset(commit1_hash, mode="--hard")
        
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "file2.txt")))
        index_entries = self.repo.index.load_as_dict()
        self.assertNotIn("file2.txt", index_entries)
        
    # ----- IGNORE TESTS -----
    def test_ignore_basic_filename(self):
        """Tests that a specific filename in .bitignore is ignored."""
        self._write_file(".bitignore", "ignored.txt")
        self._write_file("ignored.txt", "should not see me")
        self._write_file("tracked.txt", "see me")
        
        status = self.repo.status()
        self.assertNotIn("ignored.txt", status.untracked)
        self.assertIn("tracked.txt", status.untracked)

    def test_ignore_wildcard_extension(self):
        """Tests that wildcard patterns like *.log are ignored."""
        self._write_file(".bitignore", "*.log")
        self._write_file("error.log", "error data")
        self._write_file("app.log", "app data")
        self._write_file("README.md", "info")
        
        status = self.repo.status()
        self.assertNotIn("error.log", status.untracked)
        self.assertNotIn("app.log", status.untracked)
        self.assertIn("README.md", status.untracked)

    def test_ignore_directory(self):
        """Tests that an entire directory and its contents are ignored."""
        self._write_file(".bitignore", "temp/")
        self._write_file("temp/file1.tmp", "temp")
        self._write_file("temp/sub/file2.tmp", "temp")
        self._write_file("keep.txt", "keep")
        
        # Verify list_files doesn't descend into temp/
        files = self.repo.worktree.list_files()
        self.assertIn("keep.txt", files)
        self.assertNotIn("temp/file1.tmp", files)
        self.assertNotIn("temp/sub/file2.tmp", files)
        
        status = self.repo.status()
        self.assertNotIn("temp/file1.tmp", status.untracked)

    def test_ignore_anchored_path(self):
        """Tests that a leading slash anchors the pattern to the root."""
        self._write_file(".bitignore", "/root_only.txt")
        self._write_file("root_only.txt", "ignore me")
        self._write_file("subdir/root_only.txt", "track me")
        
        status = self.repo.status()
        self.assertNotIn("root_only.txt", status.untracked)
        # Depending on your regex logic, this verifies the anchor works
        self.assertIn("subdir/root_only.txt", status.untracked)

    def test_ignore_comments_and_empty_lines(self):
        """Tests that comments and whitespace in .bitignore are handled."""
        content = (
            "# This is a comment\n"
            "\n"
            "  \n"
            "ignored.txt\n"
        )
        self._write_file(".bitignore", content)
        self._write_file("ignored.txt", "ignore")
        self._write_file("normal.txt", "track")
        
        status = self.repo.status()
        self.assertNotIn("ignored.txt", status.untracked)
        self.assertIn("normal.txt", status.untracked)

    def test_internal_bit_dir_always_ignored(self):
        """Ensures the .bit directory is never tracked even without a .bitignore."""
        # Create a dummy file inside .bit (though Repository.init already creates files)
        self._write_file(".bit/config", "some config")
        
        status = self.repo.status()
        for path in status.untracked:
            self.assertFalse(path.startswith(".bit"), f"Found internal file in status: {path}")
            
    # ----- RESTORE TESTS -----
    def test_restore_worktree_reverts_to_index(self):
        """Tests bit restore <file> reverts worktree to match the index."""
        self._write_file("file.txt", "index version")
        self.repo.add(["file.txt"])
        
        # Modify the file in the worktree
        self._write_file("file.txt", "dirty version")
        self.assertEqual("dirty version", self._read_worktree_file_str("file.txt"))
        
        # Restore from index
        self.repo.restore(["file.txt"], staged=False)
        
        # Verify it matches index version
        self.assertEqual("index version", self._read_worktree_file_str("file.txt"))

    def test_restore_staged_reverts_index_to_head(self):
        """Tests bit restore --staged <file> reverts index to match HEAD."""
        self._write_file("file.txt", "head version")
        self.repo.add(["file.txt"])
        self.repo.commit("initial")
        
        # Modify and stage a new version
        self._write_file("file.txt", "staged version")
        self.repo.add(["file.txt"])
        
        # Unstage the file
        self.repo.restore(["file.txt"], staged=True)
        
        # Verify index now matches HEAD hash
        index_entries = self.repo.index.load_as_dict()
        head_hash = self.repo.db.hash_content("head version")
        self.assertEqual(head_hash, index_entries["file.txt"])
        
        # Verify worktree is still "staged version" (not overwritten)
        self.assertEqual("staged version", self._read_worktree_file_str("file.txt"))

    def test_restore_staged_new_file_removes_from_index(self):
        """Tests bit restore --staged on a new file removes it from the index."""
        self._write_file("new.txt", "content")
        self.repo.add(["new.txt"])
        
        # Unstage a file that doesn't exist in HEAD
        self.repo.restore(["new.txt"], staged=True)
        
        index_entries = self.repo.index.load_as_dict()
        self.assertNotIn("new.txt", index_entries)
        # File should still exist in worktree
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "new.txt")))

    def test_restore_multiple_files(self):
        """Tests restoring multiple files at once."""
        self._write_file("a.txt", "base a")
        self._write_file("b.txt", "base b")
        self.repo.add_all()
        
        self._write_file("a.txt", "dirty a")
        self._write_file("b.txt", "dirty b")
        
        self.repo.restore(["a.txt", "b.txt"], staged=False)
        
        self.assertEqual("base a", self._read_worktree_file_str("a.txt"))
        self.assertEqual("base b", self._read_worktree_file_str("b.txt"))
        
    # ----- STASH TESTS -----
    def test_stash_push_cleans_worktree(self):
        """Tests that stash push saves changes and resets the worktree."""
        self._write_file("file.txt", "v1")
        self.repo.add_all()
        self.repo.commit("initial")
        
        # Modify file and add a new one
        self._write_file("file.txt", "v2")
        self._write_file("new.txt", "stashed")
        
        self.repo.stash_push("my changes")
        
        # Worktree should be back to v1 and new.txt should be gone
        self.assertEqual("v1", self._read_worktree_file_str("file.txt"))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "new.txt")))
        
        # Stash ref should exist
        stash_ref_path = os.path.join(self.repo.bit_dir, 'refs', 'stash')
        self.assertTrue(os.path.exists(stash_ref_path))

    def test_stash_pop_restores_changes(self):
        """Tests that stash pop re-applies the saved changes."""
        self._write_file("file.txt", "v1")
        self.repo.add_all()
        self.repo.commit("initial")
        
        self._write_file("file.txt", "v2")
        self.repo.stash_push()
        
        self.repo.stash_pop()
        
        self.assertEqual("v2", self._read_worktree_file_str("file.txt"))
        # Stash ref should be removed if it was the last one
        stash_ref_path = os.path.join(self.repo.bit_dir, 'refs', 'stash')
        self.assertFalse(os.path.exists(stash_ref_path))

    def test_stash_list_multiple_entries(self):
        """Tests that multiple stashes form a stack."""
        self._write_file("f.txt", "base")
        self.repo.add_all()
        self.repo.commit("base")
        
        # First stash
        self._write_file("f.txt", "change 1")
        self.repo.stash_push("first")
        
        # Second stash
        self._write_file("f.txt", "change 2")
        self.repo.stash_push("second")
        
        stashes = self.repo.stash_list()
        self.assertEqual(len(stashes), 2)
        # Most recent should be at index 0
        self.assertEqual(stashes[0]['message'], "second")
        self.assertEqual(stashes[1]['message'], "first")

    def test_stash_pop_on_different_branch(self):
        """Tests that a stash can be popped onto a different branch (3-way merge)."""
        self._write_file("common.txt", "base")
        self.repo.add_all()
        self.repo.commit("base")
        
        self.repo.branch("other")
        
        # Change common.txt and stash it
        self._write_file("common.txt", "stashed change")
        self.repo.stash_push()
        
        # Switch to 'other' and make a different change
        self.repo.checkout("other")
        self._write_file("new_file.txt", "I am new")
        self.repo.add_all()
        self.repo.commit("other commit")
        
        # Pop the stash onto 'other'
        self.repo.stash_pop()
        
        self.assertEqual("stashed change", self._read_worktree_file_str("common.txt"))
        self.assertEqual("I am new", self._read_worktree_file_str("new_file.txt"))

    def test_stash_pop_conflicts_raises_error(self):
        """Tests that conflicting changes during pop raise MergeConflict."""
        self._write_file("conflict.txt", "base")
        self.repo.add_all()
        self.repo.commit("base")
        
        # Stash a change to line 1
        self._write_file("conflict.txt", "stash change")
        self.repo.stash_push()
        
        # Commit a different change to line 1
        self._write_file("conflict.txt", "manual change")
        self.repo.add_all()
        self.repo.commit("manual commit")
        
        from exceptions.merge_conflict import MergeConflict
        with self.assertRaises(MergeConflict):
            self.repo.stash_pop()

    def test_stash_pop_fails_if_worktree_dirty(self):
        """Tests that stash pop prevents overwriting uncommitted local changes."""
        self._write_file("f.txt", "base")
        self.repo.add_all()
        self.repo.commit("base")
        
        self._write_file("f.txt", "stashed")
        self.repo.stash_push()
        
        # Make worktree dirty
        self._write_file("dirty.txt", "dirty")
        
        # Depending on your implementation, this should either fail or 
        # the implementation should be updated to check status().is_clean()
        with self.assertRaises(Exception):
            self.repo.stash_pop()
            
    # ----- CLONE TESTS -----
    def test_clone_basic(self):
        """Tests that cloning a repository replicates the worktree and history."""
        # 1. Setup a source repository with content
        source_path = os.path.join(self.test_dir, "source_repo")
        os.makedirs(source_path)
        source_repo = Repository(source_path)
        source_repo.init()
        
        # Create a file and commit it
        with open(os.path.join(source_path, "hello.txt"), "w") as f:
            f.write("hello world")
        source_repo.add_all()
        source_repo.commit("initial commit")
        
        # 2. Perform the clone
        dest_path = os.path.join(self.test_dir, "cloned_repo")
        from commands.clone import CloneCommand
        # Instantiate and run the command
        clone_cmd = CloneCommand(self.repo, [source_path, dest_path])
        clone_cmd.run(print_output=False)
        
        # 3. Verify destination
        self.assertTrue(os.path.isdir(dest_path))
        self.assertTrue(os.path.isdir(os.path.join(dest_path, ".bit")))
        
        # Verify the file was checked out
        cloned_file = os.path.join(dest_path, "hello.txt")
        self.assertTrue(os.path.exists(cloned_file))
        with open(cloned_file, "r") as f:
            self.assertEqual(f.read(), "hello world")
            
        # Verify the history is present
        cloned_repo = Repository(dest_path)
        logs = cloned_repo.log()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].commit.message, "initial commit")

    def test_clone_multiple_branches(self):
        """Tests that all branches are copied during a clone."""
        source_path = os.path.join(self.test_dir, "source_multi")
        os.makedirs(source_path)
        source_repo = Repository(source_path)
        source_repo.init()
        
        # Commit to master
        with open(os.path.join(source_path, "master.txt"), "w") as f: f.write("m")
        source_repo.add_all()
        source_repo.commit("master commit")
        
        # Create and commit to another branch
        source_repo.branch("develop")
        source_repo.checkout("develop")
        with open(os.path.join(source_path, "dev.txt"), "w") as f: f.write("d")
        source_repo.add_all()
        source_repo.commit("dev commit")
        
        # Clone it
        dest_path = os.path.join(self.test_dir, "cloned_multi")
        from commands.clone import CloneCommand
        CloneCommand(self.repo, [source_path, dest_path]).run(print_output=False)
        
        cloned_repo = Repository(dest_path)
        branches = cloned_repo.list_branches()
        
        self.assertIn("master", branches)
        self.assertIn("develop", branches)
        self.assertEqual(cloned_repo.current_branch(), "develop")

    def test_clone_invalid_source_fails(self):
        """Tests that cloning from a non-existent or non-bit directory fails."""
        invalid_source = os.path.join(self.test_dir, "not_a_repo")
        os.makedirs(invalid_source) # Dir exists but no .bit inside
        
        dest_path = os.path.join(self.test_dir, "should_fail")
        
        from commands.clone import CloneCommand
        # Redirect stderr to capture the error message
        import io
        from contextlib import redirect_stderr
        
        f = io.StringIO()
        with redirect_stderr(f):
            CloneCommand(self.repo, [invalid_source, dest_path]).run(print_output=False)
            
        self.assertIn("does not appear to be a bit repository", f.getvalue())
        self.assertFalse(os.path.exists(dest_path))

    def test_config_set_and_get_local(self):
        """Tests setting a value in the local repository config."""
        config = Config(self.repo)
        config.set("user", "name", "Isaiah")
        
        # Verify it can be retrieved
        self.assertEqual(config.get("user", "name"), "Isaiah")
        
        # Verify file exists in .bit/config
        local_config_path = os.path.join(self.repo.bit_dir, "config")
        self.assertTrue(os.path.exists(local_config_path))

    def test_local_overrides_global(self):
        """Tests that local config values take precedence over global ones."""
        config = Config(self.repo)
        
        # Manually point global_path to a temp file for testing
        config.global_path = os.path.join(self.test_dir, ".bitconfig_test")
        
        config.set("user", "email", "global@example.com", global_flag=True)
        config.set("user", "email", "local@example.com", global_flag=False)
        
        self.assertEqual(config.get("user", "email"), "local@example.com")
        
if __name__ == '__main__':
    unittest.main()