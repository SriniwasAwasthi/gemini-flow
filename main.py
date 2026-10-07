"""
Gemini Flow - AI Voice Dictation & Real-Time Polish Assistant
Root Application Entrypoint
"""
import os
import sys
import traceback
from pathlib import Path

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Configure crash-safe log capture for pythonw
log_dir = Path(os.environ.get("APPDATA", Path.home())) / "GeminiFlow"
log_dir.mkdir(parents=True, exist_ok=True)
startup_log = log_dir / "gemini_flow_startup.log"

if sys.stdout is None or sys.stderr is None:
    try:
        f = open(startup_log, "a", encoding="utf-8")
        if sys.stdout is None:
            sys.stdout = f
        if sys.stderr is None:
            sys.stderr = f
    except Exception:
        pass

def _show_fatal_error(title: str, message: str):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10 | 0x10000)
    except Exception:
        pass

if __name__ == "__main__":
    try:
        from app.main import start_app
        start_app()
    except Exception as e:
        err_msg = traceback.format_exc()
        try:
            with open(startup_log, "a", encoding="utf-8") as f:
                f.write(f"\n[FATAL ERROR on launch]:\n{err_msg}\n")
        except Exception:
            pass
        _show_fatal_error("Gemini Flow — Startup Error", f"Gemini Flow encountered an error while starting:\n\n{e}\n\nSee log: {startup_log}")
        sys.exit(1)

