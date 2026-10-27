import sys
import time
import subprocess
from pathlib import Path

# Add project root directory to path
PROJECT_DIR = Path(__file__).parent.parent.resolve()
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from app.main import notify_running_instance
from app.config import ConfigManager
from app.gemini_engine import GeminiEngine
from app.ui.settings_dialog import SettingsDialog

def test_agent_c_verification():
    print("=" * 80)
    print("  AGENT C: BUILD, INTEGRATION & IPC VERIFICATION (20 ITERATIONS)")
    print("=" * 80)

    # 1. Verify C# Launcher compilation
    csc_path = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    launcher_cs = PROJECT_DIR / "Launcher.cs"
    launcher_exe = PROJECT_DIR / "Gemini Flow.exe"
    icon_path = PROJECT_DIR / "app_icon.ico"

    print("  [1] Compiling Launcher.cs with csc.exe...")
    cmd = [
        csc_path,
        "/target:winexe",
        f"/win32icon:{icon_path}",
        f"/out:{launcher_exe}",
        str(launcher_cs)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Compilation failed: {res.stderr}\n{res.stdout}"
    assert launcher_exe.exists(), "Gemini Flow.exe does not exist"
    print(f"  >> [PASS] Gemini Flow.exe compiled successfully! Size: {launcher_exe.stat().st_size:,} bytes")

    # 2. Verify Single Instance IPC
    print("\n  [2] Auditing Single Instance IPC (20 Consecutive Pings)...")
    success_count = 0
    for i in range(1, 21):
        success = notify_running_instance("PING")
        if success:
            success_count += 1
        time.sleep(0.02)
    print(f"  IPC PING Results: {success_count}/20 successful responses.")
    assert success_count == 20, f"Expected 20/20 successful pings, got {success_count}"
    print(f"  >> [PASS] Live background instance running and responding to 20/20 IPC messages!")

    # 3. Verify All 10 Settings Tabs
    print("\n  [3] Auditing All 10 Settings Tabs in SettingsDialog...")
    cfg = ConfigManager()
    engine = GeminiEngine(api_key=cfg.get("gemini_api_key", ""))
    dlg = SettingsDialog(cfg, engine)
    tab_count = dlg.tabs.count()
    tab_names = [dlg.tabs.tabText(i).encode('ascii', 'replace').decode() for i in range(tab_count)]
    print(f"  Found {tab_count} tabs: {tab_names}")
    assert tab_count == 10, f"Expected 10 tabs, found {tab_count}"
    
    expected_keywords = [
        "API_General", "Hotkeys_Mode", "Cost_Productivity", "Vocabulary Engine",
        "Custom Dictionary", "Quick Text", "History", "Profiles", "AI Dictation", "Audio Device"
    ]
    for kw in expected_keywords:
        assert any(kw in name for name in tab_names), f"Missing tab: {kw}"
    print("  >> [PASS] All 10 Settings Tabs instantiated and verified successfully!")

    print("\n" + "=" * 80)
    print("  AGENT C AUDIT PASSED 100% ACROSS ALL VERIFICATIONS!")
    print("=" * 80)

if __name__ == "__main__":
    test_agent_c_verification()
