"""
Gemini Flow Standalone Launcher
"""
import sys
import os

# Ensure package path is recognized
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Handle windowless pythonw execution (sys.stdout/stderr are None)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from app.main import start_app

if __name__ == "__main__":
    start_app()
