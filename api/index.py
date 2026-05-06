import sys
from pathlib import Path

# Add the project root to the sys.path so we can import from app.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app

# Vercel needs the app object to be imported here
