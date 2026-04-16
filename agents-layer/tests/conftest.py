import sys
from pathlib import Path

# Allow `from tools` / `from lerna_agent` when running pytest from repo root or agents-layer.
_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[2]
for path in (_ROOT, _REPO_ROOT):
    raw = str(path)
    if raw not in sys.path:
        sys.path.insert(0, raw)
