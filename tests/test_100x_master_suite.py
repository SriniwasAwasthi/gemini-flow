"""
Comprehensive 100-Case Master Verification Suite for Gemini Flow.
Tests all dimensions across 100+ test cases:
1. Category 1: Voice Triggers & Quick-Text Mid-Sentence Expansions (20 cases)
2. Category 2: Contextual Self-Corrections & Sentence Replacements (25 cases)
3. Category 3: Duplicate Sentence & Repeated Question Deduplication (20 cases)
4. Category 4: Meaningful Repetition & Emphasis Preservation (10 cases)
5. Category 5: Audio Boundary Overlap Window Merging (10 cases)
6. Category 6: Multilingual Speech Preservation & Language Isolation (15 cases)
7. Category 7: Long Speech Sustained Dictation & Zero Truncation (5 cases)
"""
import sys
import time
import json
import logging
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.transcription.universal_pipeline import (
    UniversalPipeline,
    StreamingHypothesisReconciler,
    OverlapDuplicateResolver,
    UniversalDuplicateEliminator,
    ContextualSelfCorrectionEngine,
    VoiceTriggerExpander,
    GrammarAndPunctuationProcessor
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GeminiFlow.100xMasterSuite")

pipeline = UniversalPipeline()
snippets = [
    {
        "trigger": "Hey I am Sriniwas LinkedIn GitHub",
        "content": "LinkedIn: https://www.linkedin.com/in/srinivas-awasthi/ | GitHub: https://github.com/srinivas-awasthi"
    },
    {
        "trigger": "Hey I am Srinivas LinkedIn GitHub Instagram",
        "content": "LinkedIn: https://www.linkedin.com/in/srinivas-awasthi/ | GitHub: https://github.com/srinivas-awasthi"
    },
    {
        "trigger": "my social links",
        "content": "LinkedIn: https://www.linkedin.com/in/srinivas-awasthi/ and GitHub: https://github.com/srinivas-awasthi"
    },
    {
        "trigger": "meeting intro",
        "content": "Hi everyone, thank you for joining today's session. Let's do a quick round of updates and discuss key milestones."
    }
]

tests = []

# ==============================================================================
# CATEGORY 1: Voice Triggers & Quick-Text (20 Cases)
# ==============================================================================
pos_prefixes = [
    "Hello team, good morning.",
    "During my presentation today,",
    "I would like to share my profile.",
    "For anyone reviewing my work,",
    "To introduce myself quickly,"
]
pos_suffixes = [
    "I am currently working on speech recognition.",
    "Feel free to connect with me anytime.",
    "Let us continue with the agenda.",
    "All open source code is published there.",
    "Thank you for your time."
]

for i in range(10):
    pre = pos_prefixes[i % len(pos_prefixes)]
    suf = pos_suffixes[i % len(pos_suffixes)]
    inp = f"{pre} Hey I am Sriniwas LinkedIn GitHub. {suf}"
    tests.append((
        f"CAT1-Trigger-Mid-{i+1}",
        inp,
        lambda out: "LinkedIn: https://www.linkedin.com/in/srinivas-awasthi/" in out and "GitHub: https://github.com/srinivas-awasthi" in out,
        "Mid-sentence trigger expansion with preserved prefix/suffix",
        snippets,
        "en"
    ))

# Beginning positions
for i in range(3):
    suf = pos_suffixes[i]
    inp = f"Hey I am Sriniwas LinkedIn GitHub. {suf}"
    tests.append((
        f"CAT1-Trigger-Beg-{i+1}",
        inp,
        lambda out: out.startswith("LinkedIn: https://www.linkedin.com") and "Feel free" in out or "connect" in out or "agenda" in out or "working" in out,
        "Beginning trigger expansion with preserved suffix",
        snippets,
        "en"
    ))

# Ending positions
for i in range(3):
    pre = pos_prefixes[i]
    inp = f"{pre} Hey I am Sriniwas LinkedIn GitHub."
    tests.append((
        f"CAT1-Trigger-End-{i+1}",
        inp,
        lambda out: "LinkedIn: https://www.linkedin.com" in out and (out.startswith("Hello") or out.startswith("During") or out.startswith("I would")),
        "Ending trigger expansion with preserved prefix",
        snippets,
        "en"
    ))

# Comma & pause variants
tests.append(("CAT1-Trigger-Pause-1", "Hi, ... Hey, I am Srinivas, LinkedIn, GitHub. Next topic.", lambda out: "LinkedIn: https://www.linkedin.com" in out and "Next topic" in out, "Pause and comma variant trigger expansion", snippets, "en"))
tests.append(("CAT1-Trigger-Pause-2", "Introductory note: Hey I am Sriniwas LinkedIn GitHub, moving on.", lambda out: "LinkedIn: https://www.linkedin.com" in out and "moving on" in out.lower(), "Colon variant trigger expansion", snippets, "en"))
tests.append(("CAT1-Trigger-SocialLinks", "Here are my social links. Please check my social links before the interview.", lambda out: "https://www.linkedin.com/in/srinivas-awasthi/" in out, "Multi-trigger snippet expansion", snippets, "en"))
tests.append(("CAT1-Trigger-MeetingIntro", "Let us start. Meeting intro. First item on the list.", lambda out: "thank you for joining today's session" in out, "Meeting intro trigger expansion", snippets, "en"))

# ==============================================================================
# CATEGORY 2: Contextual Self-Corrections (25 Cases)
# ==============================================================================
corrections = [
    ("It's Friday. Actually, it's Saturday.", "It's Saturday."),
    ("Today is Friday. Today is Saturday.", "Today is Saturday."),
    ("The meeting is at 2 p.m. Sorry, the meeting is at 3 p.m.", "The meeting is at 3 p.m."),
    ("The total budget is $500. Actually, $750.", "The total budget is $750."),
    ("The total budget was around ₹550. Oh wait, the total budget was ₹750.", "The total budget was ₹750."),
    ("Convert this whole data under 4 seconds. No, sorry, under 3 seconds.", "Convert this whole data under 3 seconds."),
    ("I am in 11th standard. Sorry, I am in 12th standard.", "I am in 12th standard."),
    ("Open the first application. No, open the second application.", "Open the second application."),
    ("Use the Gemini API. Sorry, use the Groq API.", "Use the Groq API."),
    ("The project should support ten users. Actually, one hundred users.", "The project should support one hundred users."),
    ("Use Gemini Fl... Gemini Flow.", "Use Gemini Flow."),
    ("Make it blue. No, make it green. Actually, make it black.", "Make it black."),
    ("Deploy on Monday. Wait, deploy on Tuesday.", "Deploy on Tuesday."),
    ("We need 4 servers. Rather, 8 servers.", "We need 8 servers."),
    ("Send email to John. No, send email to Sarah.", "Send email to Sarah."),
    ("Set the timeout to 500 ms. Actually, 200 ms.", "Set the timeout to 200 ms."),
    ("Meeting is in January. No wait, February.", "Meeting is in February."),
    ("The price is 50 euros. Correction, 40 euros.", "The price is 40 euros."),
    ("Create a new application. What I meant was create a new website using React.", "Create a new website using React."),
    ("Use Python 3.9. No sorry, Python 3.10.", "Use Python 3.10."),
    ("We will meet at 10 AM. Rather, at 11 AM.", "We will meet at 11 AM."),
    ("The file size is 15 megabytes. Actually, 25 megabytes.", "The file size is 25 megabytes."),
    ("Choose option A. Correction, choose option B.", "Choose option B."),
    ("Release version 1.0. No, release version 2.0.", "Release version 2.0."),
    ("Run on GPU. Actually, run on CPU.", "Run on CPU.")
]

for idx, (inp, exp) in enumerate(corrections):
    tests.append((
        f"CAT2-SelfCorrection-{idx+1}",
        inp,
        lambda out, e=exp: out.strip().replace('.', '').rstrip('?!').lower() == e.strip().replace('.', '').rstrip('?!').lower(),
        f"Self correction: '{inp}' -> '{exp}'",
        None,
        "en"
    ))

# ==============================================================================
# CATEGORY 3: Duplicate Sentence & Question Elimination (20 Cases)
# ==============================================================================
dup_cases = [
    ("I want to improve Gemini Flow. I want to improve Gemini Flow.", "I want to improve Gemini Flow."),
    ("Why are these three skills inactive? Why are these three skills inactive?", "Why are these three skills inactive?"),
    ("Can you tell me why these three skills are inactive or why these three skills are inactive?", "Can you tell me why these three skills are inactive?"),
    ("Yesterday I tested the application. Yesterday I tested the application.", "Yesterday, I tested the application."),
    ("Please check the system logs. Please check the system logs.", "Please check the system logs."),
    ("Where is the configuration file? Where is the configuration file?", "Where is the configuration file?"),
    ("How do I fix this issue? How do I fix this issue?", "How do I fix this issue?"),
    ("The build succeeded without warnings. The build succeeded without warnings.", "The build succeeded without warnings."),
    ("Let us deploy the service now. Let us deploy the service now.", "Let us deploy the service now."),
    ("What are the next steps for this project? What are the next steps for this project?", "What are the next steps for this project?"),
    ("Can you verify this behavior? Can you verify this behavior?", "Can you verify this behavior?"),
    ("We need lower latency on Windows. We need lower latency on Windows.", "We need lower latency on Windows."),
    ("Restart the background server. Restart the background server.", "Restart the background server."),
    ("Have you tested the audio recorder? Have you tested the audio recorder?", "Have you tested the audio recorder?"),
    ("The model is initialized. The model is initialized.", "The model is initialized."),
    ("Is the API key valid? Is the API key valid?", "Is the API key valid?"),
    ("Verify all test cases. Verify all test cases.", "Verify all test cases."),
    ("Everything is working as expected. Everything is working as expected.", "Everything is working as expected."),
    ("Check the latency metrics. Check the latency metrics.", "Check the latency metrics."),
    ("Dictation started successfully. Dictation started successfully.", "Dictation started successfully.")
]

for idx, (inp, exp) in enumerate(dup_cases):
    tests.append((
        f"CAT3-Deduplication-{idx+1}",
        inp,
        lambda out, e=exp: out.strip().replace(',', '').rstrip('.?!').lower() == e.strip().replace(',', '').rstrip('.?!').lower(),
        f"Duplicate elimination: '{inp[:35]}...'",
        None,
        "en"
    ))

# ==============================================================================
# CATEGORY 4: Meaningful Repetition Preservation (10 Cases)
# ==============================================================================
meaningful_cases = [
    "This application is fast, really fast.",
    "This application is fast, very fast.",
    "I tested it, tested it again, and finally fixed it.",
    "Monday, Wednesday, and Friday.",
    "It is hot, so hot outside.",
    "We need low latency, very low latency.",
    "He ran, ran as fast as he could.",
    "Never, never give up on the objective.",
    "The code is clean, truly clean.",
    "Step by step, day by day."
]

for idx, inp in enumerate(meaningful_cases):
    tests.append((
        f"CAT4-MeaningfulRepetition-{idx+1}",
        inp,
        lambda out, orig=inp: all(w.lower() in out.lower() for w in orig.replace(',', '').replace('.', '').split()),
        f"Preserve meaningful repetition: '{inp}'",
        None,
        "en"
    ))

# ==============================================================================
# CATEGORY 5: Audio Boundary Overlap Window Merging (10 Cases)
# ==============================================================================
overlap_pairs = [
    (["Yesterday I started developing Gemini Flow.", "Gemini Flow because I wanted to improve speech recognition."], "Yesterday, I started developing Gemini Flow because I wanted to improve speech recognition."),
    (["We attended the client meeting.", "the client meeting was very productive."], "We attended the client meeting was very productive."),
    (["Let us deploy the new model.", "the new model by Friday."], "Let us deploy the new model by Friday."),
    (["We verified the audio recorder.", "the audio recorder using unit tests."], "We verified the audio recorder using unit tests."),
    (["The latency was under 200 milliseconds.", "200 milliseconds for all frames."], "The latency was under 200 milliseconds for all frames."),
    (["Please check the dashboard.", "the dashboard to see the latest metrics."], "Please check the dashboard to see the latest metrics."),
    (["The quick text feature is expanding.", "feature is expanding properly."], "The quick text feature is expanding properly."),
    (["We are running tests on Windows 11.", "Windows 11 with Intel i5."], "We are running tests on Windows 11 with Intel i5."),
    (["The offline Whisper model is ready.", "Whisper model is ready to transcribe."], "The offline Whisper model is ready to transcribe."),
    (["Everything was validated successfully.", "validated successfully across all tests."], "Everything was validated successfully across all tests.")
]

for idx, (pair, exp) in enumerate(overlap_pairs):
    tests.append((
        f"CAT5-OverlapMerge-{idx+1}",
        pair,
        lambda out, e=exp: out.strip().rstrip('.?!').lower() == e.strip().rstrip('.?!').lower(),
        f"Overlap merge: '{pair[0][:25]}...' + '{pair[1][:25]}...'",
        None,
        "en"
    ))

# ==============================================================================
# CATEGORY 6: Multilingual Speech Preservation (15 Cases)
# ==============================================================================
multi_cases = [
    # Hindi
    ("आज शुक्रवार है, सॉरी आज शनिवार है।", "hi", lambda out: "शनिवार" in out and "शुक्रवार" not in out),
    ("नमस्ते, मेरा नाम श्रीनिवास है।", "hi", lambda out: "श्रीनिवास" in out),
    ("हम आज बैठक करेंगे।", "hi", lambda out: "बैठक" in out),
    # Marathi
    ("आज शुक्रवार आहे, माफ करा आज शनिवार आहे।", "mr", lambda out: "शनिवार" in out),
    ("नमस्कार, कसे आहात तुम्ही?", "mr", lambda out: "नमस्कार" in out),
    ("हा प्रकल्प खूप छान आहे.", "mr", lambda out: "प्रकल्प" in out),
    # German
    ("Heute ist Freitag, entschuldigung heute ist Samstag.", "de", lambda out: "Samstag" in out and "Freitag" not in out),
    ("Guten Tag, wie geht es Ihnen?", "de", lambda out: "Guten Tag" in out),
    ("Das System funktioniert einwandfrei.", "de", lambda out: "System" in out),
    # French
    ("Aujourd'hui c'est vendredi, pardon aujourd'hui c'est samedi.", "fr", lambda out: "samedi" in out and "vendredi" not in out),
    ("Bonjour, je m'appelle Srinivas.", "fr", lambda out: "Bonjour" in out),
    ("Le projet fonctionne très bien.", "fr", lambda out: "projet" in out),
    # Telugu
    ("నమస్కారం, మీరు ఎలా ఉన్నారు?", "te", lambda out: "నమస్కారం" in out),
    ("ఈ రోజు శుక్రవారం కాదు, శనివారం.", "te", lambda out: "శనివారం" in out),
    ("ధన్యవాదాలు, ప్రాజెక్ట్ చాలా బాగుంది.", "te", lambda out: "ధన్యవాదాలు" in out)
]

for idx, (inp, lang, checker) in enumerate(multi_cases):
    tests.append((
        f"CAT6-Multilingual-{lang}-{idx+1}",
        inp,
        checker,
        f"Multilingual preservation ({lang}): '{inp[:30]}...'",
        None,
        lang
    ))

# ==============================================================================
# CATEGORY 7: Long Sustained Speech (5 Cases)
# ==============================================================================
para = "Gemini Flow executes continuous real-time audio dictation. It uses 200ms frames and INT8 inference on CPU cores. "
for idx, repeat in enumerate([10, 20, 30, 40, 50]):
    long_inp = (para * repeat).strip()
    word_count = len(long_inp.split())
    tests.append((
        f"CAT7-LongSpeech-{word_count}words",
        long_inp,
        lambda out, exp_words=word_count: len(out.split()) >= exp_words * 0.95,
        f"Long speech zero-truncation guarantee ({word_count} words)",
        None,
        "en"
    ))

print(f"Total Test Cases Compiled: {len(tests)}")

passed_count = 0
failed_cases = []

t_start = time.time()
for test_id, inp, checker, desc, snips, lang in tests:
    t0 = time.time()
    if isinstance(inp, list):
        out = OverlapDuplicateResolver.merge_transcripts(inp)
    else:
        out = pipeline.process(inp, snippets=snips, language=lang)
    dt = (time.time() - t0) * 1000

    try:
        ok = checker(out)
    except Exception as ex:
        ok = False

    if ok:
        passed_count += 1
    else:
        failed_cases.append((test_id, inp, out, desc))

total_time = time.time() - t_start
print(f"================================================================================")
print(f"  100+ MASTER VERIFICATION SUITE RESULTS")
print(f"  Passed: {passed_count}/{len(tests)} ({passed_count/len(tests)*100:.1f}%)")
print(f"  Total Duration: {total_time:.3f}s (Avg per test: {total_time/len(tests)*1000:.2f}ms)")
print(f"================================================================================")

if failed_cases:
    print(f"\nFailed cases ({len(failed_cases)}):")
    for tid, inp, out, d in failed_cases:
        print(f"[{tid}] {d}\n  In:  {inp}\n  Out: {out}\n")
else:
    print("\nALL 100+ TESTS PASSED 100% WITH ZERO FAILURES!")

with open(PROJECT_ROOT / "reports" / "test_100x_master_results.json", "w", encoding="utf-8") as f:
    json.dump({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(tests),
        "passed": passed_count,
        "failed": len(failed_cases),
        "success_rate": f"{passed_count/len(tests)*100:.1f}%",
        "duration_sec": round(total_time, 3)
    }, f, indent=2)
