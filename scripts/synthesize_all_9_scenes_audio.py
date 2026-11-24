import asyncio
import edge_tts
from pathlib import Path

AUDIO_DIR = Path("videos/temp_3min_build")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

VOICE = "en-US-ChristopherNeural"
RATE = "+10%"

SCRIPTS = {
    "scene_01_intro.mp3": (
        "Welcome to Gemini Flow, the high-performance local and cloud voice dictation pipeline. "
        "Today, three autonomous AI agents are demonstrating the core architecture, security controls, "
        "and production features in real time."
    ),
    "scene_02_api.mp3": (
        "First is the API General settings. Notice how Agent 2 enters the API credentials under an active "
        "privacy Gaussian blur, securely verifying the latency directly against Google Gemini 2.5 Flash without exposing plaintext keys. "
        "All credentials and logs remain strictly on your local machine."
    ),
    "scene_03_dsp.mp3": (
        "In the Audio Device section, we have integrated a studio-grade 80Hz high-pass Butterworth filter and energy-floor noise gate. "
        "Agent 2 enables the new Whisper Mode, injecting a calibrated plus 12-dB boost so quiet, near-field whispering is captured with zero distortion."
    ),
    "scene_04_hotkeys.mp3": (
        "Under Hotkeys Mode, you can choose between Push-to-Talk and Hands-Free Toggle. Push-to-Talk is protected by a 35-millisecond kernel hardware watchdog. "
        "An 8-second emergency watchdog automatically resets the pipeline if silence stalls, and Shift Alt Z instantly recovers your last transcription."
    ),
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
    "scene_08_history.mp3": (
        "In History and AI settings, deprecated models are completely filtered out, keeping only production-ready "
        "Gemini 2.5 Flash and Pro tiers. Gemini Flow's anti-hallucination engine automatically strips YouTube-style subtitle artifacts "
        "before pasting."
    ),
    "scene_09_outro.mp3": (
        "With a flawless 28 out of 28 unit test pass rate and total zero-leak local privacy, Gemini Flow delivers enterprise-grade "
        "voice intelligence. The repository is 100% open-source and ready for production deployment."
    ),
}

async def main():
    for filename, text in SCRIPTS.items():
        out_path = AUDIO_DIR / filename
        communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
        await communicate.save(str(out_path))
        print(f"Synthesized {filename}: {out_path} ({len(text)} chars)")

if __name__ == "__main__":
    asyncio.run(main())
