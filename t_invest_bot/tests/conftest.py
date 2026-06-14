from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"

sys.path.insert(0, str(APP_DIR))
