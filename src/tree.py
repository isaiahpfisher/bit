class Tree:
    def __init__(self, entries):
        self.entries = entries
        self.hash = None

    def serialize(self):
        """Builds the byte string for storage from the entries list."""
        
        # must sort so that identical trees don't differ by order
        sorted_entries = sorted(self.entries, key=lambda e: e['name'])
        lines = []
        for entry in sorted_entries:
            lines.append(f"{entry['type']} {entry['hash']} {entry['name']}")
        
        return "\n".join(lines)

    @classmethod
    def build_from_index(cls, index, database):
        """
        Builds all trees from the index and returns the final, top-level Tree object.
        """
        index_entries = index.load()
        file_structure = cls._build_file_structure(index_entries)
        
        return cls._build_tree_recursive(file_structure, database)

    @classmethod
    def _build_tree_recursive(cls, tree_data, database):
        """
        Recursively builds Tree objects from the bottom up,
        stores them, and returns the fully constructed parent Tree object.
        """
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
    def _build_file_structure(index_entries):
        """Helper to create the nested dictionary from the flat index list."""
        file_structure = {}
        for entry in index_entries:
            path_components = entry['path'].split('/')
            current_level = file_structure
            for component in path_components[:-1]:
                current_level = current_level.setdefault(component, {})
            current_level[path_components[-1]] = {'type': 'blob', 'hash': entry['hash']}
            
        return file_structure

    @classmethod
    def parse(cls, raw_data):
        # For the 'log' command later, this would parse a tree object's
        # raw bytes back into a Tree object.
        pass