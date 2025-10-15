import os
import sys
import hashlib
import time

# --- Core ---

def init():
    """
    Initializes a new Bit repository by creating the .bit directory structure.
    """
    bit_dir = os.path.join(os.getcwd(), '.bit')
    if os.path.exists(bit_dir):
        return False

    os.makedirs(os.path.join(bit_dir, "objects"))
    os.makedirs(os.path.join(bit_dir, "refs", "head"), exist_ok=True)
    with open(os.path.join(bit_dir, "HEAD"), "w") as file:
        file.write("ref: refs/heads/master\n")
    open(os.path.join(bit_dir, "index"), "w").close()

    print(f"Initialized empty Bit repository in {bit_dir}")
    return True

def add(file_path):
    """
    Stages a file by creating a blob and updating the index.
    Assumes the CWD is the root of the repository.
    """
    repo_root = os.getcwd()
    bit_dir = os.path.join(repo_root, '.bit')

    if not os.path.exists(file_path):
        sys.stderr.write(f"Error: file not found: {file_path}\n")
        return False

    # read the file
    with open(file_path, 'rb') as file:
        file_content = file.read()

    # create hash/blob
    hash_value = hashlib.sha1(file_content).hexdigest()
    with open(os.path.join(bit_dir, "objects", hash_value), "wb") as file:
        file.write(file_content)

    # update/add to the index
    index_path = os.path.join(bit_dir, "index")
    index = {}
    if os.path.getsize(index_path) > 0:
        with open(index_path, 'r') as file:
            for line in file:
                sha1, path = line.strip().split(' ', 1)
                index[path] = sha1

    relative_path_os = os.path.relpath(os.path.abspath(file_path), repo_root)
    relative_path = relative_path_os.replace(os.sep, '/')
    index[relative_path] = hash_value

    with open(index_path, 'w', encoding='utf-8') as file:
      for path, sha1 in sorted(index.items()):
          file.write(f"{sha1} {path}\n")

def commit(message):
    """
    Commits any staged changes.
    """

    repo_root = os.getcwd()
    bit_dir = os.path.join(repo_root, '.bit')
    index_path = os.path.join(bit_dir, 'index')
    objects_path = os.path.join(bit_dir, 'objects')

    # check if index file is empty
    if os.path.getsize(index_path) == 0:
        print(f"Aborted: No changes to commit.")
        return False

    # read index file to dictionary
    index = {}
    with open(index_path, 'r') as file:
      for line in file:
        sha1, path = line.strip().split(' ', 1)
        index[path] = sha1

    # get hash of root tree
    file_structure = build_file_structure(index)
    root_tree_hash = build_tree(file_structure)
    
    # write commit object
    commit_contents = f"tree {root_tree_hash}\n"
    
    with open(os.path.join(bit_dir, 'HEAD'), 'r') as file:
        ref_path = file.read().strip().split(' ')[1]
        branch_head_path = os.path.join(bit_dir, ref_path)
        if (os.path.exists(branch_head_path)):
          with open(branch_head_path, 'r') as file:
              parent_commit_hash = file.read().strip()
              commit_contents += f"parent {parent_commit_hash}\n"
    
        
    name = os.environ.get("GIT_AUTHOR_NAME", "Isaiah Fisher")
    email = os.environ.get("GIT_AUTHOR_EMAIL", "isaiahpfisher@gmail.com")
    timestamp = int(time.time())
    timezone_offset = time.strftime('%z')
    commit_contents += f"author {name} <{email}> {timestamp} {timezone_offset}\n"
    commit_contents += f"committer {name} <{email}> {timestamp} {timezone_offset}\n\n"
    
    commit_contents += message
    
    commit_hash = hashlib.sha1(commit_contents.encode('utf-8')).hexdigest()
    with open(os.path.join(objects_path, commit_hash), 'wb') as file:
        file.write(commit_contents.encode('utf-8'))
    
    # update the branch head
    os.makedirs(os.path.dirname(branch_head_path), exist_ok=True)
    with open(branch_head_path, "wb") as file:
        file.write(commit_hash.encode("utf-8"))
      
    # clear index file
    open(index_path, 'w').close()
    
        
def build_tree(file_structure):
    repo_root = os.getcwd()
    bit_dir = os.path.join(repo_root, '.bit')
    objects_path = os.path.join(bit_dir, 'objects')
    contents = ""

    for obj, value in file_structure.items():
        if value['type'] == 'tree':
            tree_hash = build_tree(value['children'])
            contents += f"tree {tree_hash} {obj}\n"
        else:
            contents += f"blob {value['hash']} {obj}\n"
            
          
    
    hash_value = hashlib.sha1(contents.encode('utf-8')).hexdigest()
    with open(os.path.join(objects_path, hash_value), 'wb') as file:
        file.write(contents.encode("utf-8"))
        
    return hash_value                  
        
def build_file_structure(index):
    file_structure = {'type': 'tree', 'children': {}}
    for path, sha1 in sorted(index.items()):
        path_components = path.split('/')
        current_level = file_structure['children']

        for component in path_components[:-1]:
            current_level = current_level.setdefault(component, {'type': 'tree', 'children': {}})['children']

        filename = path_components[-1]
        current_level[filename] = {'type': 'blob', 'hash': sha1}

    return file_structure['children']
            

    


# --- Command Line Interface ---

def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: bit.py <command> [<args>]\n")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'init':
        success = init()
        if not success:
            sys.stderr.write("Error: A Bit repository already exists in this directory.\n")
            sys.exit(1)
    elif command == 'add':
        if not os.path.exists('.bit'):
            sys.stderr.write("Error: No Bit repository found. Please run 'bit.py init'.\n")
            sys.exit(1)
        if len(sys.argv) < 3:
            sys.stderr.write("Usage: bit.py add <file>\n")
            sys.exit(1)
        add(sys.argv[2])
    elif command == 'commit':
      if not os.path.exists('.bit'):
        sys.stderr.write("Error: No Bit repository found. Please run 'bit init'.\n")
        sys.exit(1)
      if len(sys.argv) < 4:
        sys.stderr.write("Usage: bit.py commit -m <message>\n")
        sys.exit(1)
      commit(sys.argv[3])
    else:
        sys.stderr.write(f"Error: Unknown command '{command}'\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
