import os
from .commit import Commit

class Tree:
    def __init__(self, entries):
        self.entries = entries
        self.hash = None

    def serialize(self):
        sorted_entries = sorted(self.entries, key=lambda e: e['name'])
        lines = []
        for entry in sorted_entries:
            lines.append(f"{entry['type']} {entry['hash']} {entry['name']}")
        return "\n".join(lines)

    @classmethod
    def build_from_index(cls, index, database):
        index_entries_dict = index.load_as_dict()
        file_structure = cls._build_file_structure(index_entries_dict)
        return cls._build_tree_recursive(file_structure, database)
    
    @classmethod
    def _build_tree_recursive(cls, tree_data, database):
        entries = []
        for name, data in tree_data.items():
            if 'type' in data and data['type'] == 'blob':
                entries.append({'type': 'blob', 'hash': data['hash'], 'name': name})
            else:
                subtree = cls._build_tree_recursive(data, database)
                entries.append({'type': 'tree', 'hash': subtree.hash, 'name': name})
        
        tree = Tree(entries)
        tree_content = tree.serialize()
        tree.hash = database.store(tree_content)
        return tree

    @staticmethod
    def _build_file_structure(index_entries_dict):
        """
        Helper to create the nested dictionary from a flat dictionary of {path: hash}.
        """
        file_structure = {}
        for path, hash_val in index_entries_dict.items():
            path_components = path.split('/')
            current_level = file_structure
            for component in path_components[:-1]:
                current_level = current_level.setdefault(component, {})
            current_level[path_components[-1]] = {'type': 'blob', 'hash': hash_val}
            
        return file_structure

    @classmethod
    def get_entries_from_commit(cls, database, commit_hash):
        """Reads a commit and starts walking the commit tree."""
        if commit_hash is None:
            return {}
            
        commit_data_bytes = database.read(commit_hash)
        commit = Commit.parse(commit_data_bytes)
        root_tree_hash = commit.tree_hash
        
        return cls._walk_tree(database, root_tree_hash, "")

    @classmethod
    def _walk_tree(cls, database, tree_hash, current_path):
        """Recursively walks tree objects to build a flat dict of {path: hash}."""
        entries = {}
        tree_content_bytes = database.read(tree_hash)
        tree_content = tree_content_bytes.decode('utf-8')

        for line in tree_content.splitlines():
            type, hash_val, name = line.split(' ', 2)
            path = os.path.join(current_path, name).replace(os.sep, '/')

            if type == 'blob':
                entries[path] = hash_val
            elif type == 'tree':
                sub_entries = cls._walk_tree(database, hash_val, path)
                entries.update(sub_entries)
        
        return entries

