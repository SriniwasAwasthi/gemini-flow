import asyncio
import edge_tts
from pathlib import Path

AUDIO_DIR = Path("videos/temp_3min_build")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

VOICE = "en-US-ChristopherNeural"
RATE = "+10%"

SCRIPTS = {
    "scene_05_vocab.mp3": (
        "Next is the Personal AI Vocabulary Engine. It primes Gemini with your company terminology, "
        "project codenames, and phonetic aliases. Notice the Live Normalization Sandbox below: as spoken "
        "variations are typed, the engine instantaneously normalizes them into their canonical forms in real time."
    ),
    "scene_06_dictionary.mp3": (
        "For deterministic phonetics, the Custom Dictionary maps misheard spoken phrases to exact target spellings. "
        "Here, colloquial phrases like 'pie dantic' and 'fast api' are mapped directly to 'Pydantic' and 'FastAPI', "
        "guaranteeing zero spelling errors on specialized technical jargon."
    ),
    "scene_07_quicktext.mp3": (
        "For multi-line productivity, Quick Text acts as your voice macro engine. By speaking a short trigger phrase "
        "such as 'my developer bio' or 'insert bug report template', Gemini Flow instantly expands and pastes "
        "complete multi-line templates and URLs across any active window."
    ),
}

async def main():
    for filename, text in SCRIPTS.items():
        out_path = AUDIO_DIR / filename
        communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
        await communicate.save(str(out_path))
        print(f"Synthesized: {out_path} ({len(text)} chars)")

if __name__ == "__main__":
    asyncio.run(main())
