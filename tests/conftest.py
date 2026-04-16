from pathlib import Path
import sys

# Ensure src/python is on the path so the mvp package is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "python"))
