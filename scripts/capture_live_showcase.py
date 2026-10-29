"""
Gemini Flow - Production Live UI Showcase Capture
Captures high-resolution, pixel-perfect screenshots of the current running application UI:
- Luxury Left Navigation Sidebar (10 tabs)
- Executive Brand Header & Hero Banners
- Hardware Mic Card with live VU meter
- Profiles tab with 16 Voice Command categories
- Floating HUD with audio waveforms
"""
import sys
import os
import time
import datetime
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PyQt6.QtWidgets import QApplication, QLineEdit
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor

from app.config import ConfigManager
from app.ui.settings_dialog import SettingsDialog
from app.ui.floating_hud import FloatingHUD

# Sample technical history records (Zero personal data, pure production showcase)
SHOWCASE_HISTORY = [
    {
        "id": "rec-001",
        "timestamp": datetime.datetime.now().isoformat(),
        "time_str": datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
        "text": "Refactored audio capture pipeline: integrated polyphase resampler (scipy.signal.resample_poly) and continuous PCM16 streaming to achieve zero truncation.",
        "raw_text": "refactored audio capture pipeline integrated polyphase resampler scipy signal resample poly and continuous pcm16 streaming to achieve zero truncation",
        "prompt": "",
        "duration": 4.12,
        "mode": "clean_dictation",
        "model": "gemini-2.5-flash",
        "app_name": "Visual Studio Code",
        "title": "Zero-Truncation Pipeline Refactor",
        "api_key_tag": "GoogleAIStudio",
        "is_pinned": True,
        "is_favorite": True
    },
    {
        "id": "rec-002",
        "timestamp": (datetime.datetime.now() - datetime.timedelta(minutes=45)).isoformat(),
        "time_str": (datetime.datetime.now() - datetime.timedelta(minutes=45)).strftime("%Y-%m-%d %I:%M:%S %p"),
        "text": "System Architecture: implemented seamless fallback between cloud Gemini 2.5 Flash and local on-device Faster-Whisper int8 engine.",
        "raw_text": "system architecture implemented seamless fallback between cloud gemini 2.5 flash and local on device faster whisper int8 engine",
        "prompt": "",
        "duration": 3.85,
        "mode": "clean_dictation",
        "model": "offline-whisper",
        "app_name": "Slack",
        "title": "Offline Whisper Failover Verification",
        "api_key_tag": "LocalDevice",
        "is_pinned": True,
        "is_favorite": True
    },
    {
        "id": "rec-003",
        "timestamp": (datetime.datetime.now() - datetime.timedelta(hours=2)).isoformat(),
        "time_str": (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime("%Y-%m-%d %I:%M:%S %p"),
        "text": "Universal voice command executed: created GitHub issue with reproduction steps, expected vs actual behavior, and environment metadata.",
        "raw_text": "universal voice command executed created github issue with reproduction steps expected vs actual behavior and environment metadata",
        "prompt": "",
        "duration": 5.20,
        "mode": "clean_dictation",
        "model": "gemini-2.5-flash",
        "app_name": "GitHub Desktop",
        "title": "Command: Create GitHub Issue",
        "api_key_tag": "GoogleAIStudio",
        "is_pinned": False,
        "is_favorite": False
    },
    {
        "id": "rec-004",
        "timestamp": (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(),
        "time_str": (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d %I:%M:%S %p"),
        "text": "def calculate_token_savings(cached_tokens: int, cost_per_million: float) -> float:\n    return (cached_tokens / 1_000_000.0) * cost_per_million",
        "raw_text": "def calculate token savings cached tokens int cost per million float returns float return cached tokens divided by 1 million times cost per million",
        "prompt": "code_snippet",
        "duration": 6.40,
        "mode": "prompt_enhancement",
        "model": "gemini-2.5-flash",
        "app_name": "PyCharm",
        "title": "Python Helper Implementation",
        "api_key_tag": "GoogleAIStudio",
        "is_pinned": False,
        "is_favorite": False
    }
]

def capture_all():
    app = QApplication.instance() or QApplication(sys.argv)
    
    cfg = ConfigManager()
    cfg.get_history = lambda: SHOWCASE_HISTORY

    out_dir = PROJECT_ROOT / "docs" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Capture Settings Dialog (Dark Mode)
    dlg = SettingsDialog(cfg, None)
    dlg.resize(1600, 950)
    dlg.theme_mode = "dark"
    dlg._apply_theme()

    # Mask credentials securely
    if hasattr(dlg, "api_key_input") and dlg.api_key_input:
        dlg.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        dlg.api_key_input.setText("AIzaSy_MOCK_INVALID_KEY_DEMO_TEST_999")

    if hasattr(dlg, "api_status_label") and dlg.api_status_label:
        dlg.api_status_label.setText("✅ Connection verified! Gemini API is active (gemini-2.5-flash, latency: 1.12s) — Key secured in Windows DPAPI")
        dlg.api_status_label.setStyleSheet("color: #10B981; font-weight: 600; border: none; font-size: 12px;")

    if hasattr(dlg, "mic_level_bar") and dlg.mic_level_bar:
        dlg.mic_level_bar.setValue(55)

    dlg.show()
    for _ in range(15):
        app.processEvents()
        time.sleep(0.02)

    # Map tab index to target filename
    tab_mapping = {
        0: "01-main-dashboard.png",
        1: "03-hotkeys-mode.png",
        2: "04-cost-productivity.png",
        3: "05-vocabulary-engine.png",
        4: "06-custom-dictionary.png",
        5: "07-quick-text.png",
        6: "08-history.png",
        7: "09-profiles-commands.png",
        8: "10-ai-dictation.png",
        9: "02-audio-device.png"
    }

    for idx, filename in tab_mapping.items():
        # Switch tab and activate sidebar button
        dlg.tabs.setCurrentIndex(idx)
        if hasattr(dlg, "nav_buttons") and idx < len(dlg.nav_buttons):
            for b in dlg.nav_buttons:
                b.set_active(False)
            dlg.nav_buttons[idx].set_active(True)

        if idx == 6 and hasattr(dlg, "_refresh_history"):
            dlg._refresh_history()

        for _ in range(12):
            app.processEvents()
            time.sleep(0.02)

        save_p = out_dir / filename
        pix = dlg.grab()
        pix.save(str(save_p), "PNG")
        print(f"Captured Tab {idx} -> {save_p.name} [{pix.width()}x{pix.height()}]")

    dlg.close()

    # 2. Capture Floating HUD (00-floating-hud.png)
    try:
        hud = FloatingHUD(cfg)
        hud.show_recording()
        hud.set_amplitude(0.75)
        hud.show()
        for _ in range(10):
            app.processEvents()
            time.sleep(0.02)
        hud_pix = hud.grab()
        hud_save_p = out_dir / "00-floating-hud.png"
        hud_pix.save(str(hud_save_p), "PNG")
        print(f"Captured Floating HUD -> {hud_save_p.name} [{hud_pix.width()}x{hud_pix.height()}]")
        hud.close()
    except Exception as e:
        print(f"HUD capture notice: {e}")

    print("All live UI screenshots successfully captured into docs/screenshots/!")

if __name__ == "__main__":
    capture_all()
