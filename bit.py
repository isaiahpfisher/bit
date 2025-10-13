import os
import sys

def main():
  """
  Initializes a new Bit repository.
  """
  bit_dir = os.path.join(os.getcwd(), '.bit')

  if os.path.exists(bit_dir):
      sys.stderr.write("Error: A Bit repository already exists in this directory.\n")
      sys.exit(1)

  os.makedirs(os.path.join(bit_dir, "objects"))
  with open(os.path.join(bit_dir, "HEAD"), "w") as file:
    file.write("ref: refs/heads/master\n")
  
  open(os.path.join(bit_dir, "index"), "w").close()

  print(f"Initialized empty Bit repository in {bit_dir}")


if __name__ == "__main__":
    main()