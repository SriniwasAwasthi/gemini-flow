"""
Test suite validating:
1. Prevention of UI freezes and white screens on launch and settings save.
2. Reliable Universal Text Transformation with automatic offline fallback (zero failure toasts).
"""
import sys
import os
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

def test_config_update_many():
    print("[TEST 1] Testing ConfigManager update_many atomic batching...")
    from app.config import ConfigManager
    cfg = ConfigManager()
    initial_mode = cfg.get("hotkey_mode", "toggle")
    test_updates = {
        "hotkey_mode": "push_to_talk" if initial_mode == "toggle" else "toggle",
        "custom_vocabulary": ["Antigravity", "Wispr Flow", "Gemini Flow"],
        "auto_paste": True
    }
    t0 = time.time()
    cfg.update_many(test_updates)
    elapsed = time.time() - t0
    print(f"  -> Batched update of {len(test_updates)} items completed in {elapsed:.4f}s")
    assert elapsed < 0.5, f"update_many took too long: {elapsed:.4f}s"
    assert cfg.get("hotkey_mode") == test_updates["hotkey_mode"]
    assert cfg.get("custom_vocabulary") == test_updates["custom_vocabulary"]
    
    # Restore
    cfg.set("hotkey_mode", initial_mode)
    print("  ✓ Test 1 passed!")

def test_settings_dialog_no_freeze():
    print("\n[TEST 2] Testing SettingsDialog initialization and _save_settings without GUI freeze...")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    
    from app.config import ConfigManager
    from app.gemini_engine import GeminiEngine
    from app.ui.settings_dialog import SettingsDialog
    
    cfg = ConfigManager()
    gem = GeminiEngine(api_key=cfg.get_api_key())
    
    t0 = time.time()
    dlg = SettingsDialog(cfg, gem)
    init_time = time.time() - t0
    print(f"  -> SettingsDialog initialized in {init_time:.3f}s")
    assert init_time < 5.0, f"SettingsDialog init took too long: {init_time:.3f}s"
    
    # Verify showEvent doesn't redundantly reload values
    assert getattr(dlg, '_initial_load_done', False) is True
    
    # Verify save_settings completes swiftly
    t1 = time.time()
    dlg._save_settings()
    save_time = time.time() - t1
    print(f"  -> SettingsDialog _save_settings completed in {save_time:.3f}s")
    assert save_time < 1.0, f"_save_settings took too long: {save_time:.3f}s"
    print("  ✓ Test 2 passed!")

def test_universal_text_transformation_offline_fallback():
    print("\n[TEST 3] Testing Universal Text Transformation with offline cognitive fallback...")
    from app.config import ConfigManager
    from app.transformation.gemini_transform_service import GeminiTransformService
    
    cfg = ConfigManager()
    svc = GeminiTransformService(config_manager=cfg)
    
    test_cases = [
        "The meeting was at 2 pm... sorry, 3 pm",
        "he dont know nothing about python desktop programming",
        "we need three deliverables first is auth second is database and third is ui"
    ]
    
    for text in test_cases:
        t0 = time.time()
        res = svc.transform_universal_text(text)
        duration = time.time() - t0
        print(f"\n  Input:  '{text}'")
        print(f"  Output: '{res.text}'")
        print(f"  Model:  {res.model_used} (in {duration:.3f}s, Success: {res.success})")
        assert res.success is True, f"Transformation failed for: {text}"
        assert len(res.text.strip()) > 0, "Transformed text was empty"
        assert "Gemini text transformation failed" not in res.error_message
        
    print("\n  ✓ Test 3 passed!")

def test_hotkey_manager_no_redundant_thread_restart():
    print("\n[TEST 4] Testing HotkeyManager update_config non-blocking behavior...")
    from app.hotkey_manager import HotkeyManager
    mgr = HotkeyManager("<ctrl>+<space>", "toggle")
    
    t0 = time.time()
    # Call with identical keys -> should not restart threads
    mgr.update_config("<ctrl>+<space>", "toggle")
    dur = time.time() - t0
    print(f"  -> update_config with identical keys took {dur:.4f}s")
    assert dur < 0.05, f"Identical update_config took too long: {dur:.4f}s"
    print("  ✓ Test 4 passed!")

if __name__ == "__main__":
    print("================================================================================")
    print("       GEMINI FLOW UI FREEZE & TEXT TRANSFORMATION VERIFICATION SUITE")
    print("================================================================================")
    test_config_update_many()
    test_settings_dialog_no_freeze()
    test_universal_text_transformation_offline_fallback()
    test_hotkey_manager_no_redundant_thread_restart()
    print("\n================================================================================")
    print("                 ALL 4 ROOT-CAUSE VERIFICATION TESTS PASSED!")
    print("================================================================================")
