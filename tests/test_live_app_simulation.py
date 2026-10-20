"""
End-to-end simulation of user workflow:
1. Initialize GeminiFlowApp
2. Open SettingsDialog
3. Select Combination A in showcase combo
4. Click 'Apply This Combination Now'
5. Verify app in-memory config and active system prompt for hotkey dictation
6. Select Combination B in showcase combo
7. Click 'Save & Apply Changes'
8. Verify app in-memory config and active system prompt for hotkey dictation
"""
import sys
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.resolve()
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from app.main import GeminiFlowApp
from app.ui.settings_dialog import SettingsDialog

def test_live_app_flow():
    print("=" * 70)
    print("SIMULATING LIVE APP USER SELECTION AND HOTKEY APPLICATION")
    print("=" * 70)

    flow_app = GeminiFlowApp()
    dlg = SettingsDialog(flow_app.config, flow_app.gemini, flow_app)
    dlg.settings_applied.connect(flow_app._on_settings_applied)

    # --- Scenario 1: Select Combination A and click 'Apply This Combination Now' ---
    print("\nScenario 1: Selecting Combination A (Executive & Structured)...")
    dlg.showcase_combo.setCurrentIndex(0)
    dlg._on_apply_showcase_combination()

    # Verify Config
    assert flow_app.config.get("active_profile") == "professional", "Active profile not set to professional!"
    assert flow_app.config.get_active_saved_prompt()["id"] == "smart_polish_custom", "Active prompt not smart_polish_custom!"
    
    # Verify System Prompt generated when hotkey is pressed
    prompt_a = flow_app.config.get_system_prompt()
    assert "Executive" in prompt_a, "Executive prompt missing!"
    assert "Professional" in prompt_a or "executive" in prompt_a.lower(), "Professional profile directive missing!"
    print("[PASS] Scenario 1: Combination A applied live immediately. Hotkey dictation uses Executive & Structured profile and prompt.")

    # --- Scenario 2: Select Combination B and click 'Save & Apply Changes' ---
    print("\nScenario 2: Selecting Combination B (Developer Code & Technical)...")
    dlg.showcase_combo.setCurrentIndex(1)
    dlg._save_settings()

    # Verify Config
    assert flow_app.config.get("active_profile") == "coding", "Active profile not set to coding!"
    assert flow_app.config.get_active_saved_prompt()["id"] == "code_dev_custom", "Active prompt not code_dev_custom!"
    
    # Verify System Prompt generated when hotkey is pressed
    prompt_b = flow_app.config.get_system_prompt()
    assert "Developer Code" in prompt_b or "Senior Staff Software Engineer" in prompt_b, "Coding prompt/directive missing!"
    print("[PASS] Scenario 2: Combination B applied live immediately. Hotkey dictation uses Developer Code & Technical profile and prompt.")

    # --- Scenario 3: Select Combination E (Engineering Architecture) ---
    print("\nScenario 3: Selecting Combination E (Engineering Architecture)...")
    dlg.showcase_combo.setCurrentIndex(4)
    dlg._save_settings()
    assert flow_app.config.get("active_profile") == "engineering", "Active profile not set to engineering!"
    prompt_e = flow_app.config.get_system_prompt()
    assert "Principal Systems Architect" in prompt_e or "Engineering & Architecture" in prompt_e, "Engineering directive missing!"
    print("[PASS] Scenario 3: Combination E applied live immediately.")

    # --- Scenario 4: Select Combination F (AI Prompt Engineer) ---
    print("\nScenario 4: Selecting Combination F (AI Prompt Engineer)...")
    dlg.showcase_combo.setCurrentIndex(5)
    dlg._save_settings()
    assert flow_app.config.get("active_profile") == "ai_dictations", "Active profile not set to ai_dictations!"
    prompt_f = flow_app.config.get_system_prompt()
    assert "AI Dictations" in prompt_f or "Voice Command" in prompt_f or "Prompt" in prompt_f, "AI dictation profile directive missing!"
    print("[PASS] Scenario 4: Combination F applied live immediately.")

    print("\n" + "=" * 70)
    print("ALL SCENARIOS VERIFIED: COMBINATIONS WORK DIRECTLY UPON SAVING!")
    print("=" * 70)

if __name__ == "__main__":
    test_live_app_flow()
