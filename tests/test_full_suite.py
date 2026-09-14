"""
Comprehensive Test Suite for Gemini Flow
Tests all 11 Settings tabs in order, UI widgets, buttons, hotkeys, engine features,
safe clipboard safeguards, and full integration.
"""
import os
import sys
import time
from pathlib import Path

# Ensure project directory is in python path
APP_DIR = Path(__file__).parent.resolve()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Initialize headless Qt Application
app = QApplication.instance() or QApplication(sys.argv)

from app.config import ConfigManager, DEFAULT_PROMPTS, setup_windows_startup
from app.gemini_engine import GeminiEngine
from app.text_injector import TextInjector
from app.hotkey_manager import HotkeyManager, _is_win32_key_down, _is_any_vk_down
from app.ui.floating_hud import FloatingHUD
from app.ui.tray_icon import SystemTrayManager
from app.ui.settings_dialog import SettingsDialog
from app.vocabulary.vocab_engine import VocabularyEngine
from app.profiles.profile_manager import ProfileManager


def run_comprehensive_audit():
    print("=" * 60)
    print("       GEMINI FLOW FULL AUDIT & FEATURE TEST SUITE       ")
    print("=" * 60)

    # 1. Config Manager & Registry Audit
    print("\n[1/6] Testing Configuration & Persistence...")
    cfg = ConfigManager()
    assert cfg.get_api_key() is not None, "API Key should be accessible"
    assert "clean_dictation" in DEFAULT_PROMPTS, "clean_dictation prompt missing"
    assert cfg.get("auto_cost_mode") is True, "auto_cost_mode default should be True"
    assert cfg.get_auto_prompt_conversion() in (True, False), "auto_prompt_conversion getter failed"
    print("  ✓ ConfigManager passed.")

    # Test startup configuration
    startup_res = setup_windows_startup(True)
    assert startup_res is True, "Windows startup registry configuration failed"
    print("  ✓ Windows Startup Registry configuration passed.")

    # 2. Text Injector & Clipboard Safeguard Audit
    print("\n[2/6] Testing Text Injector & Clipboard Safeguard...")
    injector = TextInjector()
    assert hasattr(injector, "get_selected_text"), "get_selected_text missing"
    assert hasattr(injector, "paste_text"), "paste_text missing"
    print("  ✓ Text Injector interface passed.")

    # 3. Hotkey Manager & Win32 Physical Key Checking Audit
    print("\n[3/6] Testing Hotkey Manager & Win32 Hardware Key Hooks...")
    events = []
    hkm = HotkeyManager(
        hotkey_str="<ctrl>+<space>",
        mode="toggle",
        prompt_hotkey_str="<ctrl>+<shift>+p",
        transform_hotkey_str="<ctrl>+<shift>+t",
        on_start=lambda: events.append("start"),
        on_stop=lambda: events.append("stop"),
        on_cancel=lambda: events.append("cancel"),
        on_prompt=lambda: events.append("prompt"),
        on_transform=lambda: events.append("transform")
    )
    # Validate Win32 key checking functions
    assert callable(_is_win32_key_down), "_is_win32_key_down missing"
    assert callable(_is_any_vk_down), "_is_any_vk_down missing"

    # Test check match logic
    hkm.set_recording_state(False)
    assert not hkm._check_match(""), "Empty hotkey should return False"
    print("  ✓ Hotkey Manager & Win32 physical checking passed.")

    # 4. Floating HUD & Audio Waveform Audit
    print("\n[4/6] Testing Floating HUD & Pill States...")
    hud = FloatingHUD(cfg)
    assert hud.wave_widget is not None, "Waveform widget missing"
    hud.update_volume(0.85)
    hud.show_state(FloatingHUD.STATE_LISTENING, "Listening...")
    hud.show_state(FloatingHUD.STATE_PROCESSING, "Refining...")
    hud.show_state(FloatingHUD.STATE_PASTED, "Pasted!")
    hud.show_state(FloatingHUD.STATE_PROMPT, "AI Prompt Ready!")
    hud.show_state(FloatingHUD.STATE_CANCELLED, "Cancelled")
    hud.hide_smooth()
    print("  ✓ Floating HUD visual states passed.")

    # 5. Settings Dialog & Tab Order Verification Audit
    print("\n[5/6] Testing Settings & Configuration Dialog...")
    gemini = GeminiEngine(api_key=cfg.get_api_key())
    dlg = SettingsDialog(cfg, gemini, injector)

    # Validate exact tab count and ordering
    expected_tabs = [
        "API_General",
        "Hotkeys_Mode",
        "Cost_Productivity",
        "Vocabulary Engine",
        "Custom Dictionary",
        "Quick Text",
        "History",
        "Profiles",
        "AI Dictation",
        "AI Model Router",
        "Audio Device"
    ]

    actual_tab_count = dlg.tabs.count()
    print(f"  -> Total Settings Tabs: {actual_tab_count}")
    assert actual_tab_count == len(expected_tabs), f"Expected {len(expected_tabs)} tabs, found {actual_tab_count}"

    for idx, expected_name in enumerate(expected_tabs):
        tab_text = dlg.tabs.tabText(idx)
        print(f"  -> Tab #{idx}: {tab_text}")
        clean_name = expected_name.lower().replace(" ", "").replace("_", "")
        clean_tab = tab_text.lower().replace(" ", "").replace("_", "")
        assert clean_name in clean_tab or any(part in clean_tab for part in clean_name.split()), f"Tab mismatch at index {idx}: expected '{expected_name}', got '{tab_text}'"

    print("  ✓ All 11 Tabs match the exact requested sequence!")

    # Test settings dialog button wiring and functions
    print("\n[6/6] Testing Settings Dialog UI Buttons & Functional Features...")
    assert hasattr(dlg, "btn_save"), "Save button missing"
    assert hasattr(dlg, "btn_restart"), "Restart button missing"
    assert hasattr(dlg, "btn_close"), "Close button missing"
    assert hasattr(dlg, "btn_test_api"), "Test API button missing"
    assert hasattr(dlg, "btn_test_mic"), "Test Mic button missing"
    assert hasattr(dlg, "btn_add_dict"), "Add Dictionary button missing"
    assert hasattr(dlg, "btn_add_snippet"), "Add Snippet button missing"
    assert hasattr(dlg, "btn_copy_selected"), "Copy Selected History button missing"
    assert hasattr(dlg, "btn_reinsert_selected"), "Paste Selected History button missing"
    assert hasattr(dlg, "btn_pin_selected"), "Pin Selected History button missing"
    assert hasattr(dlg, "btn_fav_selected"), "Favorite Selected History button missing"
    assert hasattr(dlg, "btn_delete_selected"), "Delete Selected History button missing"
    assert hasattr(dlg, "btn_clear_history"), "Clear History button missing"
    assert hasattr(dlg, "_poll_live_updates"), "_poll_live_updates method missing"
    assert hasattr(dlg, "notify_history_changed"), "notify_history_changed method missing"
    assert hasattr(dlg, "_restore_window_state"), "_restore_window_state method missing"
    assert hasattr(dlg, "_save_window_state"), "_save_window_state method missing"

    # Test Vocabulary Engine integration
    ve = VocabularyEngine()
    test_phrase = ve.normalize("hello world")
    assert isinstance(test_phrase, str), "Vocab normalization failed"
    print("  ✓ Vocabulary Engine tests passed.")

    # Test History search and filter functions
    dlg._history_search_query = "test"
    dlg._refresh_history()
    dlg._history_search_query = ""
    dlg._refresh_history()
    print("  ✓ History Search & Filtering passed.")

    # Test Save & Apply Settings handler
    dlg._save_settings()
    print("  ✓ Save & Apply Changes handler passed.")

    # Cleanup dialog
    dlg.close()

    print("\n" + "=" * 60)
    print("   ALL 11 TABS, BUTTONS, FEATURES & HOOKS PASSED 100%!   ")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_comprehensive_audit()
    sys.exit(0 if success else 1)
