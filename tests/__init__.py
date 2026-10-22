"""Run directly from a checkout without installing dependencies."""

import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
# Keep fixtures and engine scratch files inside the checkout, including in
# restricted development environments. This only affects the test process.
_TEMP = _ROOT / "is" / "test-tmp"
_TEMP.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_TEMP)
