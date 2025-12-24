import sys
from pathlib import Path

# Ensure `src` is on sys.path so tests can import the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
import sys
import os

# Ensure `src` is on sys.path so tests can import the package
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
