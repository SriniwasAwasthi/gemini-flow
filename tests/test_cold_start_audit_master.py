"""
Comprehensive Master Audit for Gemini Flow:
1. Cold-start persistence and full disk fidelity in config.json and profiles.json.
2. Clean startup via main_standalone.py and app.main without NameError/AttributeError/SyntaxError.
3. Groq API Key field and helper methods in SettingsDialog load and persist correctly.
4. Prompt transformations adhering to prompt_transformation_showcase.md output all 5 XML tags with zero truncation.
"""
import os
import sys
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import ConfigManager, APP_DIR, CONFIG_FILE
from app.profiles.profile_manager import ProfileManager, Profile, PROFILES_FILE
from app.transformation.transform_engine import TransformEngine


class TestMasterColdStartAudit(unittest.TestCase):

    def setUp(self):
        # Backup config and profiles
        self.config_backup = None
        if CONFIG_FILE.exists():
            self.config_backup = CONFIG_FILE.read_bytes()
        
        self.profiles_path = Path(PROFILES_FILE)
        self.profiles_backup = None
        if self.profiles_path.exists():
            self.profiles_backup = self.profiles_path.read_bytes()

    def tearDown(self):
        # Restore backups
        if self.config_backup is not None:
            CONFIG_FILE.write_bytes(self.config_backup)
        elif CONFIG_FILE.exists():
            pass
        
        if self.profiles_backup is not None:
            self.profiles_path.write_bytes(self.profiles_backup)

    def test_01_cold_process_persistence(self):
        """Test persistence across a brand-new, completely separate Python OS process."""
        # Session 1: Setup test state
        cm = ConfigManager()
        test_groq = "gsk_cold_start_verification_key_99999"
        test_api_key = "AIzaSy_COLD_BOOT_VERIFICATION_KEY_123"
        test_model = "groq-whisper-turbo"
        test_hotkey = "<ctrl>+<alt>+k"
        test_hotkey_disp = "Ctrl + Alt + K"
        test_prompt_hotkey = "<alt>+p"
        test_prompt_disp = "Alt + P"
        test_transform_hotkey = "<alt>+t"
        test_transform_disp = "Alt + T"
        test_vocab = ["Supercalifragilistic", "WhisperTurboAudit", "ColdBootVerified"]
        test_active_profile = "engineering"

        cm.set("groq_api_key", test_groq)
        cm.set("api_key", test_api_key)
        cm.set("model_name", test_model)
        cm.set("hotkey", test_hotkey)
        cm.set("hotkey_display", test_hotkey_disp)
        cm.set("prompt_hotkey", test_prompt_hotkey)
        cm.set("prompt_hotkey_display", test_prompt_disp)
        cm.set("transform_hotkey", test_transform_hotkey)
        cm.set("transform_hotkey_display", test_transform_disp)
        cm.set("custom_vocabulary", test_vocab)
        cm.set("active_profile", test_active_profile)

        # Profile manager: add custom profile
        pm = ProfileManager(str(self.profiles_path))
        custom_prof = Profile(
            id="audit_profile_custom",
            name="Audit Custom Profile",
            description="Custom profile for cold-start persistence testing.",
            preferred_model="groq-whisper-turbo",
            system_prompt_addition="[Audit Directive]: Enforce absolute precision.",
            vocabulary_categories=["Testing", "Audit"],
            temperature=0.15
        )
        pm.create_custom_profile(custom_prof)

        # Verify physical files exist on disk
        self.assertTrue(CONFIG_FILE.exists(), f"config.json must exist at {CONFIG_FILE}")
        self.assertTrue(self.profiles_path.exists(), f"profiles.json must exist at {self.profiles_path}")

        # Raw JSON read from disk before spawning new process
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            disk_config = json.load(f)
        self.assertEqual(disk_config.get("groq_api_key"), test_groq)
        self.assertEqual(disk_config.get("api_key"), test_api_key)
        self.assertEqual(disk_config.get("model_name"), test_model)
        self.assertEqual(disk_config.get("hotkey"), test_hotkey)
        self.assertEqual(disk_config.get("prompt_hotkey"), test_prompt_hotkey)
        self.assertEqual(disk_config.get("transform_hotkey"), test_transform_hotkey)
        self.assertEqual(disk_config.get("custom_vocabulary"), test_vocab)
        self.assertEqual(disk_config.get("active_profile"), test_active_profile)

        # Session 2: Fresh OS subprocess
        check_script = f"""
import sys, os
from pathlib import Path

ROOT = r"{ROOT}"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.config import ConfigManager, CONFIG_FILE
from app.profiles.profile_manager import ProfileManager

cm = ConfigManager()
assert cm.get("groq_api_key") == "{test_groq}", f"Groq key mismatch: {{cm.get('groq_api_key')}}"
assert cm.get("api_key") == "{test_api_key}", f"API key mismatch: {{cm.get('api_key')}}"
assert cm.get("model_name") == "{test_model}", f"Model mismatch: {{cm.get('model_name')}}"
assert cm.get("hotkey") == "{test_hotkey}", f"Hotkey mismatch: {{cm.get('hotkey')}}"
assert cm.get("prompt_hotkey") == "{test_prompt_hotkey}", f"Prompt hotkey mismatch: {{cm.get('prompt_hotkey')}}"
assert cm.get("transform_hotkey") == "{test_transform_hotkey}", f"Transform hotkey mismatch: {{cm.get('transform_hotkey')}}"
assert "ColdBootVerified" in cm.get("custom_vocabulary", []), "Custom vocabulary item missing"
assert cm.get("active_profile") == "{test_active_profile}", "Active profile mismatch"

pm = ProfileManager(r"{self.profiles_path}")
prof = pm.get_profile("audit_profile_custom")
assert prof is not None, "Custom profile was not reloaded from profiles.json"
assert prof.name == "Audit Custom Profile", f"Profile name mismatch: {{prof.name}}"
assert prof.preferred_model == "groq-whisper-turbo", "Profile preferred model mismatch"

print("COLD_START_SUBPROCESS_SUCCESS")
"""
        proc = subprocess.run(
            [sys.executable, "-c", check_script],
            capture_output=True,
            text=True,
            cwd=str(ROOT)
        )
        self.assertEqual(proc.returncode, 0, f"Subprocess failed with error:\n{proc.stderr}\nOutput: {proc.stdout}")
        self.assertIn("COLD_START_SUBPROCESS_SUCCESS", proc.stdout)

    def test_02_clean_app_start_and_imports(self):
        """Test that main_standalone and app.main load and initialize cleanly without NameError or AttributeError."""
        check_script = f"""
import sys, os
from pathlib import Path
ROOT = r"{ROOT}"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# 1. Verify main_standalone import
import main_standalone
assert hasattr(main_standalone, "CURRENT_DIR")
assert hasattr(main_standalone, "startup_log")

# 2. Verify app.main import and GeminiFlowApp instantiation
from app.main import GeminiFlowApp
app = GeminiFlowApp()
assert app.config is not None
assert app.gemini is not None
assert app.transcription_engine is not None
assert app.hud is not None
assert app.tray is not None
assert app.hotkey_mgr is not None

# Clean teardown
app.server.close()
app.hotkey_mgr.stop()
print("APP_START_VERIFIED_CLEAN")
"""
        proc = subprocess.run(
            [sys.executable, "-c", check_script],
            capture_output=True,
            text=True,
            cwd=str(ROOT)
        )
        self.assertEqual(proc.returncode, 0, f"Subprocess failed with error:\n{proc.stderr}\nOutput: {proc.stdout}")
        self.assertIn("APP_START_VERIFIED_CLEAN", proc.stdout)

    def test_03_settings_dialog_groq_key_and_helpers(self):
        """Test SettingsDialog Groq API key field, helper methods, echo toggling, paste, clear, and save."""
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication, QLineEdit
        qapp = QApplication.instance() or QApplication([])

        from app.gemini_engine import GeminiEngine
        from app.text_injector import TextInjector
        from app.ui.settings_dialog import SettingsDialog

        cm = ConfigManager()
        test_groq = "gsk_initial_groq_test_key_4444"
        cm.set("groq_api_key", test_groq)

        gem = GeminiEngine(cm)
        inj = TextInjector()
        dlg = SettingsDialog(cm, gem, inj)

        # 1. Check UI element existence
        self.assertTrue(hasattr(dlg, "groq_key_input"), "SettingsDialog missing groq_key_input")
        self.assertTrue(hasattr(dlg, "btn_toggle_groq_key"), "SettingsDialog missing btn_toggle_groq_key")
        self.assertTrue(hasattr(dlg, "btn_paste_groq_key"), "SettingsDialog missing btn_paste_groq_key")
        self.assertTrue(hasattr(dlg, "btn_clear_groq_key"), "SettingsDialog missing btn_clear_groq_key")
        self.assertTrue(hasattr(dlg, "groq_status_label"), "SettingsDialog missing groq_status_label")

        # 2. Initial loaded value
        self.assertEqual(dlg.groq_key_input.text(), test_groq)
        self.assertEqual(dlg.groq_key_input.echoMode(), QLineEdit.EchoMode.Password)

        # 3. Test _toggle_groq_key_echo
        dlg._toggle_groq_key_echo()
        self.assertEqual(dlg.groq_key_input.echoMode(), QLineEdit.EchoMode.Normal)
        self.assertEqual(dlg.btn_toggle_groq_key.text(), "🔒 Hide")
        dlg._toggle_groq_key_echo()
        self.assertEqual(dlg.groq_key_input.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(dlg.btn_toggle_groq_key.text(), "👁️ Show")

        # 4. Test _clear_groq_key
        dlg._clear_groq_key()
        self.assertEqual(dlg.groq_key_input.text(), "")
        self.assertEqual(cm.get("groq_api_key"), "")
        self.assertNotIn("GROQ_API_KEY", os.environ)
        self.assertIn("cleared", dlg.groq_status_label.text().lower())

        # 5. Test typing new key and saving
        new_key = "gsk_newly_typed_groq_key_5555"
        dlg.groq_key_input.setText(new_key)
        dlg.save_settings()
        self.assertEqual(cm.get("groq_api_key"), new_key)
        self.assertEqual(os.environ.get("GROQ_API_KEY"), new_key)

    def test_04_prompt_transformations_5_tags_and_zero_truncation(self):
        """Test prompt transformations adhering to prompt_transformation_showcase.md output all 5 XML tags with zero truncation."""
        test_cases = [
            (
                "Coffee Shop E-Commerce",
                (
                    "Create a beginner-friendly e-commerce website for a coffee shop. "
                    "The website should have a Home page, Product Listing page, Product Details page, "
                    "Shopping Cart, Login/Register, and Checkout page. Users can browse coffee products, "
                    "add items to the cart, and place orders. Use a clean coffee-themed design with "
                    "responsive layouts for mobile and desktop.\n\n"
                    "Tech Stack:\n"
                    "• Frontend: React.js, Tailwind CSS\n"
                    "• Backend: Node.js, Express.js\n"
                    "• Database: MongoDB\n"
                    "• Authentication: JWT\n"
                    "• Payments: Stripe"
                ),
                ["Senior Full-Stack Architect", "Coffee Shop", "MongoDB", "Stripe"]
            ),
            (
                "CodePulse SaaS Landing Page",
                (
                    'Make a high converting modern landing page for an AI code review tool named "CodePulse". '
                    'I want a dark mode hero section, feature grid, social proof ticker, pricing table with '
                    'monthly/annual toggle, and FAQ accordion.'
                ),
                ["Product Designer", "CodePulse", "Landing Page"]
            ),
            (
                "Windows 11 Fluent Desktop",
                (
                    "Build a desktop system monitor app in Python that looks like Windows 11 Settings. "
                    "It should show CPU usage, RAM, disk space, and running processes with kill buttons."
                ),
                ["Windows Desktop Software Engineer", "PyQt", "psutil"]
            ),
            (
                "RESTful API Contract",
                (
                    "I need an API spec and mock server for a patient appointment scheduling system "
                    "for a dental clinic. Doctors, Patients, Appointments, and Services."
                ),
                ["API Architect", "OpenAPI"]
            )
        ]

        REQUIRED_TAGS = [
            "<role>", "</role>",
            "<context>", "</context>",
            "<task>", "</task>",
            "<constraints>", "</constraints>",
            "<output_format>", "</output_format>"
        ]

        for name, raw_text, expected_keywords in test_cases:
            transformed = TransformEngine.convert_to_prompt(raw_text)
            
            # Check length to guarantee zero truncation
            self.assertGreater(len(transformed), 300, f"{name}: Output was truncated or too short")

            # Check 5 required XML tags
            for tag in REQUIRED_TAGS:
                self.assertIn(tag, transformed, f"{name}: Missing required XML tag {tag}")

            # Verify no canned persona
            if "Coffee" in name:
                self.assertNotIn("Security Engineer", transformed, "Canned persona detected in Coffee Shop prompt")
                self.assertNotIn("FastAPI", transformed, "Hallucinated FastAPI in Coffee Shop prompt")

            # Check keyword fidelity
            for kw in expected_keywords:
                self.assertIn(kw.lower(), transformed.lower(), f"{name}: Missing essential keyword '{kw}'")

            # Verify no ellipses truncating requirements
            self.assertNotIn("...", transformed, f"{name}: Contains ellipsis truncation ('...')")


if __name__ == "__main__":
    unittest.main()
