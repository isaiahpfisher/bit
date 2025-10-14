import os
import sys
import hashlib

def main():
  if sys.argv[1] == 'init':
      init()
  else:
    if not has_existing_bit_directory():
      sys.stderr.write("Error: No Bit repository found in this directory.\n")
      sys.exit(1)
    elif sys.argv[1] == 'add':
      add(sys.argv[2])
   


def init():
  """
  Initializes a new Bit repository.
  """
  if has_existing_bit_directory():
    sys.stderr.write("Error: A Bit repository already exists in this directory.\n")
    sys.exit(1)

  repo_root = os.getcwd()
  bit_dir = os.path.join(repo_root, ".bit")
  os.makedirs(os.path.join(bit_dir, "objects"))
  with open(os.path.join(bit_dir, "HEAD"), "w") as file:
    file.write("ref: refs/heads/master\n")
  
  open(os.path.join(bit_dir, "index"), "w").close()

  print(f"Initialized empty Bit repository in {bit_dir}")
   

def add(file_path):
  """
  Stages a file by creating a blob and updating the index.
  """
  repo_root = os.getcwd()
  bit_dir = os.path.join(repo_root, ".bit")

  #  read the file
  try:
    with open(file_path, 'rb') as file:
      file_content = file.read()
  except FileNotFoundError:
    sys.stderr.write(f"Error: file not found: {file_path}\n")
    sys.exit(1)

  # create the blob
  hash = hashlib.sha1(file_content).hexdigest()
  with open(os.path.join(bit_dir, "objects", hash), "wb") as file:
    file.write(file_content)

  # read existing index into dictionary
  index_path = os.path.join(bit_dir, "index")
  index = {}

  if os.path.exists(index_path):
    with open(index_path, 'r') as file:
      for line in file:
        if line.strip(): # Avoid empty lines
          sha1, path = line.strip().split(' ', 1)
          index[path] = sha1
  
  # update/add new hash
  path_from_root = os.path.relpath(os.path.abspath(file_path), repo_root)
  index[path_from_root] = hash

  # write updated index back to file
  with open(index_path, "w") as file:
    for path, sha1 in index.items():
      file.write(f"{sha1} {path}\n")
  
  print(f"Staged {file_path}")

def has_existing_bit_directory():
  repo_root = os.getcwd()
  bit_dir = os.path.join(repo_root, '.bit')
  return os.path.exists(bit_dir)

if __name__ == "__main__":
    main()