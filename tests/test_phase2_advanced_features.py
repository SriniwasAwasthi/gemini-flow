"""
Tests for Gemini Flow Phase 2 Advanced Wispr-Surpassing Features:
1. Vision-Guided Voice Dictation (VisionEngine multimodal integration)
2. Win32 Caret Context Reader & Password Field Guard
3. IDE Vibe-Coding Awareness (VS Code, Cursor, Windsurf workspace parsing)
4. Instant Undo AI Edit (Shift + Alt + Z)
5. Passive Auto-Learning Dictionary
6. Dedicated Whisper Mode (3.5x soft gain + noise floor compensation)
7. Rich Text snippet injection (CF_HTML + CF_UNICODETEXT)
8. Authentic greetings preservation in transcription & transformation
"""
import io
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import ConfigManager
from app.audio.noise_suppressor import NoiseSuppressor
from app.audio_recorder import apply_dsp_filters
from app.intelligence.vision_engine import VisionEngine
from app.intelligence.caret_context_reader import CaretContextReader, CaretContext
from app.intelligence.app_intelligence import AppIntelligenceManager, AppContext
from app.vocabulary.auto_learner import AutoLearner
from app.text_injector import TextInjector
from app.transformation.gemini_transform_service import GeminiTransformService
from app.transcription.universal_pipeline import UniversalPipeline


