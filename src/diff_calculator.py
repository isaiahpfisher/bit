import difflib
from .file_diff import FileDiff
from .ref import Ref
from .tree import Tree

class DiffCalculator:
    """Calculates differences between repository states."""

    @classmethod
    def calculate_index_vs_worktree(cls, repo) -> list[FileDiff]:
        """
        Calculates and returns a list of Diffs between the index and the worktree (unstaged files).
        """
        index_entries = repo.index.load_as_dict()
        worktree_entries = repo.worktree.list_and_hash_files()
        
        return cls._calculate_original_vs_new(repo, index_entries, worktree_entries)
    
    @classmethod
    def calculate_index_vs_head(cls, repo) -> list[FileDiff]:
        """
        Calculates and returns a list of Diffs between the index and the last commit.
        """
        last_commit_hash = Ref.from_symbol(repo, 'HEAD').read_hash()
        head_entries = Tree.get_entries_from_commit(repo.db, last_commit_hash)
        index_entries = repo.index.load_as_dict()
        
        return cls._calculate_original_vs_new(repo, head_entries, index_entries, include_added_files=True)
    
    @classmethod
    def calculate_file_vs_file(cls, repo, path, hash_a, hash_b, n = 3) -> FileDiff:
        """
        Calculates and returns the file diff for the given hashes.
        """
        blob_a_bytes = repo.db.read(hash_a)
        blob_b_bytes = repo.db.read(hash_b)
        
        diff_lines = cls._generate_unified_diff(blob_a_bytes, blob_b_bytes, path, n)
        
        return FileDiff(
            path=path, 
            status='modified', 
            lines=diff_lines,
            hash_a=hash_a,
            hash_b=hash_b
            )

    # --- UTILS ---
    @classmethod
    def _calculate_original_vs_new(cls, repo, original, new, include_added_files=False):
        all_paths = set(original.keys()) | set(new.keys())
        results: list[FileDiff]  = []

        for path in sorted(list(all_paths)):
            hash_in_original = original.get(path)
            hash_in_new = new.get(path)

            if hash_in_original and not hash_in_new:
                blob_a_bytes = repo.db.read(hash_in_original)
                blob_b_bytes = "".encode("utf-8", errors="replace")
                
                diff_lines = cls._generate_unified_diff(blob_a_bytes, blob_b_bytes, path)
                
                results.append(FileDiff(
                    path=path, 
                    status='deleted', 
                    lines=diff_lines,
                    hash_a=hash_in_original,
                    hash_b=None
                ))
            elif include_added_files and not hash_in_original and hash_in_new:
                blob_a_bytes = "".encode("utf-8", errors="replace")
                blob_b_bytes = repo.worktree.read_file(path)
                
                diff_lines = cls._generate_unified_diff(blob_a_bytes, blob_b_bytes, path)
                
                results.append(FileDiff(
                    path=path, 
                    status='added', 
                    lines=diff_lines,
                    hash_a=hash_in_original,
                    hash_b=hash_in_new
                ))
            elif hash_in_original and hash_in_new and hash_in_original != hash_in_new:
                blob_a_bytes = repo.db.read(hash_in_original)
                blob_b_bytes = repo.worktree.read_file(path)
                
                diff_lines = cls._generate_unified_diff(blob_a_bytes, blob_b_bytes, path)
                
                results.append(FileDiff(
                    path=path, 
                    status='modified', 
                    lines=diff_lines,
                    hash_a=hash_in_original,
                    hash_b=hash_in_new
                ))

        return results
    
    @classmethod
    def _generate_unified_diff(cls, blob_a_bytes, blob_b_bytes, path, n = 3):
        """Generates raw unified diff lines between two blob contents (bytes)."""
        lines_a = blob_a_bytes.decode('utf-8', errors='replace').splitlines(keepends=True)
        lines_b = blob_b_bytes.decode('utf-8', errors='replace').splitlines(keepends=True)

        diff_generator = difflib.unified_diff(
            lines_a,
            lines_b,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm='\n',
            n=0
        )
        
        diff_lines = list(diff_generator)
        if diff_lines:
             return diff_lines[2:] 
        return []
