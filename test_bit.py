import unittest
import os
import shutil
import tempfile
from .bit import init, add

class TestBit(unittest.TestCase):

    def setUp(self):
        """
        Creates a temporary directory to act as the test repository.
        """
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """
        Cleans up the temporary directory.
        """
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    # --- Tests for the 'init' command ---

    def test_init_creates_bit_directory(self):
        """Test that init creates the .bit directory and subdirectories."""
        self.assertFalse(os.path.exists('.bit'))
        init()
        self.assertTrue(os.path.isdir('.bit'))
        self.assertTrue(os.path.isdir(os.path.join('.bit', 'objects')))

    def test_init_creates_core_files(self):
        """Test that init creates HEAD and an empty index."""
        init()
        self.assertTrue(os.path.exists(os.path.join('.bit', 'HEAD')))
        self.assertTrue(os.path.exists(os.path.join('.bit', 'index')))
        self.assertEqual(os.path.getsize(os.path.join('.bit', 'index')), 0)

    def test_init_head_content(self):
        """Test that the HEAD file has the correct initial content."""
        init()
        with open(os.path.join('.bit', 'HEAD'), 'r') as f:
            self.assertEqual(f.read(), "ref: refs/heads/master\n")

    def test_init_returns_false_if_repo_exists(self):
        """Test that calling init twice fails the second time."""
        self.assertTrue(init()) 
        self.assertFalse(init())

    # --- Tests for the 'add' command ---

    def test_add_creates_blob_for_new_file(self):
        """Test that add creates a blob object with the correct hash."""
        init()
        file_content = b"hello world"
        sha1_hash = "2aae6c35c94fcfb415dbe95f408b9ce91ee846ed"
        with open("hello.txt", "wb") as f:
            f.write(file_content)

        add("hello.txt")

        blob_path = os.path.join('.bit', 'objects', sha1_hash)
        self.assertTrue(os.path.exists(blob_path))
        with open(blob_path, 'rb') as f:
            self.assertEqual(f.read(), file_content)

    def test_add_updates_index(self):
        """Test that add correctly adds an entry to the index file."""
        init()
        with open("test.txt", "w") as f:
            f.write("test content")

        add("test.txt")

        expected_hash = "1eebdf4fdc9fc7bf283031b93f9aef3338de9052"

        with open(os.path.join('.bit', 'index'), 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0].strip(), f"{expected_hash} test.txt")

    def test_add_updates_existing_entry_in_index(self):
        """Test that adding a modified file updates its hash in the index."""
        init()
        # Add the file once
        with open("file.txt", "w") as f: f.write("original")
        add("file.txt")

        # Modify the file and add it again
        with open("file.txt", "w") as f: f.write("modified")
        add("file.txt")

        # Hash for modified file
        expected_hash_modified = "99db324742823c55d975b605e1fc22f4253a9b7d"
        with open(os.path.join('.bit', 'index'), 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0].strip(), f"{expected_hash_modified} file.txt")

    def test_add_fails_for_bad_file_path(self):
        """Test that adding a file path that doesn't exist fails."""
        init()
        self.assertFalse(add("file_that_does_not_exist.txt"))


if __name__ == '__main__':
    unittest.main()
