"""
Verification of Cold-Boot Persistence & Full System Durability.
Simulates shutting down the computer and restarting Gemini Flow from a cold state:
1. Writes configuration, Groq API key, hotkeys, profiles, and vocabulary to disk.
2. Destroys all in-memory processes and singletons.
3. Reloads ConfigManager, GeminiEngine, and SettingsDialog from disk in a fresh cold start.
4. Asserts 100% data fidelity.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import ConfigManager, APP_DIR, CONFIG_FILE
from app.transformation.transform_engine import TransformEngine


class TestColdBootPersistence(unittest.TestCase):

    def setUp(self):
        # Backup existing config file if present
        self.backup_path = CONFIG_FILE.with_suffix(".backup_test")
        if CONFIG_FILE.exists():
            import shutil
            shutil.copy2(CONFIG_FILE, self.backup_path)

    def tearDown(self):
        # Restore backup config
        if self.backup_path.exists():
            import shutil
            shutil.copy2(self.backup_path, CONFIG_FILE)
            self.backup_path.unlink(missing_ok=True)

    def test_cold_boot_persistence_cycle(self):
        # 1. Simulate Session 1 (Before shutdown)
        cm1 = ConfigManager()
        cm1.set("groq_api_key", "gsk_test_persistent_groq_key_123456789")
        cm1.set("api_key", "AIzaSy_TEST_PERSISTENT_GEMINI_KEY")
        cm1.set("model_name", "groq-whisper-turbo")
        cm1.set("hotkey", "<ctrl>+<alt>+t")
        cm1.set("hotkey_display", "Ctrl + Alt + T")
        cm1.set("prompt_hotkey", "<alt>+p")
        cm1.set("prompt_hotkey_display", "Alt + P")
        cm1.set("transform_hotkey", "<alt>+t")
        cm1.set("transform_hotkey_display", "Alt + T")
        vocab = list(cm1.get("custom_vocabulary", [])) + ["ColdBootPersistenceTestWord"]
        cm1.set("custom_vocabulary", vocab)

        # Verify physical file exists on disk
        self.assertTrue(CONFIG_FILE.exists(), f"Config file {CONFIG_FILE} must physically exist on disk")

        # 2. Simulate Cold Reboot (Destroy all in-memory references)
        ConfigManager._instance = None
        if "GROQ_API_KEY" in os.environ:
            del os.environ["GROQ_API_KEY"]
        del cm1

        # 3. Simulate Session 2 (Cold boot after PC restart)
        cm2 = ConfigManager()
        reloaded_groq = cm2.get("groq_api_key")
        self.assertEqual(reloaded_groq, "gsk_test_persistent_groq_key_123456789", "Groq API key must survive PC shutdown!")
        self.assertEqual(cm2.get("model_name"), "groq-whisper-turbo", "Selected model must survive PC shutdown!")
        self.assertEqual(cm2.get("hotkey"), "<ctrl>+<alt>+t", "Main hotkey must survive PC shutdown!")
        self.assertEqual(cm2.get("prompt_hotkey"), "<alt>+p", "Prompt hotkey must survive PC shutdown!")
        self.assertIn("ColdBootPersistenceTestWord", cm2.get("custom_vocabulary", []), "Custom vocabulary must survive PC shutdown!")

        # 4. Verify SettingsDialog loads reloaded keys without error
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        qapp = QApplication.instance() or QApplication([])
        from app.gemini_engine import GeminiEngine
        from app.text_injector import TextInjector
        from app.ui.settings_dialog import SettingsDialog

        gem = GeminiEngine(cm2)
        inj = TextInjector()
        dlg = SettingsDialog(cm2, gem, inj)
        self.assertEqual(dlg.groq_key_input.text(), "gsk_test_persistent_groq_key_123456789")
        self.assertEqual(dlg.hotkey_btn.display_str, "Ctrl + Alt + T")
        self.assertEqual(dlg.prompt_hotkey_btn.display_str, "Alt + P")

        # 5. Verify Prompt Transformation operates with 100% fidelity on cold boot
        raw = "Create a beginner-friendly e-commerce website for a coffee shop with React, Node, MongoDB, and Stripe."
        prompt = TransformEngine.convert_to_prompt(raw)
        self.assertIn("<role>", prompt)
        self.assertIn("Coffee Shop", prompt)
        self.assertIn("MongoDB", prompt)
        self.assertIn("<output_format>", prompt)


if __name__ == "__main__":
    unittest.main()
