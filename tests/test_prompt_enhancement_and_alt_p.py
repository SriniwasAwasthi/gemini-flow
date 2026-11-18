import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import ConfigManager
from app.gemini_engine import GeminiEngine
from app.transformation.transform_engine import TransformEngine, TransformType, FIVE_PART_PROMPT_TAGS
from app.text_injector import TextInjector


class TestPromptEnhancementAndAltP(unittest.TestCase):

    def setUp(self):
        self.config = ConfigManager()
        self.gemini = GeminiEngine(self.config)
        self.injector = TextInjector()
        self.required_tags = [
            "<role>", "</role>",
            "<context>", "</context>",
            "<task>", "</task>",
            "<constraints>", "</constraints>",
            "<output_format>", "</output_format>"
        ]

        self.ex1 = "Create a fast audio recorder for Gemini Flow that captures sound from Bluetooth earbuds on Windows and doesn't crash when unplugged"
        self.ex2 = "Make a login page with authentication for my website with React, Tailwind, and FastAPI."

    def test_example_1_prompt_contains_all_5_part_blueprint_tags(self):
        prompt = TransformEngine.convert_to_prompt(self.ex1, model_client=self.gemini)
        self.assertTrue(len(prompt) > 200)
        for tag in self.required_tags:
            self.assertIn(tag, prompt, f"Missing tag '{tag}' in Example 1 prompt")
        self.assertNotIn("1. ROLE & PERSONA:", prompt)
        self.assertNotIn("15. EXPECTED OUTPUT", prompt)

    def test_example_2_prompt_contains_all_5_part_blueprint_tags(self):
        prompt = TransformEngine.convert_to_prompt(self.ex2, model_client=self.gemini)
        self.assertTrue(len(prompt) > 200)
        for tag in self.required_tags:
            self.assertIn(tag, prompt, f"Missing tag '{tag}' in Example 2 prompt")
        self.assertNotIn("1. ROLE & PERSONA:", prompt)
        self.assertNotIn("15. EXPECTED OUTPUT", prompt)

    def test_gemini_enhance_to_ai_prompt_guarantees_5_part_blueprint(self):
        ok, prompt = self.gemini.enhance_to_ai_prompt(self.ex1)
        self.assertTrue(ok)
        for tag in self.required_tags:
            self.assertIn(tag, prompt, f"Missing tag '{tag}' in GeminiEngine prompt output")

    def test_transform_text_improves_speech_to_fluent_english(self):
        improved = TransformEngine.transform_text(
            text="today is Monday sorry today is Tuesday and we buyed three apple",
            transform_type=TransformType.IMPROVE,
            model_client=None
        )
        self.assertTrue(len(improved) > 10)
        self.assertNotIn("<role>", improved)
        self.assertNotIn("1. ROLE & PERSONA", improved)

    def test_text_injector_has_clipboard_fallback(self):
        self.assertTrue(hasattr(self.injector, "get_clipboard_text"))
        text = self.injector.get_clipboard_text()
        self.assertIsInstance(text, str)


if __name__ == "__main__":
    unittest.main()
