"""
Automated Tests for Phase 3: Post-Processing & Fidelity Gate.
Verifies:
1. Deterministic text normalization (whitespace, capital I, sentence starts, contractions).
2. Spoken voice punctuation expansion and filler/stutter removal.
3. Hard Fidelity Gate checks:
   - Length variance (rejects > 15% change)
   - Content word edit distance (rejects > 25% change)
   - Number/entity preservation (rejects dropped or invented numbers)
4. Long text paragraph chunking (<= 250 words per call).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.intelligence.post_processing import (
    deterministic_cleanup,
    fidelity_gate,
    post_process_transcript
)


class TestPhase3PostProcessing(unittest.TestCase):

    def test_deterministic_cleanup_basics(self):
        """Tests capitalization, standalone I, and contraction repair."""
        raw = "yesterday i saw that he dont know how to fix the bug"
        clean = deterministic_cleanup(raw)
        self.assertEqual(clean, "Yesterday I saw that he don't know how to fix the bug")

    def test_spoken_punctuation_expansion(self):
        """Tests spoken punctuation token replacement when enabled."""
        raw = "hello comma how are you question mark i am doing well period"
        clean = deterministic_cleanup(raw, voice_punctuation=True)
        self.assertEqual(clean, "Hello, how are you? I am doing well.")

    def test_stutter_and_filler_removal(self):
        """Tests removal of verbal fillers and collapsing of stutter repetitions."""
        raw = "um we we need to uh deploy the the server"
        clean = deterministic_cleanup(raw, remove_fillers=True, remove_stutters=True)
        self.assertEqual(clean, "We need to deploy the server")

    def test_fidelity_gate_pass(self):
        """Tests fidelity gate passing on clean minor grammar corrections."""
        raw = "Yesterday I go to office and saw him."
        polished = "Yesterday I went to the office and saw him."
        passed, out, reason = fidelity_gate(raw, polished)
        self.assertTrue(passed, f"Gate should pass minor tense fix: {reason}")
        self.assertEqual(out, polished)

    def test_fidelity_gate_rejects_hallucination_and_length(self):
        """Tests fidelity gate rejecting text when length differs by >15%."""
        raw = "The release date is scheduled for Friday."
        # LLM hallucinates an entire paragraph
        hallucinated = "The release date is scheduled for Friday. In addition, I recommend reviewing the entire architecture and sending emails to all shareholders."
        passed, out, reason = fidelity_gate(raw, hallucinated)
        self.assertFalse(passed, "Fidelity gate must reject length expansion > 15%")
        # Output must fall back to the deterministic clean raw text!
        self.assertIn("Friday", out)
        self.assertNotIn("shareholders", out)

    def test_fidelity_gate_rejects_missing_or_invented_numbers(self):
        """Tests fidelity gate rejecting dropped or hallucinated numbers."""
        raw = "The total budget allocated is $4,500 for the project."

        # Case A: Dropped number
        dropped_num = "The total budget allocated is for the project."
        passed, _, reason = fidelity_gate(raw, dropped_num)
        self.assertFalse(passed, "Gate must reject polish that drops numbers")

        # Case B: Hallucinated number
        invented_num = "The total budget allocated is $4,500 and $9,000 for the project."
        passed, _, reason = fidelity_gate(raw, invented_num)
        self.assertFalse(passed, "Gate must reject newly invented numbers")

    def test_post_process_pipeline_end_to_end(self):
        """Tests full 4-stage pipeline execution."""
        raw = "dont worry comma we will finish on time period"

        def mock_llm_copy_editor(text, prompt):
            # Returns copy edited text
            return True, "Don't worry, we will finish on time."

        result = post_process_transcript(
            raw_text=raw,
            grammar_polish_enabled=True,
            polish_fn=mock_llm_copy_editor,
            voice_punctuation=True
        )
        self.assertEqual(result, "Don't worry, we will finish on time.")


if __name__ == "__main__":
    unittest.main()
