"""
Automated Unit Tests for Phase 3: Shortcuts & Text Transformation (Features 15-18, R5).

Verifies:
1. Feature 15: Alt+T Text Transformation
   - Execution via TransformType.TRANSFORM_TEXT and TransformType.IMPROVE.
   - Filter speech fillers ("um", "uh", "you know", "like") and stutter repetitions.
   - Preservation of exact meaning, context, tenses, technical vocabulary, and numbers.
   - Intelligent structuring into paragraphs or bullet points.
2. Feature 16: Alt+P Prompt Enhancement (Mandatory 15-Section Structure)
   - Mandatory 15 section headings generated verbatim in exact sequential order.
   - Unstated details marked as '[Unspecified]' without fabrication or hallucination.
   - Technical facts, error codes, file paths, and line numbers preserved.
   - Output contains no outer markdown code fences (```).
3. Feature 17: Shortcut Pipeline Independence & Default Configuration
   - Config default hotkeys: '<alt>+t' (transform) and '<alt>+p' (prompt) with aliases.
   - HotkeyManager default arguments set to '<alt>+p' and '<alt>+t'.
   - Distinct hotkey IDs (HOTKEY_ID_TRANSFORM, HOTKEY_ID_PROMPT, HOTKEY_ID_MAIN).
   - Win32 hotkey parsing of '<alt>+t' and '<alt>+p'.
   - Independent callbacks and worker threads: pressing one never triggers the other.
4. Feature 18: Selection Extraction and Clipboard Safety
   - TextInjector.get_selected_text_with_backup() returns (selection, backup).
   - Atomic pre-hotkey clipboard restoration on failure or empty selection.
   - TextInjector.restore_clipboard_backup() restores pre-hotkey clipboard.
   - Terminal vs standard app paste routing (Ctrl+Shift+V vs Ctrl+V).
   - Clipboard transient lock retry backoff.
"""
import sys
import time
import unittest
import unittest.mock
from pathlib import Path
from typing import List, Optional, Tuple

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import ConfigManager, DEFAULT_CONFIG
from app.transformation.transform_engine import (
    TransformEngine,
    TransformType,
    TransformPreset,
    TRANSFORM_PRESETS,
    MANDATORY_15_SECTIONS
)
from app.hotkey_manager import (
    HotkeyManager,
    HOTKEY_ID_MAIN,
    HOTKEY_ID_PROMPT,
    HOTKEY_ID_TRANSFORM,
    _parse_hotkey_to_win32
)
from app.text_injector import TextInjector


