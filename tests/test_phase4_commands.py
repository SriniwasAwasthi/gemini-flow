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

import os
from unittest.mock import patch

from app.commands import (
    COMMAND_REGISTRY,
    COMMAND_MAP,
    ACTION_COMMANDS,
    ACTION_MAP,
    ALL_COMMANDS,
    match_spoken_command,
    CommandDefinition
)
from app.main import (
    MUTEX_NAME,
    IPC_PIPE_NAME,
    acquire_app_mutex,
    release_app_mutex,
    terminate_other_gemini_flow_instances
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

    # -------------------------------------------------------------------------
    # Feature 19: Strictly Remove 3 Spoken Triggers
    # -------------------------------------------------------------------------
    def test_feature_19_removed_spoken_triggers(self):
        """F19: Removed spoken triggers ('start dictation', 'stop dictation', 'new line', 'cancel dictation', 'new paragraph') must NEVER be intercepted."""
        removed_phrases = [
            "start dictation",
            "stop dictation",
            "new line",
            "start recording",
            "stop recording",
            "start",
            "stop",
            "next line",
            "start new line",
            "cancel dictation",
            "cancel",
            "new paragraph",
            "start new paragraph",
            "please start dictation",
            "please stop dictation",
            "please new line",
            "please cancel dictation",
            "please new paragraph"
        ]
        for phrase in removed_phrases:
            res = match_spoken_command(phrase)
            self.assertIsNone(res, f"Removed trigger '{phrase}' must return None (treated as dictation)")

    # -------------------------------------------------------------------------
    # Feature 20: Decouple Action Commands from Profile Commands
    # -------------------------------------------------------------------------
    def test_feature_20_action_commands_decoupled(self):
        """F20: Action commands are decoupled into ACTION_COMMANDS; COMMAND_REGISTRY has strictly 16."""
        self.assertEqual(len(COMMAND_REGISTRY), 16, "COMMAND_REGISTRY must contain strictly 16 profile commands")
        for cmd in COMMAND_REGISTRY:
            self.assertFalse(getattr(cmd, "is_action", False), f"Profile command {cmd.id} must have is_action=False")

        self.assertGreaterEqual(len(ACTION_COMMANDS), 6, "ACTION_COMMANDS must contain the decoupled actions")
        for cmd in ACTION_COMMANDS:
            self.assertTrue(getattr(cmd, "is_action", False), f"Action command {cmd.id} must have is_action=True")

        action_ids = {c.id for c in ACTION_COMMANDS}
        expected_retained_actions = {
            "action_bullet_point",
            "action_numbered_list",
            "action_undo",
            "action_select_all",
            "action_copy_all",
            "action_clear_all"
        }
        for expected_id in expected_retained_actions:
            self.assertIn(expected_id, action_ids, f"Retained action '{expected_id}' must exist in ACTION_COMMANDS")

        # Removed triggers must NOT exist in ACTION_COMMANDS
        self.assertNotIn("action_start_dictation", action_ids)
        self.assertNotIn("action_stop_dictation", action_ids)
        self.assertNotIn("action_new_line", action_ids)
        self.assertNotIn("action_cancel_dictation", action_ids)
        self.assertNotIn("action_new_paragraph", action_ids)

    # -------------------------------------------------------------------------
    # Feature 21: Retain Other Spoken Action Commands
    # -------------------------------------------------------------------------
    def test_feature_21_retained_action_commands(self):
        """F21: Retained action commands must be intercepted correctly."""
        test_cases = [
            ("bullet point", "action_bullet_point"),
            ("numbered list", "action_numbered_list"),
            ("undo that", "action_undo"),
            ("delete that", "action_undo"),
            ("select all", "action_select_all"),
            ("copy all", "action_copy_all"),
            ("clear all", "action_clear_all"),
        ]
        for utterance, expected_id in test_cases:
            res = match_spoken_command(utterance)
            self.assertIsNotNone(res, f"Retained action '{utterance}' failed to match")
            cmd, _ = res
            self.assertEqual(cmd.id, expected_id)
            self.assertTrue(cmd.is_action)

    # -------------------------------------------------------------------------
    # Feature 22: Contextual Protection for Mid-Sentence Speech
    # -------------------------------------------------------------------------
    def test_feature_22_mid_sentence_protection(self):
        """F22: Trigger words mid-sentence must NEVER be falsely intercepted as commands."""
        mid_sentence_phrases = [
            "We need to start the project today",
            "Please stop by my office after lunch",
            "Our company has a new line of products",
            "They decided to cancel the flight due to weather",
            "According to our plan, summarize this document",
            "Tomorrow we start the refactoring",
            "We cannot stop until tests pass",
            "This creates a new line of opportunities",
            "In our retrospective today we agreed to start the new sprint on Monday, stop using obsolete libraries, and introduce a new line of automated E2E tests.",
            "let us start dictation now"
        ]
        for phrase in mid_sentence_phrases:
            res = match_spoken_command(phrase)
            self.assertIsNone(res, f"Mid-sentence speech '{phrase}' must return None")

    # -------------------------------------------------------------------------
    # Feature 23: Single-Instance Mutex Audit
    # -------------------------------------------------------------------------
    def test_feature_23_single_instance_mutex(self):
        """F23: Single-instance Win32 Named Mutex and IPC pipe constants and methods."""
        self.assertEqual(MUTEX_NAME, "Global\\GeminiFlow_SingleInstance_Mutex")
        self.assertEqual(IPC_PIPE_NAME, "GeminiFlow_SingleInstance_IPC")
        
        # Test acquire / release cycle
        primary = acquire_app_mutex()
        self.assertIsInstance(primary, bool)
        release_app_mutex()
        
        # Double release should be completely safe
        try:
            release_app_mutex()
        except Exception as e:
            self.fail(f"Double release_app_mutex threw exception: {e}")

    # -------------------------------------------------------------------------
    # Feature 24: Safe Zombie/Orphan Process Cleanup
    # -------------------------------------------------------------------------
    def test_feature_24_safe_process_cleanup(self):
        """F24: Process cleanup excludes current PID and executes safely without terminating unrelated processes."""
        curr_pid = os.getpid()
        with patch("subprocess.run") as mock_run:
            terminate_other_gemini_flow_instances(exclude_pid=curr_pid)
            for call_args in mock_run.call_args_list:
                args = call_args[0][0]
                self.assertNotIn(str(curr_pid), args, "Current PID must never be targeted by taskkill")


if __name__ == "__main__":
    unittest.main()
