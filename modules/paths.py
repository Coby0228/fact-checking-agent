from pathlib import Path
import sys

ROOT = Path.cwd()

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

