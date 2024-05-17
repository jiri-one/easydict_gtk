import sys
from pathlib import Path

parent_dir = str(Path(__file__).parent.parent)
print(parent_dir)
sys.path.append(parent_dir)

from easydict_gtk.easydict import main

main()
