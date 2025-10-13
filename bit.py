import os
import sys

pathToBitDir = os.path.join(os.getcwd(), '.bit')

if (os.path.exists(pathToBitDir)):
  sys.stderr.write("Error: A bit repository already exists in this directory.\n")
  exit(1)

os.makedirs(".bit/objects")
with open(os.path.join(pathToBitDir, "HEAD"), "x") as file:
  file.write("ref: refs/heads/master")
open(os.path.join(pathToBitDir, "index"), "x")

print("Initialized empty Bit repository in " + pathToBitDir)