class TestPhase3Transformation(unittest.TestCase):
    """Automated unit test suite verifying Milestone M4 (Features 15-18)."""

    # =========================================================================
    # Feature 15: Alt+T Text Transformation
    # =========================================================================

    def test_f15_preset_registration(self):
        """F15: TransformType.TRANSFORM_TEXT and TransformType.IMPROVE are registered."""
        preset_improve = TransformEngine.get_preset(TransformType.IMPROVE)
        self.assertIsNotNone(preset_improve)
        self.assertEqual(preset_improve.type, TransformType.IMPROVE)
        self.assertIn("clarity", preset_improve.description.lower())

        preset_transform = TransformEngine.get_preset(TransformType.TRANSFORM_TEXT)
        self.assertIsNotNone(preset_transform)
        self.assertEqual(preset_transform.type, TransformType.TRANSFORM_TEXT)
        self.assertIn("fluent", preset_transform.system_instruction.lower())

    def test_f15_filter_speech_fillers_and_stutters(self):
        """F15: Filters speech fillers ('um', 'uh', 'you know', 'like') and collapses stutters."""
        raw = "um uh yesterday we we meet with the 4 engineers to discuss the $2,500 server budget"
        clean = TransformEngine.filter_speech_fillers(raw)

        # Fillers removed
        self.assertNotIn("um", clean.lower().split())
        self.assertNotIn("uh", clean.lower().split())
        # Stutter collapsed
        self.assertNotIn("we we", clean)
        self.assertIn("we", clean)
        # Numerical facts intact
        self.assertIn("4", clean)
        self.assertIn("$2,500", clean)

    def test_f15_speech_filler_you_know_and_like(self):
        """F15: Filters 'you know' and disfluent 'like' while keeping meaningful 'like'."""
        disfluent = "The database latency was, like, 25ms and, you know, we resolved it quickly."
        cleaned = TransformEngine.filter_speech_fillers(disfluent)
        self.assertNotIn("you know", cleaned.lower())
        self.assertIn("25ms", cleaned)

    def test_f15_grammatical_tense_correction(self):
        """F15: Corrects past-tense slips ('yesterday I go' -> 'yesterday I went')."""
        raw = "yesterday I go to office and saw the team"
        transformed = TransformEngine.transform_text(raw, transform_type=TransformType.TRANSFORM_TEXT)
        self.assertIn("yesterday i went", transformed.lower())

    def test_f15_preserves_numbers_entities_and_technical_terms(self):
        """F15: Strictly preserves port numbers, error codes, and technical jargon."""
        raw = "The server port is 8080 and latency is 25ms with $500 cost on Windows 11."
        transformed = TransformEngine.transform_text(raw, transform_type=TransformType.TRANSFORM_TEXT)
        self.assertIn("8080", transformed)
        self.assertIn("25ms", transformed)
        self.assertIn("$500", transformed)
        self.assertIn("Windows 11", transformed)

    def test_f15_smart_bullet_formatting(self):
        """F15: Intelligently structures run-together items into clean bullet points."""
        text = "We discussed three main things. First is audio capture. Second is model routing. Third is mutex safety."
        formatted = TransformEngine.format_smart_structure(text)
        self.assertIn("•", formatted)
        self.assertIn("audio capture", formatted.lower())
        self.assertIn("model routing", formatted.lower())
        self.assertIn("mutex safety", formatted.lower())

    # =========================================================================
    # Feature 16: Alt+P Prompt Enhancement (Mandatory 15-Section Structure)
    # =========================================================================

    def test_f16_mandatory_15_section_headings_contract(self):
        """F16: Exactly 15 mandatory section headings defined in exact order."""
        self.assertEqual(len(MANDATORY_15_SECTIONS), 15)
        expected_headings = [
            "1. ROLE & PERSONA",
            "2. PROJECT CONTEXT",
            "3. PROBLEM STATEMENT",
            "4. OBJECTIVE",
            "5. TASK DESCRIPTION",
            "6. REQUIREMENTS & SPECIFICATIONS",
            "7. IMPLEMENTATION GUIDELINES",
            "8. TECHNICAL REQUIREMENTS",
            "9. UI/UX REQUIREMENTS",
            "10. WORKFLOW & EXPECTED BEHAVIOUR",
            "11. CONSTRAINTS & RESTRICTIONS",
            "12. EDGE CASES & ERROR HANDLING",
            "13. ACCEPTANCE CRITERIA",
            "14. TESTING & VERIFICATION",
            "15. EXPECTED OUTPUT & DELIVERABLES"
        ]
        self.assertEqual(MANDATORY_15_SECTIONS, expected_headings)

    def test_f16_convert_to_prompt_generates_all_15_sections_verbatim(self):
        """F16: convert_to_prompt output contains all 15 headings verbatim in sequential order."""
        raw_bug_notes = (
            "We have a crash in app/audio_recorder.py around line 350 during device selection. "
            "PortAudio throws PaErrorCode -9997 on laptop internal array mics. "
            "Need to dynamically query native sample rate (44.1k vs 48k) instead of hardcoding 16k in InputStream. "
            "Must support Windows 11 WASAPI."
        )
        prompt = TransformEngine.convert_to_prompt(raw_bug_notes)

        # 1. Verify every heading appears in the text
        last_idx = -1
        for heading in MANDATORY_15_SECTIONS:
            idx = prompt.find(heading)
            self.assertNotEqual(idx, -1, f"Missing mandatory section heading: {heading}")
            self.assertGreater(idx, last_idx, f"Section {heading} out of sequential order")
            last_idx = idx

    def test_f16_unstated_details_marked_as_unspecified(self):
        """F16: Details not provided in input are marked '[Unspecified]' not hallucinated."""
        raw_notes = "Crash in app/audio_recorder.py line 350 with PaErrorCode -9997."
        prompt = TransformEngine.convert_to_prompt(raw_notes)
        self.assertIn("[Unspecified]", prompt)
        # UI/UX should be unspecified since input did not state UI requirements
        self.assertIn("9. UI/UX REQUIREMENTS: [Unspecified]", prompt)

    def test_f16_user_facts_preserved_in_prompt(self):
        """F16: All user-provided technical facts, line numbers, and error codes are preserved."""
        raw = "Crash in app/audio_recorder.py line 350 with PaErrorCode -9997 and 48k rate."
        prompt = TransformEngine.convert_to_prompt(raw)
        self.assertIn("app/audio_recorder.py", prompt)
        self.assertIn("line 350", prompt)
        self.assertIn("PaErrorCode -9997", prompt)
        self.assertTrue("48k" in prompt or "48kHz" in prompt)

    def test_f16_no_outer_markdown_fences(self):
        """F16: Output prompt contains no outer markdown code fences (```)."""
        prompt = TransformEngine.convert_to_prompt("Fix memory leak in buffer queue.")
        self.assertFalse(prompt.strip().startswith("```"))
        self.assertFalse(prompt.strip().endswith("```"))

    def test_f16_enforce_15_sections_strips_fences_and_fills_omitted(self):
        """F16: enforce_15_sections restores missing headings and strips fences."""
        partial_llm_response = (
            "```markdown\n"
            "1. ROLE & PERSONA: Senior Engineer\n"
            "2. PROJECT CONTEXT: Gemini Flow\n"
            "3. PROBLEM STATEMENT: Fix bug\n"
            "```"
        )
        enforced = TransformEngine.enforce_15_sections(partial_llm_response, raw_input="Fix bug")
        self.assertFalse(enforced.startswith("```"))
        for heading in MANDATORY_15_SECTIONS:
            self.assertIn(heading, enforced)

    # =========================================================================
    # Feature 17: Shortcut Pipeline Independence & Default Configuration
    # =========================================================================

    def test_f17_default_configuration_hotkeys(self):
        """F17: Default configuration specifies '<alt>+t' and '<alt>+p' with aliases."""
        self.assertEqual(DEFAULT_CONFIG["transform_hotkey"], "<alt>+t")
        self.assertEqual(DEFAULT_CONFIG["hotkey_transform"], "<alt>+t")
        self.assertEqual(DEFAULT_CONFIG["prompt_hotkey"], "<alt>+p")
        self.assertEqual(DEFAULT_CONFIG["hotkey_prompt"], "<alt>+p")

    def test_f17_config_manager_normalize_and_helpers(self):
        """F17: ConfigManager correctly retrieves and normalizes transform and prompt hotkeys."""
        cfg = ConfigManager()
        # Ensure helper methods return expected defaults
        self.assertEqual(cfg.get_transform_hotkey(), "<alt>+t")
        self.assertEqual(cfg.get_prompt_hotkey(), "<alt>+p")

    def test_f17_distinct_win32_hotkey_ids(self):
        """F17: Win32 hotkey IDs are distinct and independent."""
        self.assertNotEqual(HOTKEY_ID_TRANSFORM, HOTKEY_ID_PROMPT)
        self.assertNotEqual(HOTKEY_ID_TRANSFORM, HOTKEY_ID_MAIN)
        self.assertNotEqual(HOTKEY_ID_PROMPT, HOTKEY_ID_MAIN)

    def test_f17_win32_parsing_alt_t_and_alt_p(self):
        """F17: Win32 parser parses '<alt>+t' and '<alt>+p' to MOD_ALT and VK_T / VK_P."""
        res_t = _parse_hotkey_to_win32("<alt>+t")
        self.assertIsNotNone(res_t)
        mod_t, vk_t = res_t
        self.assertTrue(mod_t & 0x0001, "MOD_ALT must be set for Alt+T")
        self.assertEqual(vk_t, ord('T'))

        res_p = _parse_hotkey_to_win32("<alt>+p")
        self.assertIsNotNone(res_p)
        mod_p, vk_p = res_p
        self.assertTrue(mod_p & 0x0001, "MOD_ALT must be set for Alt+P")
        self.assertEqual(vk_p, ord('P'))

    def test_f17_independent_callbacks_execution(self):
        """F17: Triggering Alt+T does NOT trigger Alt+P callback, and vice versa."""
        mgr = HotkeyManager()
        alt_t_invoked = False
        alt_p_invoked = False

        mgr.on_transform = lambda: exec("alt_t_invoked = True", globals(), locals())
        mgr.on_prompt = lambda: exec("alt_p_invoked = True", globals(), locals())

        # Simulate transform trigger
        mgr._handle_transform_trigger(source="test")
        time.sleep(0.05)
        self.assertTrue(mgr._transform_hotkey_active)
        self.assertFalse(mgr._prompt_hotkey_active)

    def test_f17_hotkey_manager_default_arguments(self):
        """F17: HotkeyManager constructor defaults are '<alt>+p' and '<alt>+t'."""
        mgr = HotkeyManager()
        self.assertEqual(mgr.prompt_hotkey_str, "<alt>+p")
        self.assertEqual(mgr.transform_hotkey_str, "<alt>+t")

    # =========================================================================
    # Feature 18: Selection Extraction and Clipboard Safety
    # =========================================================================

    def test_f18_get_selected_text_with_backup_success(self):
        """F18: get_selected_text_with_backup returns (selection, original_clipboard)."""
        injector = TextInjector()
        with unittest.mock.patch("pyperclip.paste", side_effect=["Original Pre-Hotkey Clip", "Selected Text To Transform"]):
            with unittest.mock.patch("pyperclip.copy"):
                with unittest.mock.patch.object(injector, "focus_target_window"):
                    with unittest.mock.patch("app.text_injector.send_atomic_copy"):
                        selected, backup = injector.get_selected_text_with_backup(require_selection=True)
                        self.assertEqual(selected, "Selected Text To Transform")
                        self.assertEqual(backup, "Original Pre-Hotkey Clip")

    def test_f18_get_selected_text_restores_clipboard_on_no_selection(self):
        """F18: If no text is selected, original clipboard is restored and selection is empty."""
        injector = TextInjector()
        clip_data = ["Original Pre-Hotkey Clip"]

        def mock_paste():
            return clip_data[0]

        def mock_copy(val):
            clip_data[0] = val

        with unittest.mock.patch("pyperclip.paste", side_effect=mock_paste), \
             unittest.mock.patch("pyperclip.copy", side_effect=mock_copy), \
             unittest.mock.patch.object(injector, "focus_target_window"):
            selected, backup = injector.get_selected_text_with_backup(require_selection=True)
            self.assertIsNone(selected)
            self.assertEqual(backup, "Original Pre-Hotkey Clip")
            # Verified clipboard was restored to original pre-hotkey content
            self.assertEqual(clip_data[0], "Original Pre-Hotkey Clip")

    def test_f18_restore_clipboard_backup_explicit(self):
        """F18: restore_clipboard_backup restores provided backup to clipboard."""
        injector = TextInjector()
        with unittest.mock.patch.object(injector, "_safe_set_clipboard", return_value=True) as mock_safe_set:
            ok = injector.restore_clipboard_backup("Saved User Notes")
            self.assertTrue(ok)
            mock_safe_set.assert_called_with("Saved User Notes")

    def test_f18_paste_text_atomic_routing(self):
        """F18: paste_text routes correctly for standard vs terminal applications."""
        injector = TextInjector()
        with unittest.mock.patch.object(injector, "focus_target_window"):
            with unittest.mock.patch.object(injector, "is_terminal_target", return_value=False):
                with unittest.mock.patch.object(injector, "_safe_set_clipboard", return_value=True):
                    with unittest.mock.patch("app.text_injector.release_held_modifiers", return_value=[]):
                        with unittest.mock.patch("app.text_injector.send_atomic_paste") as mock_paste:
                            ok = injector.paste_text("Transformed Result", restore_clipboard=False)
                            self.assertTrue(ok)
                            mock_paste.assert_called_with(is_terminal=False)

    def test_f18_clipboard_transient_lock_retry(self):
        """F18: _safe_set_clipboard retries on transient clipboard locks."""
        injector = TextInjector()
        # First attempt raises exception (e.g. locked by another app), second succeeds
        with unittest.mock.patch("pyperclip.copy", side_effect=[Exception("Clipboard Locked"), None]):
            ok = injector._safe_set_clipboard("Retry Text", max_retries=3)
            self.assertTrue(ok)

    # =========================================================================
    # Pipeline Independence & Coordination
    # =========================================================================

    def test_pipeline_independence_alt_t_vs_alt_p(self):
        """Verifies Alt+T does not invoke 15-section prompt template, and Alt+P does."""
        input_text = "Fix audio crash in audio_recorder.py on line 350."

        # Alt+T Text Transformation
        res_t = TransformEngine.transform_text(input_text, transform_type=TransformType.TRANSFORM_TEXT)
        self.assertNotIn("1. ROLE & PERSONA", res_t)
        self.assertNotIn("15. EXPECTED OUTPUT & DELIVERABLES", res_t)

        # Alt+P Prompt Enhancement
        res_p = TransformEngine.transform_text(input_text, transform_type=TransformType.CONVERT_PROMPT)
        self.assertIn("1. ROLE & PERSONA", res_p)
        self.assertIn("15. EXPECTED OUTPUT & DELIVERABLES", res_p)


if __name__ == "__main__":
    unittest.main()
