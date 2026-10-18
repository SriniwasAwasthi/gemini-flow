"""
Comprehensive Verification Suite for Spoken Voice Command Triggers & Intent Routing
Verifies all 16 command categories, trigger detection, payload extraction, and Gemini transformations.
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.intent.intent_system import IntentClassifier, IntentCategory, INTENT_TO_TRANSFORM_MAP
from app.transformation.transform_engine import TransformType, TransformEngine
from app.gemini_engine import GeminiEngine
from app.config import ConfigManager

def test_voice_command_triggers():
    print("=" * 80)
    print("       GEMINI FLOW SPOKEN VOICE COMMANDS & INTENT ROUTING TEST SUITE")
    print("=" * 80)

    cm = ConfigManager()
    api_key = cm.get_api_key()
    gemini = GeminiEngine(api_key=api_key)

    # -------------------------------------------------------------------------
    # TEST 1: User's Exact "Make it more professional" Dictation
    # -------------------------------------------------------------------------
    print("\n[TEST 1] User's Exact Voice Command: 'Make it more professional.'")
    user_speech = (
        "Make it more professional. Hello, I am Sriniwas Awasthi. I was just wondering how my app reacted "
        "to the speech I gave and I was just thinking about what to what all to the main changes I have made "
        "and all. So, I came to the conclusion that it's 11:15 and 17th of October, I just want to sleep now."
    )

    intent_res = IntentClassifier.classify(user_speech)
    print(f"  - Detected Intent: {intent_res.intent.value}")
    print(f"  - Trigger Matched: '{intent_res.command_trigger}'")
    print(f"  - Cleaned Payload: '{intent_res.payload[:70]}...'")

    assert intent_res.intent == IntentCategory.PROFESSIONALIZE, f"Error: Expected PROFESSIONALIZE, got {intent_res.intent}"
    assert "Make it more professional" not in intent_res.payload, "Error: Trigger was not stripped from payload!"
    assert "Hello, I am Sriniwas Awasthi" in intent_res.payload, "Error: User greeting/name lost from payload!"

    # Test Live Transformation with Gemini
    if api_key:
        print("  - Running Live Gemini Transformation...")
        trans_res = gemini.transform_text(
            raw_text=intent_res.payload,
            transform_type=TransformType.PROFESSIONAL
        )
        print(f"  - Live Transformation Success: {trans_res.success} (Model: {trans_res.model_used})")
        print(f"  - Formatted Output:\n    \"{trans_res.text}\"")
        assert trans_res.success, f"Transformation failed: {trans_res.error_message}"
        assert len(trans_res.text.strip()) > 30, "Transformed text is too short!"
    print("  [PASS] Test 1: 'Make it more professional' correctly routed and transformed.")

    # -------------------------------------------------------------------------
    # TEST 2: User's Exact "Fix my grammar:" Spoken Trigger
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Spoken Trigger: 'Fix my grammar:'")
    grammar_speech = "Fix my grammar: We was going to the market yesterday and she don't know nothing about it."
    intent_g = IntentClassifier.classify(grammar_speech)
    print(f"  - Detected Intent: {intent_g.intent.value}")
    print(f"  - Trigger Matched: '{intent_g.command_trigger}'")
    print(f"  - Cleaned Payload: '{intent_g.payload}'")

    assert intent_g.intent == IntentCategory.GRAMMAR_FIX, f"Error: Expected GRAMMAR_FIX, got {intent_g.intent}"
    assert "Fix my grammar" not in intent_g.payload
    assert "We was going" in intent_g.payload

    if api_key:
        trans_g = gemini.transform_text(
            raw_text=intent_g.payload,
            transform_type=TransformType.FIX_GRAMMAR
        )
        print(f"  - Live Grammar Fix Output:\n    \"{trans_g.text}\"")
        assert trans_g.success
        assert "were going" in trans_g.text.lower()
    print("  [PASS] Test 2: 'Fix my grammar:' correctly routed and corrected.")

    # -------------------------------------------------------------------------
    # TEST 3: User's Exact "Generate code in Python:" Spoken Trigger
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Spoken Trigger: 'Generate code in Python:'")
    code_speech = "Generate code in Python: write a function that reverses a linked list"
    intent_c = IntentClassifier.classify(code_speech)
    print(f"  - Detected Intent: {intent_c.intent.value}")
    print(f"  - Target Language: '{intent_c.target_language}'")
    print(f"  - Trigger Matched: '{intent_c.command_trigger}'")
    print(f"  - Cleaned Payload: '{intent_c.payload}'")

    assert intent_c.intent == IntentCategory.GENERATE_CODE, f"Error: Expected GENERATE_CODE, got {intent_c.intent}"
    assert intent_c.target_language.lower() == "python"
    assert "Generate code in Python" not in intent_c.payload
    assert intent_c.payload == "write a function that reverses a linked list"
    print("  [PASS] Test 3: 'Generate code in Python:' language extracted and payload cleaned.")

    # -------------------------------------------------------------------------
    # TEST 4: Clipboard Fallback (Spoken Trigger with No Payload)
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Clipboard Fallback when User Speaks ONLY the Trigger")
    selected_text = "hey team we gotta delay the launch to friday cause database test failed"
    pure_cmd = "Make this professional."
    intent_pure = IntentClassifier.classify(pure_cmd, clipboard_fallback=selected_text)
    print(f"  - Spoken Input: '{pure_cmd}'")
    print(f"  - Detected Intent: {intent_pure.intent.value}")
    print(f"  - Fallback Payload Used: '{intent_pure.payload}'")

    assert intent_pure.intent == IntentCategory.PROFESSIONALIZE
    assert intent_pure.payload == selected_text
    print("  [PASS] Test 4: Screen selection / Clipboard text successfully used as payload.")

    # -------------------------------------------------------------------------
    # TEST 5: Standard Dictation Non-Trigger Protection (Zero False Positives)
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Standard Dictation Immunity (Zero False Positives)")
    regular_dictations = [
        "Hey, I was just thinking of the some advantage of the forest.",
        "We need to hire a professional developer for our team.",
        "My grammar teacher taught me English in school.",
        "Please send me the report by tomorrow morning.",
    ]
    for rd in regular_dictations:
        intent_rd = IntentClassifier.classify(rd)
        assert intent_rd.intent == IntentCategory.DICTATE, f"False trigger on: '{rd}' (Got {intent_rd.intent})"
    print("  [PASS] Test 5: Regular dictations containing trigger words in the body remain DICTATE.")

    # -------------------------------------------------------------------------
    # TEST 6: All 16 Built-in Spoken Command Categories Trigger Verification
    # -------------------------------------------------------------------------
    print("\n[TEST 6] All 16 Command Categories Trigger Verification")
    all_categories_samples = [
        ("Make this professional: We need more budget.", IntentCategory.PROFESSIONALIZE),
        ("Make this casual: The sync has been postponed.", IntentCategory.MAKE_CASUAL),
        ("Turn this into a prompt: Build a web scraper.", IntentCategory.CREATE_PROMPT),
        ("Summarize this: Key decisions from the meeting.", IntentCategory.SUMMARIZE),
        ("Fix grammar: They has been working on it.", IntentCategory.GRAMMAR_FIX),
        ("Make this shorter: We are writing to notify you that...", IntentCategory.SHORTEN),
        ("Expand this: Trees provide shade.", IntentCategory.EXPAND),
        ("Explain this: Quantum entanglement basics.", IntentCategory.EXPLAIN),
        ("Translate this to French: Good morning everyone.", IntentCategory.TRANSLATE),
        ("Draft an email about: Launch date moved to next week.", IntentCategory.CREATE_EMAIL),
        ("Create a GitHub issue: Memory leak in worker thread.", IntentCategory.CREATE_GITHUB_ISSUE),
        ("Create a pull request: Add voice intent classifier.", IntentCategory.CREATE_GITHUB_PR),
        ("Create task list: Setup database, write unit tests.", IntentCategory.CREATE_TASK),
        ("Write a python script to: scrape headlines.", IntentCategory.GENERATE_CODE),
        ("Format this into a table: Name, Age, Role, City.", IntentCategory.FORMAT_TEXT),
        ("Rewrite this: The project went well yesterday.", IntentCategory.REWRITE),
    ]

    for sample_text, expected_intent in all_categories_samples:
        res_cat = IntentClassifier.classify(sample_text)
        assert res_cat.intent == expected_intent, f"Mismatch on '{sample_text}': Expected {expected_intent}, got {res_cat.intent}"
        assert res_cat.payload != "", f"Empty payload for '{sample_text}'"

    print("  [PASS] All 16 Command Categories verified with 100% classification accuracy.")

    print("\n" + "=" * 80)
    print("     ALL SPOKEN VOICE COMMAND & INTENT TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 80)

if __name__ == "__main__":
    test_voice_command_triggers()
