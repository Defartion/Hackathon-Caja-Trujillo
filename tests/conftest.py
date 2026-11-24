import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import os
os.environ.setdefault("CUOTAFLEX_PERSISTENCIA", "0")  # las pruebas no escriben data/cuotaflex.db
