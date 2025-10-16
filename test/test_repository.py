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
    
    # ----- INIT -----
    def test_init_creates_repository_structure(self):      
        self.assertFalse(os.path.exists(self.repo.bit_dir))
        self.repo.init()

        self.assertTrue(os.path.isdir(self.repo.bit_dir))
        self.assertTrue(os.path.isdir(os.path.join(self.repo.bit_dir, 'objects')))
        self.assertTrue(os.path.isdir(os.path.join(self.repo.bit_dir, 'refs', 'heads')))

        head_path = os.path.join(self.repo.bit_dir, 'HEAD')
        self.assertTrue(os.path.exists(head_path))
        with open(head_path, 'r') as f:
            self.assertEqual("ref: refs/heads/master\n", f.read())

        self.assertTrue(self.repo.index.is_empty())

    def test_init_raises_error_if_repository_exists(self):
        self.repo.init()
        with self.assertRaises(FileExistsError):
            self.repo.init()
         
    # ----- ADD -----
    def test_add_stages_a_single_file(self):
        self.repo.init()
        file_content = 'hello world'
        with open("hello.txt", "w", encoding="utf-8") as f: f.write(file_content)    
        
        staged_count = self.repo.add(["hello.txt"])
        self.assertEqual(1, staged_count)
        
        expected_hash = '2aae6c35c94fcfb415dbe95f408b9ce91ee846ed'
        index_entries = self.repo.index.load()
        self.assertEqual(1, len(index_entries))
        self.assertEqual(expected_hash, index_entries[0]['hash'])
        self.assertEqual("hello.txt", index_entries[0]['path'])
    
    def test_add_raises_error_for_nonexistent_file(self):
        self.repo.init()
        with self.assertRaises(FileNotFoundError):
            self.repo.add(["nonexistent.txt"])

    def test_add_stages_multiple_files(self):
        self.repo.init()
        with open("file1.txt", "w") as f: f.write("one")
        with open("file2.txt", "w") as f: f.write("two")
        
        staged_count = self.repo.add(["file1.txt", "file2.txt"])
        self.assertEqual(2, staged_count)

        index_entries = self.repo.index.load()
        self.assertEqual(2, len(index_entries))
        self.assertIn("file1.txt", [e['path'] for e in index_entries])
        self.assertIn("file2.txt", [e['path'] for e in index_entries])

    def test_add_all_stages_all_files_in_worktree(self):
        self.repo.init()
        with open("file1.txt", "w") as f: f.write("one")
        os.makedirs("src")
        with open("src/file2.py", "w") as f: f.write("two")

        staged_count = self.repo.add_all()
        self.assertEqual(2, staged_count)

        index_entries = self.repo.index.load()
        self.assertEqual(2, len(index_entries))
        paths = {e['path'] for e in index_entries}
        self.assertIn("file1.txt", paths)
        self.assertIn("src/file2.py", paths)

    # ----- COMMIT -----       
    def test_commit_creates_initial_commit(self):
        self.repo.init()
        with open("README.md", "w", encoding="utf-8") as f: f.write("Welcome!")
        self.repo.add(["README.md"])

        commit_message = "Initial commit"
        commit_hash = self.repo.commit(commit_message)

        master_ref_path = os.path.join(self.repo.bit_dir, 'refs', 'heads', 'master')
        self.assertTrue(os.path.exists(master_ref_path))
        with open(master_ref_path, 'r') as f:
            self.assertEqual(commit_hash, f.read().strip())

        self.assertTrue(self.repo.index.is_empty())
        
        commit_content = self._read_object(commit_hash)
        self.assertIn(f"\n\n{commit_message}", commit_content)
        self.assertNotIn("parent ", commit_content)
            
    def test_commit_creates_subsequent_commit(self):
        self.repo.init()
        with open("file1.txt", "w") as f: f.write("first")
        self.repo.add(["file1.txt"])
        commit1_hash = self.repo.commit("First commit")

        with open("file2.txt", "w") as f: f.write("second")
        self.repo.add(["file2.txt"])
        commit2_hash = self.repo.commit("Second commit")
        
        commit2_content = self._read_object(commit2_hash)
        self.assertIn(f"parent {commit1_hash}", commit2_content)
        
    # ----- UTILS -----
    def _read_object(self, hash_val):
      path = os.path.join(self.repo.db.path, hash_val)
      with open(path, 'rb') as f:
          return f.read().decode('utf-8')
        
if __name__ == '__main__':
    unittest.main()
