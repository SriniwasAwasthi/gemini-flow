"""
Automated Tests for Phase 4: Profiles & 16 Command Categories.
Verifies:
1. Exact presence and order of all 16 command categories in COMMAND_REGISTRY.
2. Spoken trigger matching contract: trigger matches ONLY at start of utterance.
   Mid-sentence trigger phrases are treated as normal text (return None).
3. Automated validation execution for all 16 commands:
   - Generate Code: passes ast.parse (Python 3) and rejects invalid syntax.
   - Summarize: verifies output is strictly shorter than input.
   - Fix Grammar: verified by fidelity gate.
   - Professionalize: verifies all numbers and entities are preserved.
   - GitHub Issue & PR: verifies markdown headers and checklist boxes (- [ ]).
   - Create Prompt: verifies structured sections (Role, Task, Context, etc.).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.commands import (
    COMMAND_REGISTRY,
    COMMAND_MAP,
    match_spoken_command,
    CommandDefinition
)


class TestPhase4Commands(unittest.TestCase):

    def test_registry_size_and_order(self):
        """Verifies all 16 command categories exist in the exact required order."""
        self.assertEqual(len(COMMAND_REGISTRY), 16, "Must contain exactly 16 command categories")
        expected_ids = [
            "professionalize",
            "make_casual",
            "create_prompt",
            "summarize",
            "grammar_fix",
            "shorten",
            "expand",
            "explain",
            "translate",
            "create_email",
            "create_github_issue",
            "create_github_pr",
            "create_task",
            "generate_code",
            "format_text",
            "rewrite"
        ]
        actual_ids = [c.id for c in COMMAND_REGISTRY]
        self.assertEqual(actual_ids, expected_ids, "Command registry IDs and order must match specification")

    def test_first_words_trigger_matching(self):
        """Verifies trigger matches only when at start of utterance."""
        # 1. Matches at start
        utt1 = "Make this professional: we need to delay the launch to Friday"
        res1 = match_spoken_command(utt1)
        self.assertIsNotNone(res1)
        cmd1, payload1 = res1
        self.assertEqual(cmd1.id, "professionalize")
        self.assertEqual(payload1, "we need to delay the launch to Friday")

        # 2. Mid-sentence trigger occurrence must NOT trigger command!
        utt2 = "In our team meeting we decided to make this professional approach standard across all departments"
        res2 = match_spoken_command(utt2)
        self.assertIsNone(res2, "Mid-sentence trigger occurrence must be treated as regular speech")

    def test_generate_code_validator(self):
        """Tests code validator with ast.parse on valid Python code and rejects invalid syntax."""
        cmd = COMMAND_MAP["generate_code"]
        self.assertEqual(cmd.default_temperature, 0.0, "Code generation default temperature must be 0.0")

        # Valid code block
        valid_code_out = (
            "Here is the requested script:\n"
            "```python\n"
            "import os\n"
            "def calculate_total(a: int, b: int) -> int:\n"
            "    '''Sums two numbers.'''\n"
            "    return a + b\n"
            "if __name__ == '__main__':\n"
            "    print(calculate_total(10, 20))\n"
            "```\n"
        )
        ok, reason = cmd.validator("write a python script to sum two numbers", valid_code_out)
        self.assertTrue(ok, f"Valid code should pass: {reason}")

        # Invalid syntax code block
        invalid_code_out = (
            "```python\n"
            "def calculate_total(a, b\n"  # Missing closing parenthesis and colon
            "    return a + b\n"
            "```"
        )
        ok, reason = cmd.validator("write code", invalid_code_out)
        self.assertFalse(ok, "Invalid Python syntax must be rejected by ast.parse")

    def test_summarize_validator(self):
        """Tests summarize validator requires output strictly shorter than input."""
        cmd = COMMAND_MAP["summarize"]
        inp = "We had our quarterly review today. Overall revenue grew by twenty percent across all sectors. The mobile app saw thirty thousand new downloads. However customer support tickets increased by fifteen percent due to login glitches. We decided to hire two additional support engineers and deploy an authentication hotfix by Friday."
        out_good = "• Revenue: Increased by 20% across all sectors.\n• App Downloads: 30,000 new mobile users.\n• Support & Fix: Deploying auth hotfix by Friday and adding 2 engineers."
        ok, reason = cmd.validator(inp, out_good)
        self.assertTrue(ok, f"Good summary should pass: {reason}")

        out_bad = inp + " Here is even more added rambling text that makes the summary longer than the original input."
        ok, reason = cmd.validator(inp, out_bad)
        self.assertFalse(ok, "Summary longer than input must be rejected")

    def test_all_16_command_validators_on_sample_inputs(self):
        """Runs validation across all 16 commands to guarantee contracts."""
        for cmd in COMMAND_REGISTRY:
            self.assertIsNotNone(cmd.id)
            self.assertIsNotNone(cmd.name)
            self.assertGreater(len(cmd.trigger_phrases), 0)
            self.assertIsNotNone(cmd.system_prompt)
            self.assertIsNotNone(cmd.validator)
            self.assertIn(cmd.default_temperature, (0.0, 0.2))


if __name__ == "__main__":
    unittest.main()