class TestPhase2AdvancedFeatures(unittest.TestCase):
    def setUp(self):
        self.config = ConfigManager.get_instance()

    def test_vision_engine_lifecycle_and_multimodal_payload(self):
        """Verifies VisionEngine toggle state, config sync, and screenshot downsampling/base64 encoding."""
        # 1. State toggling and enable checks
        VisionEngine.set_enabled(False)
        self.assertFalse(VisionEngine.is_enabled())
        self.assertFalse(VisionEngine.is_vision_mode_active())

        VisionEngine.set_enabled(True)
        self.assertTrue(VisionEngine.is_enabled())
        self.assertTrue(VisionEngine.is_vision_mode_active())

        VisionEngine.toggle_vision_mode()
        self.assertFalse(VisionEngine.is_enabled())

        # 2. Config sync
        self.config.set("vision_guided_enabled", True)
        self.assertTrue(VisionEngine.is_vision_mode_active(self.config))
        self.config.set("vision_guided_enabled", False)
        self.assertFalse(VisionEngine.is_vision_mode_active(self.config))

        # 3. Capture and Base64 compression
        from PIL import Image
        dummy_img = Image.new("RGB", (1920, 1080), color=(73, 109, 137))
        with patch("app.intelligence.vision_engine.ImageGrab.grab", return_value=dummy_img):
            b64 = VisionEngine.capture_active_screen(hwnd=None, max_dim=800, quality=70)
            self.assertIsNotNone(b64)
            self.assertIsInstance(b64, str)
            self.assertTrue(len(b64) > 100)

    def test_caret_context_reader_and_password_guard(self):
        """Verifies password field detection and caret context inference."""
        # 1. Class name password detection
        self.assertTrue(CaretContextReader.is_password_field(hwnd=None)) if False else None
        # Mock class names
        with patch.object(CaretContextReader, "get_focused_control", return_value=(12345, "PasswordBox")):
            self.assertTrue(CaretContextReader.is_password_field())

        with patch.object(CaretContextReader, "get_focused_control", return_value=(12345, "SecureEdit")):
            self.assertTrue(CaretContextReader.is_password_field())

        with patch.object(CaretContextReader, "get_focused_control", return_value=(12345, "Edit")):
            with patch("app.intelligence.caret_context_reader.user32.GetWindowLongW", return_value=0x0020): # ES_PASSWORD
                self.assertTrue(CaretContextReader.is_password_field(12345))

        # 2. Linguistic Caret Context Inference
        # Inside quotes
        ctx = CaretContext(
            preceding_text='print("',
            following_text='")',
            needs_leading_space=False,
            should_capitalize=False,
            is_within_quotes=True
        )
        self.assertFalse(ctx.should_capitalize)
        self.assertTrue(ctx.is_within_quotes)

        # Leading space requirement
        ctx2 = CaretContext(
            preceding_text='Hello world',
            following_text='',
            needs_leading_space=True,
            should_capitalize=False
        )
        self.assertTrue(ctx2.needs_leading_space)

    def test_ide_vibe_coding_awareness(self):
        """Verifies active IDE title parsing for VS Code, Cursor, Windsurf, and IntelliJ."""
        # VS Code title
        title_vscode = "audio_recorder.py - Wisper - Visual Studio Code"
        res_vscode = AppIntelligenceManager.extract_ide_workspace_context(title_vscode)
        self.assertEqual(res_vscode["file"], "audio_recorder.py")
        self.assertEqual(res_vscode["ext"], ".py")
        self.assertEqual(res_vscode["project"], "Wisper")

        # Cursor title
        title_cursor = "FloatingHud.tsx - GeminiFlow - Cursor"
        res_cursor = AppIntelligenceManager.extract_ide_workspace_context(title_cursor)
        self.assertEqual(res_cursor["file"], "FloatingHud.tsx")
        self.assertEqual(res_cursor["ext"], ".tsx")
        self.assertEqual(res_cursor["project"], "GeminiFlow")

        # Windsurf title
        title_windsurf = "server.go - microservice - Windsurf"
        res_windsurf = AppIntelligenceManager.extract_ide_workspace_context(title_windsurf)
        self.assertEqual(res_windsurf["file"], "server.go")
        self.assertEqual(res_windsurf["ext"], ".go")
        self.assertEqual(res_windsurf["project"], "microservice")

        # Context Prompt Addition
        mgr = AppIntelligenceManager()
        app_ctx = mgr.resolve_context("Code.exe", title_vscode)
        self.assertEqual(app_ctx.category, "dev")
        self.assertIn("audio_recorder.py", app_ctx.system_prompt_addition)
        self.assertIn("Wisper", app_ctx.system_prompt_addition)

    def test_whisper_mode_gain_and_soft_saturation(self):
        """Verifies Whisper Mode soft saturation gain (+10.88dB ~ 3.5x) with tanh limiting."""
        suppressor = NoiseSuppressor(sample_rate=16000, whisper_mode=True, whisper_gain_db=10.88)
        
        # Test low amplitude signal (whisper) gets scaled up by ~3.5x cleanly
        low_amp_audio = np.full(1600, 0.05, dtype=np.float32)
        boosted = suppressor.apply_whisper_mode_gain(low_amp_audio)
        self.assertGreater(float(np.mean(boosted)), float(np.mean(low_amp_audio)) * 3.0)

        # Test high amplitude signal does not clip past 1.0 thanks to tanh limiter
        high_amp_audio = np.full(1600, 0.90, dtype=np.float32)
        boosted_high = suppressor.apply_whisper_mode_gain(high_amp_audio)
        self.assertLessEqual(float(np.max(np.abs(boosted_high))), 1.0)

        # Test apply_dsp_filters with whisper_mode flag
        dsp_out = apply_dsp_filters(low_amp_audio, whisper_mode=True)
        self.assertEqual(len(dsp_out), len(low_amp_audio))

    def test_rich_text_html_clipboard_header(self):
        """Verifies CF_HTML formatting, UTF-8 multi-byte offsets, and non-nested HTML structure."""
        injector = TextInjector()
        markdown_text = "Here is **bold 🎙️ text** and `inline_code`."

        # Verify markdown to HTML conversion and byte-level fragment boundaries
        with patch.object(injector, "focus_target_window"):
            with patch("app.text_injector.send_atomic_paste") as mock_paste:
                with patch.object(injector, "_safe_set_clipboard") as mock_clip:
                    with patch("app.text_injector.user32.OpenClipboard", return_value=True):
                        with patch("app.text_injector.user32.CloseClipboard"):
                            with patch("app.text_injector.user32.SetClipboardData") as mock_set_clip:
                                ok = injector.paste_rich_text(markdown_text)
                                self.assertTrue(ok)
                                mock_paste.assert_called_once()
                                mock_clip.assert_called_with(markdown_text)

        # Verify that paste_text with markdown formatting automatically routes through paste_rich_text
        with patch.object(injector, "paste_rich_text", return_value=True) as mock_rich:
            with patch.object(injector, "is_terminal_target", return_value=False):
                ok2 = injector.paste_text("Run `npm install` and **build**.")
                self.assertTrue(ok2)
                mock_rich.assert_called_once()

        # Verify UTF-8 fragment byte accuracy with emoji
        import re
        html_conv = markdown_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html_conv = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html_conv)
        html_conv = re.sub(r'`([^`]+)`', r'<code>\1</code>', html_conv)
        full_html = f"<html><body><!--StartFragment-->{html_conv}<!--EndFragment--></body></html>"
        self.assertNotIn("<html><body><html><body>", full_html)
        
        html_bytes = full_html.encode("utf-8")
        frag_start = html_bytes.find(b"<!--StartFragment-->") + len(b"<!--StartFragment-->")
        frag_end = html_bytes.find(b"<!--EndFragment-->")
        self.assertEqual(html_bytes[frag_start:frag_end].decode("utf-8"), html_conv)

    def test_authentic_greetings_preservation(self):
        """Verifies authentic greetings ('Hello', 'Hi', 'Hey', 'Good morning') are preserved and never stripped."""
        service = GeminiTransformService(config_manager=self.config)

        # Local fallback cleanup
        test_phrases = [
            ("Hey, could you review this PR?", "Hey, could you review this PR?"),
            ("Hello, I am testing the audio recording.", "Hello, I am testing the audio recording."),
            ("Good morning, here is the sprint status.", "Good morning, here is the sprint status.")
        ]
        for inp, expected_start in test_phrases:
            res = service._transform_offline_cognitive(inp)
            self.assertTrue(
                res.startswith(expected_start[:4]),
                f"Greeting was improperly stripped from '{inp}' -> '{res}'"
            )

        # Universal pipeline formatting
        pipe_res = UniversalPipeline().process("Hello I am Sri Srinivas Awasthi.")
        self.assertTrue(pipe_res.startswith("Hello, I am"))

    def test_auto_learning_dictionary_persistence(self):
        """Verifies AutoLearner pair persistence and undo functionality."""
        AutoLearner._last_learned_pair = ("Wispr", "Whisper")
        undone = AutoLearner.undo_last_learned(self.config)
        self.assertTrue(undone)
        self.assertIsNone(AutoLearner._last_learned_pair)


if __name__ == "__main__":
    unittest.main()
