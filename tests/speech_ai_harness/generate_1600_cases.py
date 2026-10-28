"""
Generates the 1,600 Test Cases for Voice Commands (100 runs per category across 16 categories).
Covers:
- Diverse topics: Engineering, Business, Daily Life, Science, Healthcare, Finance, Travel, Legal
- Both modes: Spoken-at-start (85%) and Highlighted-text-plus-hotkey (15%)
- Spoken names: Trina Savastrian, Srinivas, Sarah Chen, Alex Rivera, Dr. Patel, Marcus Vance
- Numbers, currencies, dates ($5,000, Friday, 3 PM, 18% tax, 2.5GB)
- Mandatory Real Failure Example as Case #1 of PROFESSIONALIZE
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.intent.intent_system import IntentCategory

OUTPUT_FILE = Path("tests/speech_ai_harness/voice_commands_1600_cases.json")

# 16 Categories and their typical trigger prefixes
CATEGORY_CONFIGS = {
    IntentCategory.PROFESSIONALIZE: {
        "triggers": ["Make this professional.", "Make this professional:", "Make it more professional:", "Professionalize this:", "Executive tone:"],
        "highlighted_triggers": ["Make this professional.", "Professionalize.", "Make it formal."],
        "key_entities": ["Trina Savastrian", "Srinivas", "Alex Rivera", "Dr. Patel", "Marcus Vance"],
    },
    IntentCategory.MAKE_CASUAL: {
        "triggers": ["Make this casual:", "Make this casual.", "Casual tone:", "Friendly tone:", "Make it conversational:"],
        "highlighted_triggers": ["Make this casual.", "Casual tone.", "Tone down."],
        "key_entities": ["Sarah Chen", "Srinivas", "David", "Jessica"],
    },
    IntentCategory.CREATE_PROMPT: {
        "triggers": ["Turn this into a prompt:", "Create AI prompt:", "Generate prompt:", "Turn into prompt.", "Prompt engineering:"],
        "highlighted_triggers": ["Turn this into a prompt.", "Create prompt.", "AI prompt."],
        "key_entities": ["FastAPI", "React", "OAuth2", "Gemini", "PyTorch"],
    },
    IntentCategory.SUMMARIZE: {
        "triggers": ["Summarize this:", "Summarize this.", "TLDR:", "Give me a summary:", "Executive summary:"],
        "highlighted_triggers": ["Summarize this.", "TLDR.", "Give me a summary."],
        "key_entities": ["Srinivas", "Friday", "five grand", "Quarter 3", "AWS"],
    },
    IntentCategory.GRAMMAR_FIX: {
        "triggers": ["Fix grammar:", "Fix my grammar.", "Correct grammar:", "Fix spelling:", "Proofread this:"],
        "highlighted_triggers": ["Fix grammar.", "Proofread.", "Correct grammar."],
        "key_entities": ["Trina Savastrian", "yesterday", "three apples", "Sydney"],
    },
    IntentCategory.SHORTEN: {
        "triggers": ["Make this shorter:", "Make this shorter.", "Shorten this:", "Cut the fluff:", "Be concise:"],
        "highlighted_triggers": ["Make this shorter.", "Shorten.", "Be concise."],
        "key_entities": ["Srinivas", "Project Apollo", "30 days", "ten thousand dollars"],
    },
    IntentCategory.EXPAND: {
        "triggers": ["Expand this:", "Expand this.", "Elaborate on this:", "Give more detail:", "Flesh this out:"],
        "highlighted_triggers": ["Expand this.", "Elaborate.", "Give more detail."],
        "key_entities": ["edge computing", "vector embeddings", "Sarah Chen", "latency reduction"],
    },
    IntentCategory.EXPLAIN: {
        "triggers": ["Explain this:", "Explain this.", "Break this down:", "Explain simply:", "ELI5:"],
        "highlighted_triggers": ["Explain this.", "Explain simply.", "Break this down."],
        "key_entities": ["Transformer architecture", "zero knowledge proofs", "SIP protocol", "database sharding"],
    },
    IntentCategory.TRANSLATE: {
        "triggers": ["Translate this to French:", "Translate this to Spanish:", "Translate this to German:", "Translate this to Japanese:", "Translate to Hindi:"],
        "highlighted_triggers": ["Translate to French.", "Translate to Spanish.", "Translate to German."],
        "key_entities": ["Paris", "Madrid", "Berlin", "Tokyo", "Delhi"],
    },
    IntentCategory.CREATE_EMAIL: {
        "triggers": ["Draft an email about:", "Write an email to:", "Compose email:", "Draft email:", "Email draft:"],
        "highlighted_triggers": ["Draft an email.", "Compose email.", "Draft email."],
        "key_entities": ["Srinivas", "Sarah Chen", "Client Demo", "Friday launch", "Board meeting"],
    },
    IntentCategory.CREATE_GITHUB_ISSUE: {
        "triggers": ["Create a GitHub issue:", "File an issue for:", "Bug report issue:", "New issue:", "GitHub issue:"],
        "highlighted_triggers": ["Create GitHub issue.", "File issue.", "Bug report."],
        "key_entities": ["Memory leak", "AudioRecorder", "NullPointerException", "v1.4.0", "Windows 11"],
    },
    IntentCategory.CREATE_GITHUB_PR: {
        "triggers": ["Create a pull request:", "Create a PR:", "Draft PR description:", "PR summary:", "Pull request:"],
        "highlighted_triggers": ["Create a pull request.", "Draft PR.", "PR description."],
        "key_entities": ["Voice intent routing", "ModelRouter", "tests/speech_ai_harness", "feature/audio-fix"],
    },
    IntentCategory.CREATE_TASK: {
        "triggers": ["Create task list:", "Make a to-do list:", "Action items:", "Generate checklist:", "Create tasks:"],
        "highlighted_triggers": ["Create task list.", "Action items.", "Make a to-do list."],
        "key_entities": ["Srinivas", "Trina Savastrian", "Friday", "budget review", "deploy cluster"],
    },
    IntentCategory.GENERATE_CODE: {
        "triggers": ["Generate code in Python:", "Write a python script to:", "Write a function in TypeScript that:", "Generate SQL query to:", "Write code to:"],
        "highlighted_triggers": ["Generate code in Python.", "Write Python code.", "Generate code."],
        "key_entities": ["binary search", "JWT authentication", "reverse linked list", "aggregate sales by month"],
    },
    IntentCategory.FORMAT_TEXT: {
        "triggers": ["Format this into a table:", "Create a markdown table:", "Format as a table:", "Convert to table:", "Table format:"],
        "highlighted_triggers": ["Format into a table.", "Convert to table.", "Markdown table."],
        "key_entities": ["Name, Role, Location, Salary", "Model, Latency, Accuracy, Status", "Product, Price, Stock, Rating"],
    },
    IntentCategory.REWRITE: {
        "triggers": ["Rewrite this:", "Polish this:", "Improve this text:", "Rephrase this:", "Rewrite and polish:"],
        "highlighted_triggers": ["Rewrite this.", "Polish this.", "Rephrase."],
        "key_entities": ["Trina Savastrian", "Srinivas", "strategic initiative", "customer engagement"],
    }
}

# Base templates covering varied domains and grammar styles
BASE_TOPICS = [
    ("engineering", "We gotta push the release to next Tuesday because the Redis cache synchronization test failed under load."),
    ("business", "Hey team we gotta delay the launch to friday cause database test failed also Srinivas will prepare the slides and keep budget under five grand."),
    ("grocery", "I was visiting the market and I buy two apples one mango three bananas and bread then I come back home."),
    ("medical", "Patient reported severe headaches and mild dizziness since last Thursday after taking twenty milligrams of lisinopril."),
    ("finance", "The quarterly revenue grew by fifteen percent reaching four point two million dollars with EBITDA margins above thirty percent."),
    ("travel", "Flight departs at seven forty five AM from terminal two with layover in Frankfurt before arriving in London."),
    ("legal", "The contractor agrees to deliver all source code and documentation by November fifteenth under mutual non disclosure terms."),
    ("daily_personal", "Hello I am Srinivas and I went to the downtown coffee shop with my colleague to discuss the upcoming marathon."),
    ("education", "Photosynthesis is the biological process by which green plants use sunlight to synthesize nutrients from carbon dioxide and water."),
    ("devops", "Docker container crashed with out of memory error code 137 during the automated database migration script."),
    ("customer_support", "Customer ticket number 4920 reports that payment was deducted twice via Stripe gateway for the annual subscription."),
    ("hr_recruiting", "Candidate Marcus Vance completed the technical coding interview and demonstrated strong proficiency in distributed systems."),
    ("marketing", "Our social media campaign generated over twenty thousand clicks and reduced customer acquisition cost by twelve percent."),
    ("real_estate", "The commercial property on Fifth Avenue offers twelve thousand square feet with five dedicated parking bays."),
    ("science_ai", "Fine tuning language models with low rank adaptation significantly cuts memory footprint while maintaining downstream benchmark accuracy."),
    ("event_planning", "The annual tech conference will host forty keynote speakers and expect three thousand attendees in San Francisco."),
    ("logistics", "Shipment containing sixty microcontrollers was delayed at customs and will arrive at warehouse by Wednesday noon."),
    ("mobile_app", "Flutter application stuttered during high speed scrolling on older Android devices due to unnecessary widget rebuilds."),
    ("security", "Penetration test revealed cross site scripting vulnerability in user profile bio input field."),
    ("collaboration", "Sarah Chen will coordinate the weekly sync and update Jira tickets before end of business today.")
]

def build_1600_cases():
    cases = []
    case_id = 1

    for cat, conf in CATEGORY_CONFIGS.items():
        cat_cases = []
        triggers = conf["triggers"]
        highlighted_triggers = conf["highlighted_triggers"]
        entities = conf["key_entities"]

        for i in range(100):
            # Case 1 for PROFESSIONALIZE: Mandatory User Real Failure Example
            if cat == IntentCategory.PROFESSIONALIZE and i == 0:
                raw_input = "Make this professional. I'm Trina Savastrian, I was just visiting the market and I was doing some random stuff I buy: Two apples. One mango three bananas. I come back home."
                cat_cases.append({
                    "id": case_id,
                    "category": cat.value,
                    "mode": "spoken_at_start",
                    "input_text": raw_input,
                    "expected_trigger": "Make this professional.",
                    "expected_name": "Trina Savastrian",
                    "is_mandatory_regression": True,
                    "expected_checks": ["Trina Savastrian", "apples", "mango", "bananas", "•"]
                })
                case_id += 1
                continue

            # 15% highlighted-text-plus-hotkey mode
            is_highlighted = (i >= 85)
            topic_idx = i % len(BASE_TOPICS)
            domain, base_payload = BASE_TOPICS[topic_idx]

            # Injected entity if applicable
            entity = entities[i % len(entities)]
            if "{entity}" not in base_payload and (i % 3 == 0):
                base_payload = f"{base_payload} Note that {entity} is leading this effort."

            if is_highlighted:
                # User selected text on screen, speaks only trigger
                trig = highlighted_triggers[i % len(highlighted_triggers)]
                cat_cases.append({
                    "id": case_id,
                    "category": cat.value,
                    "mode": "highlighted_plus_hotkey",
                    "spoken_command": trig,
                    "highlighted_text": base_payload,
                    "input_text": trig,
                    "expected_trigger": trig,
                    "expected_name": entity if (i % 3 == 0) else None,
                    "is_mandatory_regression": False,
                    "expected_checks": [entity] if (i % 3 == 0) else []
                })
            else:
                # Spoken at start mode
                trig = triggers[i % len(triggers)]
                delim = " " if trig.endswith((".", ":")) else ": "
                raw_input = f"{trig}{delim}{base_payload}"
                cat_cases.append({
                    "id": case_id,
                    "category": cat.value,
                    "mode": "spoken_at_start",
                    "input_text": raw_input,
                    "expected_trigger": trig,
                    "expected_name": entity if (i % 3 == 0) else None,
                    "is_mandatory_regression": False,
                    "expected_checks": [entity] if (i % 3 == 0) else []
                })

            case_id += 1

        cases.extend(cat_cases)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)

    print(f"Generated {len(cases)} test cases across {len(CATEGORY_CONFIGS)} categories (100 runs each).")
    print(f"Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_1600_cases()
