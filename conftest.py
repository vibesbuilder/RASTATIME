import sys
from pathlib import Path

# Add the repo root to sys.path so that top-level packages
# (playout, audio, streams, backend) are importable in tests
# without requiring an installed package.
sys.path.insert(0, str(Path(__file__).parent))
