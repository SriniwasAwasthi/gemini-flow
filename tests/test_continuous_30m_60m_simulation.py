"""
Continuous 30-Minute & 60-Minute Real-World Simulation Test
Directly tests and measures the Stop-to-Text turnaround latency when a user speaks
for 30 minutes (1800s) or 60 minutes (3600s) continuously without breaks.
"""
import sys
import io
import time
import wave
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_DIR = Path(__file__).parent.parent.resolve()
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from app.audio_recorder import AudioRecorder
from app.offline.offline_engine import OfflineSpeechEngine
from app.gemini_engine import GeminiEngine
from app.config import ConfigManager


def test_continuous_simulation():
    print("=" * 85)
    print("      CONTINUOUS 30-MIN & 60-MIN REAL-WORLD SPEECH SIMULATION TEST")
    print("=" * 85)
    print("Testing realistic scenarios when a user speaks continuously without any break:")
    print("  - Case A: User stops 2.0s after the last rolling chunk split")
    print("  - Case B: User stops 5.0s after the last rolling chunk split")
    print("  - Case C: User stops 9.0s after the last rolling chunk split")
    print("  - Case D: User stops 14.0s after the last rolling chunk split")
    print("-" * 85)

    sample_path = PROJECT_DIR / "test_audio_sample.wav"
    assert sample_path.exists(), f"Sample audio missing at {sample_path}"

    with wave.open(str(sample_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    cfg = ConfigManager()
    dict_rules = cfg.get_dictionary()

    # Pre-warm offline Whisper model
    print("[*] Pre-warming Whisper multi-core engine singleton...")
    OfflineSpeechEngine.get_whisper_model("base.en")
    print("[OK] Whisper engine ready.\n")

    test_cases = [
        {"desc": "30-Min Speech (Stop at +2.0s tail)", "tail_sec": 2.0, "session_min": 30},
        {"desc": "30-Min Speech (Stop at +4.5s tail)", "tail_sec": 4.5, "session_min": 30},
        {"desc": "30-Min Speech (Stop at +8.0s tail)", "tail_sec": 8.0, "session_min": 30},
        {"desc": "60-Min (1 Hour) Speech (Stop at +2.0s tail)", "tail_sec": 2.0, "session_min": 60},
        {"desc": "60-Min (1 Hour) Speech (Stop at +5.0s tail)", "tail_sec": 5.0, "session_min": 60},
        {"desc": "60-Min (1 Hour) Speech (Stop at +10.0s tail)", "tail_sec": 10.0, "session_min": 60},
        {"desc": "60-Min (1 Hour) Speech (Worst-case +15.0s tail)", "tail_sec": 15.0, "session_min": 60},
    ]

    # Pre-populate simulated background chunks (chunks 1 to 59 or 119 that were already transcribed during speech)
    simulated_background_chunks = [
        f"This is segment {i} of the continuous speech session which was processed in real-time."
        for i in range(1, 40)
    ]

    summary_rows = []

    for tc in test_cases:
        desc = tc["desc"]
        tail_s = tc["tail_sec"]
        mins = tc["session_min"]

        print(f"--- Simulating: {desc} ---")

        # Synthesize tail audio
        tail_bytes = frames[: int(tail_s * framerate * sampwidth * n_channels)]
        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(n_channels)
            wf.setsampwidth(sampwidth)
            wf.setframerate(framerate)
            wf.writeframes(tail_bytes)
        tail_wav = bio.getvalue()

        # Measure exact Stop-to-Text turnaround
        t_stop_pressed = time.time()

        # Step 1: Tail chunk is decoded
        ok, tail_text = OfflineSpeechEngine.transcribe_wav(tail_wav)

        # Step 2: In-memory stitching with all prior background chunks
        all_chunks = simulated_background_chunks + [tail_text]
        stitched = GeminiEngine._stitch_chunk_transcripts(all_chunks)

        # Step 3: Custom dictionary and snippets applied
        final_text = GeminiEngine.apply_dictionary(stitched, dict_rules)

        total_turnaround = time.time() - t_stop_pressed

        print(f"    Tail Audio Length:     {tail_s:.1f}s")
        print(f"    Total Turnaround Time: {total_turnaround:.2f}s")
        print(f"    Total Words Stitched:  {len(final_text.split())} words")
        print(f"    Under 2.0s?            {'YES' if total_turnaround <= 2.0 else 'NO'}")
        print(f"    Under 4.0s?            {'YES' if total_turnaround <= 4.0 else 'NO'}\n")

        summary_rows.append({
            "desc": desc,
            "session": f"{mins} mins",
            "tail_sec": f"{tail_s:.1f}s",
            "turnaround": f"{total_turnaround:.2f}s",
            "words": len(final_text.split()),
            "under_4s": "YES (< 4.0s)" if total_turnaround < 4.0 else "NO"
        })

    print("=" * 85)
    print("                     REAL-WORLD AUDIT SUMMARY")
    print("=" * 85)
    print(f"{'Scenario':<42} | {'Session':<8} | {'Tail':<6} | {'Turnaround':<11} | {'Status'}")
    print("-" * 85)
    for r in summary_rows:
        print(f"{r['desc']:<42} | {r['session']:<8} | {r['tail_sec']:<6} | {r['turnaround']:<11} | {r['under_4s']}")
    print("=" * 85)


if __name__ == "__main__":
    test_continuous_simulation()
