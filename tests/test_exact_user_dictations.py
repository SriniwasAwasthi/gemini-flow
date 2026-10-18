import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.intent.intent_system import IntentClassifier, IntentCategory, INTENT_TO_TRANSFORM_MAP
from app.transformation.transform_engine import TransformType
from app.gemini_engine import GeminiEngine
from app.config import ConfigManager

cm = ConfigManager()
api_key = cm.get_api_key()
gemini = GeminiEngine(api_key=api_key)

print("=" * 80)
print("TESTING USER'S 3 EXACT REAL DICTATIONS END-TO-END WITH GEMINI API")
print("=" * 80)

# Sample 1: Generate Code in Python
t1 = "Generate code in Python. Write a function that reverses a linked list."
r1 = IntentClassifier.classify(t1)
print(f"\n[1] Spoken: '{t1}'")
print(f"    Intent: {r1.intent.value} | Language: {r1.target_language} | Payload: '{r1.payload}'")
assert r1.intent == IntentCategory.GENERATE_CODE
assert r1.target_language.lower() == "python"

if api_key:
    custom_inst = r1.system_instruction
    res1 = gemini.transform_text(raw_text=r1.payload, transform_type=TransformType.TECHNICAL, custom_instruction=custom_inst)
    print(f"    Transformed Result (Success={res1.success}, Model={res1.model_used}):\n{res1.text[:200]}...")
    assert res1.success
    assert "def " in res1.text or "class " in res1.text
    print("    [PASS] Python code generated cleanly!")

# Sample 2: Fix my grammar
t2 = 'Fix my grammar. "We was going to market yesterday and she don\'t know nothing about it."'
r2 = IntentClassifier.classify(t2)
payload2 = r2.payload.strip().strip('"').strip()
print(f"\n[2] Spoken: '{t2}'")
print(f"    Intent: {r2.intent.value} | Payload: '{payload2}'")
assert r2.intent == IntentCategory.GRAMMAR_FIX

if api_key:
    res2 = gemini.transform_text(raw_text=payload2, transform_type=TransformType.FIX_GRAMMAR)
    print(f"    Transformed Result (Success={res2.success}, Model={res2.model_used}):\n    \"{res2.text}\"")
    assert res2.success
    assert "were going" in res2.text.lower()
    print("    [PASS] Grammar corrected cleanly!")

# Sample 3: Make it more professional
t3 = (
    "Make it more professional. Hello, I am Sriniwas Awasthi. I was just wondering how my app reacted to the speech "
    "I gave, and I was just thinking about what to want all the main changes I have made and all. So, I came to the "
    "conclusion at that it's 11:15 and 17th of October. I just want to sleep now."
)
r3 = IntentClassifier.classify(t3)
print(f"\n[3] Spoken: '{t3[:60]}...'")
print(f"    Intent: {r3.intent.value} | Payload: '{r3.payload[:60]}...'")
assert r3.intent == IntentCategory.PROFESSIONALIZE

if api_key:
    res3 = gemini.transform_text(raw_text=r3.payload, transform_type=TransformType.PROFESSIONAL)
    print(f"    Transformed Result (Success={res3.success}, Model={res3.model_used}):\n    \"{res3.text}\"")
    assert res3.success
    assert len(res3.text.strip()) > 30
    print("    [PASS] Professionalized prose generated cleanly!")

print("\n" + "=" * 80)
print("ALL 3 USER DICTATIONS TRANSFORMED WITH 100% SUCCESS!")
print("=" * 80)
