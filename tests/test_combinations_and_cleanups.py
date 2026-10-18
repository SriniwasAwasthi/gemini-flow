"""
Verification test for:
1. Removal of 'Interactive Voice AI Cost & Productivity Predictor'
2. Removal of 'Google Gemini Official API Pricing Matrix'
3. Removal of 'AI Model Router' tab
4. Profile & Dictation Style Combination Showcase reactivity and persistence
5. Hotkey system prompt generation with active profile & prompt
"""
import sys
import os
from pathlib import Path

# Add project root directory to path
PROJECT_DIR = Path(__file__).parent.parent.resolve()
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from app.config import ConfigManager
from app.gemini_engine import GeminiEngine
from app.ui.settings_dialog import SettingsDialog, COMBINATION_SHOWCASE_DATA

def test_removed_features_and_combinations():
    print("=" * 70)
    print("TESTING REMOVED FEATURES & SHOWCASE COMBINATION REACTIVITY")
    print("=" * 70)
    
    cfg = ConfigManager()
    ge = GeminiEngine(cfg)
    dlg = SettingsDialog(cfg, ge)

    # 1. Verify tabs count and titles
    tab_titles = [dlg.tabs.tabText(i) for i in range(dlg.tabs.count())]
    print(f"Active Tabs ({len(tab_titles)}): {tab_titles}")
    assert "🎯 AI Model Router" not in tab_titles, "AI Model Router tab should be removed!"
    assert not any("Router" in t for t in tab_titles), "No router tab should exist!"
    print("[PASS] 1. AI Model Router tab successfully removed.")

    # 2. Verify Cost Tab does not contain predictor card or pricing matrix
    assert not hasattr(dlg, "pred_volume_combo"), "Interactive predictor should be removed!"
    assert not hasattr(dlg, "pricing_table"), "Pricing matrix table should be removed!"
    print("[PASS] 2. Interactive Cost Predictor and Pricing Matrix successfully removed.")

    # 3. Test Showcase combinations selection and reactivity for Combinations A through F
    for idx, item in enumerate(COMBINATION_SHOWCASE_DATA):
        dlg.showcase_combo.setCurrentIndex(idx)
        
        # Verify profile_combo was automatically selected
        selected_prof = dlg.profile_combo.currentData()
        assert selected_prof == item["profile_id"], (
            f"Combo {item['title']}: expected profile '{item['profile_id']}', got '{selected_prof}'"
        )
        
        # Verify saved_prompts_combo was automatically selected
        selected_prompt = dlg.saved_prompts_combo.currentData()
        assert selected_prompt == item["prompt_id"], (
            f"Combo {item['title']}: expected prompt '{item['prompt_id']}', got '{selected_prompt}'"
        )
        
        # Save & Apply and verify persistence into ConfigManager
        dlg._save_settings()
        assert cfg.get("active_profile") == item["profile_id"], "Active profile not persisted!"
        active_saved = cfg.get_active_saved_prompt()
        assert active_saved is not None and active_saved.get("id") == item["prompt_id"], (
            f"Active saved prompt mismatch! Expected {item['prompt_id']}, got {active_saved.get('id') if active_saved else None}"
        )
        
        # Verify system prompt contains profile directive
        system_prompt = cfg.get_system_prompt()
        assert len(system_prompt) > 50, "System prompt too short!"
        assert "Profile Directive" in system_prompt or item["profile_id"] in system_prompt, (
            f"Profile directive missing in system prompt for combo {item['title']}"
        )
        
        print(f"[PASS] 3.{idx+1} {item['title'][:35]}... -> Profile: {selected_prof}, Prompt: {selected_prompt} (Verified & Saved).")

    print("\n[PASS] All Showcase Combinations A-F reactive, auto-selecting, saving, and applying to hotkey dictation perfectly!")
    print("=" * 70)

if __name__ == "__main__":
    test_removed_features_and_combinations()
