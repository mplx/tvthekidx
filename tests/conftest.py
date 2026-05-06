import sys
import os
from unittest.mock import MagicMock

# Put src/ first so `import tvthekidx` resolves the package, not tvthekidx.py in root.
_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _src not in sys.path:
    sys.path.insert(0, _src)

# Generate _version.py stub when hatch-vcs hasn't built it yet.
_ver = os.path.join(_src, "tvthekidx", "_version.py")
if not os.path.exists(_ver):
    with open(_ver, "w") as _f:
        _f.write('__version__ = "0.0.0.dev"\n')

# Mock heavy / optional dependencies not needed for unit tests.
for _mod in ("tmdbv3api", "ffmpeg", "moviepy", "moviepy.editor"):
    if _mod not in sys.modules:
        try:
            __import__(_mod)
        except ImportError:
            sys.modules[_mod] = MagicMock()
