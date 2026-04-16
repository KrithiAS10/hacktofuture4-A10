import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "agents-layer"):
    raw = str(path)
    if raw not in sys.path:
        sys.path.insert(0, raw)
