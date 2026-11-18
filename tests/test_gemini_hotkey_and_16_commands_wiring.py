"""
Comprehensive Verification Suite for:
1. Persistent ConfigStore & Gemini API Key precedence (DPAPI + config.json + backup recovery)
2. Dedicated GeminiTransformService (fast-fail 400/401/403, 404/429 failover, timeouts, empty key)
3. Hotkey Mode: Universal Text Transformation Shortcut & AI Prompt Transformation Shortcut
4. Profiles -> All 16 Command Categories (Spoken Triggers + Interactive Settings Test)
5. Zero Regression on the 7 existing dictation/transcription models
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.config as config_mod
from app.config import ConfigManager, DEFAULT_CONFIG
from app.commands import COMMAND_REGISTRY, COMMAND_MAP, match_spoken_command
from app.router.model_router import MODEL_REGISTRY
from app.security.security_manager import SecurityManager
from app.transformation.gemini_transform_service import (
    GeminiTransformService,
    DEFAULT_TRANSFORM_MODEL_CHAIN,
)
from app.transcription.engine import UnifiedTranscriptionEngine


def _mock_gemini_response(status_code: int, text: str = "", error_msg: str = "") -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    if status_code == 200:
        payload = {
            "candidates": [
                {"content": {"parts": [{"text": text}]}}
            ]
        }
        resp.json.return_value = payload
        resp.text = json.dumps(payload)
    else:
        payload = {"error": {"message": error_msg or f"HTTP {status_code} error"}}
        resp.json.return_value = payload
        resp.text = json.dumps(payload)
    return resp


class _ImmediateThread:
    """Runs thread target synchronously in unit tests for deterministic signal checks."""
    def __init__(self, target=None, daemon=None, name=None, args=(), kwargs=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self):
        if self._target:
            self._target(*self._args, **self._kwargs)


class TestPersistentSettingsAndKeyPrecedence(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)
        self.orig_app_dir = config_mod.APP_DIR
        self.orig_cfg_file = config_mod.CONFIG_FILE
        self.orig_hist_file = config_mod.HISTORY_FILE
        self.orig_env_gemini = os.environ.get("GEMINI_API_KEY")
        config_mod.APP_DIR = self.tmp_path
        config_mod.CONFIG_FILE = self.tmp_path / "config.json"
        config_mod.HISTORY_FILE = self.tmp_path / "history.json"

    def tearDown(self):
        config_mod.APP_DIR = self.orig_app_dir
        config_mod.CONFIG_FILE = self.orig_cfg_file
        config_mod.HISTORY_FILE = self.orig_hist_file
        if self.orig_env_gemini is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = self.orig_env_gemini
        self.tmp_dir.cleanup()

    def test_saved_user_key_overrides_stale_env_and_persists_cold_boot(self):
        os.environ["GEMINI_API_KEY"] = "AIzaSyStaleEnvKey999999"
        cm1 = ConfigManager()
        cm1.set_api_key("AIzaSyUserSavedRealKey12345")

        # Simulate stale .env key lingering in process env after restart
        os.environ["GEMINI_API_KEY"] = "AIzaSyStaleEnvKey999999"
        cm2 = ConfigManager()
        self.assertEqual(cm2.get_api_key(), "AIzaSyUserSavedRealKey12345")

    def test_custom_hotkey_presets_persist_across_restart(self):
        cm1 = ConfigManager()
        cm1.set("prompt_hotkey", "<ctrl>+<shift>+p")
        cm1.set("prompt_hotkey_display", "Ctrl + Shift + P")
        cm1.set("transform_hotkey", "<ctrl>+<shift>+t")
        cm1.set("transform_hotkey_display", "Ctrl + Shift + T")
        cm1.set("model_name", "offline-whisper")

        cm2 = ConfigManager()
        self.assertEqual(cm2.get_prompt_hotkey(), "<ctrl>+<shift>+p")
        self.assertEqual(cm2.get("prompt_hotkey_display"), "Ctrl + Shift + P")
        self.assertEqual(cm2.get_transform_hotkey(), "<ctrl>+<shift>+t")
        self.assertEqual(cm2.get("transform_hotkey_display"), "Ctrl + Shift + T")
        self.assertEqual(cm2.get("model_name"), "offline-whisper")

    def test_backup_recovery_on_corrupted_config_and_deep_merge(self):
        cm1 = ConfigManager()
        cm1.set("active_profile", "engineering")
        cm1.set("model_name", "groq-whisper-turbo")
        cm1.save_config()

        # Corrupt primary config.json; valid .json.bak should recover cleanly
        config_mod.CONFIG_FILE.write_text("{corrupt json", encoding="utf-8")
        cm2 = ConfigManager()
        self.assertEqual(cm2.get("active_profile"), "engineering")
        self.assertEqual(cm2.get("model_name"), "groq-whisper-turbo")
        self.assertIn("history_retention_days", cm2.get("security", {}))
        self.assertEqual(cm2.get("gemini_transform_model"), "gemini-2.5-flash")


class TestGeminiTransformService(unittest.TestCase):
    def test_empty_key_fails_cleanly_without_network(self):
        session = MagicMock(spec=requests.Session)
        svc = GeminiTransformService(api_key="", session=session)
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}, clear=False):
            res = svc.transform_universal_text("hello team sorry im late")
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "EMPTY_KEY")
        self.assertIn("Gemini API key", res.error_message)
        session.post.assert_not_called()

    def test_invalid_key_401_403_fast_fails_immediately(self):
        for code in (401, 403):
            session = MagicMock(spec=requests.Session)
            session.post.return_value = _mock_gemini_response(code, error_msg="API key not valid")
            svc = GeminiTransformService(api_key="AIzaSyInvalidKeyTest", session=session)
            res = svc.transform_universal_text("fix this sentence")
            self.assertFalse(res.success)
            self.assertEqual(res.error_type, "INVALID_KEY")
            self.assertEqual(res.error_code, code)
            self.assertEqual(session.post.call_count, 1)

    def test_404_rotates_cleanly_to_fallback_gemini_model(self):
        session = MagicMock(spec=requests.Session)
        session.post.side_effect = [
            _mock_gemini_response(404, error_msg="Model not found"),
            _mock_gemini_response(200, text="Hey team, sorry I'm late sending this."),
        ]
        svc = GeminiTransformService(api_key="AIzaSyValidKeyTest123", session=session)
        res = svc.transform_universal_text("hey team sorry im late sending this")
        self.assertTrue(res.success)
        self.assertEqual(res.model_used, DEFAULT_TRANSFORM_MODEL_CHAIN[1])
        self.assertEqual(res.text, "Hey team, sorry I'm late sending this.")
        self.assertEqual(session.post.call_count, 2)

    def test_rate_limit_and_timeout_surface_non_crashing_errors(self):
        session_429 = MagicMock(spec=requests.Session)
        session_429.post.return_value = _mock_gemini_response(429, error_msg="Quota exceeded")
        svc_429 = GeminiTransformService(api_key="AIzaSyValidKeyTest123", session=session_429)
        res_429 = svc_429.transform_universal_text("test text")
        self.assertFalse(res_429.success)
        self.assertEqual(res_429.error_type, "RATE_LIMITED")

        session_to = MagicMock(spec=requests.Session)
        session_to.post.side_effect = requests.exceptions.Timeout("Read timed out")
        svc_to = GeminiTransformService(api_key="AIzaSyValidKeyTest123", session=session_to)
        res_to = svc_to.transform_universal_text("test text")
        self.assertFalse(res_to.success)
        self.assertEqual(res_to.error_type, "TIMEOUT")

    def test_meta_prompt_uses_context_aware_instructions_and_preserves_domain(self):
        session = MagicMock(spec=requests.Session)
        expected_xml = (
            "<role>\n"
            "Senior Full-Stack Architect specializing in MERN e-commerce, Tailwind CSS, JWT authentication, and Stripe integration.\n"
            "</role>\n\n"
            "<context>\n"
            "Build a beginner-friendly coffee shop e-commerce platform using React.js, Tailwind CSS, Node.js, Express.js, MongoDB, JWT, and Stripe.\n"
            "</context>\n\n"
            "<task>\n"
            "Phase 1: Define Mongoose schemas and seed data.\n"
            "Phase 2: Implement Express REST APIs, JWT auth, and Stripe checkout.\n"
            "Phase 3: Implement React Cart and Auth context.\n"
            "Phase 4: Build Home, Product Listing, Product Details, Shopping Cart, Login/Register, and Checkout pages.\n"
            "</task>\n\n"
            "<constraints>\n"
            "- Deliver complete, runnable files with clean folder separation.\n"
            "- Use mobile-first responsive coffee-themed Tailwind layouts and zero TODO placeholders.\n"
            "</constraints>\n\n"
            "<output_format>\n"
            "Provide modular backend and frontend files step-by-step with local startup commands.\n"
            "</output_format>"
        )
        session.post.return_value = _mock_gemini_response(200, text=expected_xml)
        svc = GeminiTransformService(api_key="AIzaSyValidKeyTest123", session=session)

        coffee_input = (
            "Create a beginner-friendly e-commerce website for a coffee shop. "
            "Pages: Home, Product Listing, Product Details, Shopping Cart, Login/Register, Checkout. "
            "Tech Stack: React.js, Tailwind CSS, Node.js, Express.js, MongoDB, JWT, Stripe."
        )
        res = svc.transform_to_ai_prompt(coffee_input)
        self.assertTrue(res.success)
        self.assertIn("<role>", res.text)
        self.assertIn("MERN", res.text)
        self.assertNotIn("Next.js", res.text)
        self.assertIn("Stripe", res.text)
        self.assertNotIn("...", res.text)

        # Verify request headers & connect/read timeouts
        _, kwargs = session.post.call_args
        self.assertEqual(kwargs["headers"]["x-goog-api-key"], "AIzaSyValidKeyTest123")
        self.assertEqual(kwargs["timeout"], (2.0, GeminiTransformService.READ_TIMEOUT))

    def test_deprecated_model_config_migrates_and_list_models_discovers_fallback(self):
        # 1. Stale config value gemini-2.0-flash is excluded from transform chain
        mock_cfg = MagicMock()
        mock_cfg.get.side_effect = lambda k, default=None: "gemini-2.0-flash" if k == "gemini_transform_model" else default
        svc = GeminiTransformService(config_manager=mock_cfg, api_key="AIzaSyDiscTest123")
        chain = svc._get_model_chain()
        self.assertNotIn("gemini-2.0-flash", chain)
        self.assertEqual(chain[0], DEFAULT_TRANSFORM_MODEL_CHAIN[0])

        # 2. If all static chain models return 404, ListModels discovery finds a live model
        session = MagicMock(spec=requests.Session)
        list_resp = MagicMock(spec=requests.Response)
        list_resp.status_code = 200
        list_resp.json.return_value = {
            "models": [
                {"name": "models/gemini-9.9-flash", "supportedGenerationMethods": ["generateContent"]},
            ]
        }
        session.get.return_value = list_resp
        session.post.side_effect = [_mock_gemini_response(404, "Not found")] * len(DEFAULT_TRANSFORM_MODEL_CHAIN) + [
            _mock_gemini_response(200, text="Discovered model succeeded.")
        ]
        svc_disc = GeminiTransformService(api_key="AIzaSyDiscTest123", session=session)
        res = svc_disc.transform_universal_text("hello world")
        self.assertTrue(res.success)
        self.assertEqual(res.model_used, "gemini-9.9-flash")
        self.assertEqual(res.text, "Discovered model succeeded.")


class TestHotkeyModeAnd16CommandsWiring(unittest.TestCase):
    COMMAND_SAMPLE_OUTPUTS = {
        "professionalize": "Good afternoon,\n\nWe completed the v2 update yesterday on a $1,500 budget, and all tests passed.\n\n• v2 update completed\n• Budget: $1,500\n• All tests passed",
        "make_casual": "Hey there! Just a heads-up that our quarterly projection moved up by 12%.",
        "create_prompt": "<role>\nSenior Data & Backend Engineer.\n</role>\n<context>\nPostgreSQL deduplication script.\n</context>\n<task>\nConnect to Postgres and remove duplicate user accounts safely.\n</task>\n<constraints>\nUse transactional SQL and dry-run logging.\n</constraints>\n<output_format>\nRunnable Python script.\n</output_format>",
        "summarize": "**TL;DR:** Revenue grew 20% with 30,000 mobile downloads, but login issues lifted support tickets 15%—hiring 2 engineers and shipping a fix Friday.\n• Revenue +20%, 30,000 new mobile downloads\n• Support tickets +15% from login glitches\n• Hiring 2 engineers; auth hotfix by Friday",
        "grammar_fix": "Yesterday I went to office and saw three problem with the database.",
        "shorten": "Reboot the database server at 10 PM to prevent errors.",
        "expand": "Adopting microservices decouples our backend components so teams can deploy independently, scale bottleneck services without duplicating the monolith, and isolate failures before they cascade.",
        "explain": "Think of quantization like packing a suitcase with vacuum-sealed bags: faster-whisper shrinks 32-bit model weights into compact 8-bit numbers so they fit in smaller memory and run much faster while keeping accuracy high.",
        "translate": "Buenos días, nuestra reunión de equipo comenzará a las 10:30 AM.",
        "create_email": "Subject: Demo Ready for Review — Meeting Thursday at 2:00 PM\n\nHi Alex,\n\nThe demo is ready for your review. Are you available to meet this Thursday at 2:00 PM?\n\nBest regards,",
        "create_github_issue": "## Title\nSettings dialog crashes with AttributeError on Audio tab during clean install\n\n## Summary\nClicking the Audio tab on a clean install raises an AttributeError.\n\n## Steps to Reproduce\n1. Run clean install.\n2. Open Settings -> Audio.\n\n## Action Items\n- [ ] Guard missing attribute initialization",
        "create_github_pr": "## Summary\nRefactored audio recorder to use polyphase 16 kHz resampling and added unit tests.\n\n## Testing Checklist\n- [ ] Verify 16 kHz resample unit tests pass",
        "create_task": "- [ ] Deploy the new build\n- [ ] Verify database migrations\n- [ ] Notify the QA team\n- [ ] Update release notes",
        "generate_code": "```python\nfrom pathlib import Path\nimport hashlib\n\n\ndef hash_dir(path: str) -> dict[str, str]:\n    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(path).rglob('*') if p.is_file()}\n```",
        "format_text": "| Item | Price |\n|---|---|\n| Apples | $5 |\n| Bananas | $3 |\n| Oranges | $4 |",
        "rewrite": "This plan is solid, though starting immediately will help us avoid timeline slippage.",
    }

    def test_all_16_commands_run_via_gemini_key_across_every_non_gemini_dictation_model(self):
        self.assertEqual(len(COMMAND_REGISTRY), 16)

        for dictation_model in (
            "offline-whisper",
            "groq-whisper-turbo",
            "moonshine-onnx",
            "sherpa-onnx",
            "ollama-qwen2.5",
        ):
            mock_config = MagicMock()
            mock_config.get_api_key.return_value = "AIzaSyDedicatedCmdKey999"
            mock_config.get.side_effect = lambda k, default=None: (
                dictation_model if k in ("model_name", "model_mode") else
                "English" if k == "translate_target_language" else
                "gemini-2.5-flash" if k == "gemini_transform_model" else default
            )

            session = MagicMock(spec=requests.Session)
            svc = GeminiTransformService(config_manager=mock_config, session=session)

            # Bind GeminiFlowApp._execute_voice_command behavior directly without starting QApplication
            from app.main import GeminiFlowApp
            fake_app = MagicMock()
            fake_app.config = mock_config
            fake_app.gemini_transform_service = svc

            for cmd in COMMAND_REGISTRY:
                expected_out = self.COMMAND_SAMPLE_OUTPUTS[cmd.id]
                session.post.return_value = _mock_gemini_response(200, text=expected_out)

                ok, out = GeminiFlowApp._execute_voice_command(fake_app, cmd, cmd.sample_input)
                self.assertTrue(ok, f"[{dictation_model}] Command {cmd.id} failed: {out}")
                self.assertTrue(bool(out.strip()))
                is_valid, reason = cmd.validator(cmd.sample_input, out)
                self.assertTrue(is_valid, f"[{dictation_model}] Command {cmd.id} validator failed: {reason}")
                _, kwargs = session.post.call_args
                self.assertEqual(kwargs["headers"]["x-goog-api-key"], "AIzaSyDedicatedCmdKey999")

    def test_spoken_trigger_detection_matches_and_strips_all_16_categories(self):
        sample_spoken = [
            ("professionalize", "Make it more professional: hey boss the build finished yesterday"),
            ("make_casual", "Make casual. Please be advised our release is ready."),
            ("create_prompt", "Create AI prompt for a FastAPI rate limiter"),
            ("summarize", "Summarize this: Revenue grew 20 percent and churn dropped 4 percent."),
            ("grammar_fix", "Fix my grammar: yesterday i go to store"),
            ("shorten", "Make it shorter: In order to make sure this works properly."),
            ("expand", "Expand on this: Use Redis caching"),
            ("explain", "Explain concept: vector embeddings"),
            ("translate", "Translate to French: Good morning team"),
            ("create_email", "Draft email to Sarah about Friday release"),
            ("create_github_issue", "GitHub issue when clicking export app freezes"),
            ("create_github_pr", "GitHub PR added retry logic to webhook dispatcher"),
            ("create_task", "Task list ship release, update docs, run benchmarks"),
            ("generate_code", "Generate code write a python function for fibonacci"),
            ("format_text", "Format table apples 5 dollars, bananas 3 dollars"),
            ("rewrite", "Polish and rewrite this draft needs smoother flow"),
        ]
        for expected_id, spoken in sample_spoken:
            matched = match_spoken_command(spoken)
            self.assertIsNotNone(matched, f"Failed to match spoken trigger: {spoken}")
            cmd, payload = matched
            self.assertEqual(cmd.id, expected_id)
            self.assertTrue(len(payload) > 0, f"Empty payload extracted for: {spoken}")

        # Verify polyglot code validator accepts SQL/JS fences while keeping Python AST validation
        sql_ok, _ = COMMAND_MAP["generate_code"].validator("write sql", "```sql\nSELECT * FROM users;\n```")
        self.assertTrue(sql_ok)
        bad_py_ok, _ = COMMAND_MAP["generate_code"].validator("write python", "```python\ndef broken(:\n```")
        self.assertFalse(bad_py_ok)

    def test_validator_failure_retries_once_at_temperature_zero(self):
        session = MagicMock(spec=requests.Session)
        session.post.side_effect = [
            _mock_gemini_response(200, text="plain paragraph without table pipes"),
            _mock_gemini_response(200, text="| Fruit | Price |\n|---|---|\n| Apple | $5 |"),
        ]
        svc = GeminiTransformService(api_key="AIzaSyRetryTest123", session=session)
        res = svc.execute_command_category(COMMAND_MAP["format_text"], "apple 5 dollars")
        self.assertTrue(res.success)
        self.assertIn("| Fruit | Price |", res.text)
        self.assertEqual(session.post.call_count, 2)
        second_call_body = session.post.call_args_list[1].kwargs["json"]
        self.assertEqual(second_call_body["generationConfig"]["temperature"], 0.0)

    def test_hotkey_handlers_wire_to_gemini_transform_service(self):
        from app.main import GeminiFlowApp

        session = MagicMock(spec=requests.Session)
        svc = GeminiTransformService(api_key="AIzaSyHotkeyKey123", session=session)

        fake_app = MagicMock()
        fake_app.is_busy_processing = False
        fake_app.gemini_transform_service = svc
        fake_app.text_injector = MagicMock()
        fake_app.text_injector.get_selected_text_with_backup.return_value = ("hey team sorry im late sending this", "old")
        fake_app.hud = MagicMock()
        fake_app.tray = MagicMock()
        fake_app.hotkey_mgr = MagicMock()
        fake_app.signals = MagicMock()

        session.post.return_value = _mock_gemini_response(200, text="Hi team, apologies for the delay in sending this.")
        with patch("app.main.threading.Thread", _ImmediateThread), \
             patch("app.main.time.sleep"):
            GeminiFlowApp.on_transform_hotkey(fake_app)

        fake_app.signals.transform_finished.emit.assert_called_once_with(
            True,
            "Hi team, apologies for the delay in sending this.",
            "Universal Text Transform",
        )

        # Now test Alt+P prompt transformation error surfacing on invalid 401 key
        session.post.return_value = _mock_gemini_response(401, error_msg="Unauthorized key")
        fake_app.is_busy_processing = False
        fake_app.text_injector.get_selected_text_with_backup.return_value = ("Build a CLI app in Python", "old")
        with patch("app.main.threading.Thread", _ImmediateThread), \
             patch("app.main.time.sleep"):
            GeminiFlowApp.on_prompt_hotkey(fake_app)

        emitted_args = fake_app.signals.prompt_finished.emit.call_args[0]
        self.assertFalse(emitted_args[0])
        self.assertIn("401", emitted_args[1])

    def test_settings_interactive_command_test_runs_gemini_even_in_offline_mode(self):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PyQt6.QtWidgets import QApplication
        from app.ui.settings_dialog import SettingsDialog

        qt_app = QApplication.instance() or QApplication([])

        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "AIzaSySettingsCmdKey123"
        mock_config.get.side_effect = lambda k, default=None: (
            "offline-whisper" if k in ("model_name", "model_mode") else
            "English" if k == "translate_target_language" else
            "gemini-2.5-flash" if k == "gemini_transform_model" else default
        )

        session = MagicMock(spec=requests.Session)
        session.post.return_value = _mock_gemini_response(200, text="**TL;DR:** Revenue up 20%.\n• Shipping auth hotfix Friday")
        svc = GeminiTransformService(config_manager=mock_config, session=session)

        fake_dlg = MagicMock()
        fake_dlg.config = mock_config
        fake_dlg.main_app = MagicMock(gemini_transform_service=svc)
        fake_dlg.cmd_test_combo = MagicMock()
        fake_dlg.cmd_test_combo.currentData.return_value = "summarize"
        fake_dlg.txt_test_cmd_input = MagicMock()
        fake_dlg.txt_test_cmd_input.toPlainText.return_value = COMMAND_MAP["summarize"].sample_input
        fake_dlg.api_key_input = MagicMock()
        fake_dlg.api_key_input.text.return_value = "AIzaSySettingsCmdKey123"
        fake_dlg.lbl_cmd_validation_status = MagicMock()
        fake_dlg.txt_test_cmd_output = MagicMock()
        fake_dlg.btn_run_test_cmd = MagicMock()
        fake_dlg.command_test_finished = MagicMock()

        with patch("threading.Thread", _ImmediateThread):
            SettingsDialog._run_interactive_command_test(fake_dlg)

        emitted = fake_dlg.command_test_finished.emit.call_args[0]
        self.assertTrue(emitted[0])
        self.assertIn("TL;DR", emitted[1])

        SettingsDialog._on_interactive_command_test_result(fake_dlg, emitted[0], emitted[1], emitted[2], emitted[3])
        fake_dlg.txt_test_cmd_output.setText.assert_called_once()
        fake_dlg.lbl_cmd_validation_status.setText.assert_called_with("✅ Passed Validator (Gemini API)")

    def test_zero_regression_on_all_7_existing_models(self):
        expected_7 = {
            "offline-whisper",
            "groq-whisper-turbo",
            "moonshine-onnx",
            "sherpa-onnx",
            "gemini-2.5-flash",
            "gemini-3.5-flash-lite",
            "ollama-qwen2.5",
        }
        router_expected = expected_7 - {"sherpa-onnx"}
        self.assertTrue(router_expected.issubset(set(MODEL_REGISTRY.keys())))
        engine = UnifiedTranscriptionEngine(api_key="")
        diag = engine.get_all_models_diagnostics()
        diag_names = set(diag.keys())
        for model_id in expected_7:
            self.assertIn(model_id, diag_names)


if __name__ == "__main__":
    unittest.main()
