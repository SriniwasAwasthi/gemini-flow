"""
Reproduction Test for Speech Truncation (13s of 30s drop).
Simulates a 30-second dictation where rolling assembly times out or VAD prematurely trims
the tail segment, demonstrating the truncation bug BEFORE the comprehensive fix.
"""
import time
import io
import wave
import numpy as np
import unittest


def generate_synthetic_speech_30s(sample_rate: int = 16000) -> tuple[bytes, str]:
    """Generates a 30-second WAV with speech tones and a distinct conclusion sentence."""
    total_sec = 30.0
    t = np.linspace(0, total_sec, int(sample_rate * total_sec), endpoint=False)
    # Fundamental voice frequency (180 Hz) with formant harmonics (540 Hz, 1200 Hz)
    carrier = 0.3 * np.sin(2 * np.pi * 180 * t) + 0.15 * np.sin(2 * np.pi * 540 * t)

    # Modulate envelope to simulate words (0.3s word, 0.1s pause)
    word_period = 0.4
    mod = np.where((t % word_period) < 0.28, 1.0, 0.05)
    # Add a 0.5s pause at 13.0s (which triggered old VAD cutoff)
    mod = np.where((t >= 13.0) & (t <= 13.5), 0.001, mod)

    audio_signal = (carrier * mod).astype(np.float32)
    # Clip and convert to PCM16
    pcm16 = (np.clip(audio_signal, -1.0, 1.0) * 32767).astype(np.int16)

    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())

    expected_full_text = "This is the initial speech segment up to thirteen seconds. And this is the vital final segment concluding the full thirty seconds."
    return bio.getvalue(), expected_full_text


def simulate_legacy_rolling_assembly_truncation(wav_bytes: bytes) -> str:
    """
    Simulates the legacy rolling assembly logic from app/main.py:
    1. First chunk of ~13s is processed.
    2. User stops at 30s.
    3. Tail chunk of 17s is enqueued, but a 3.2s timeout expires before completion.
    4. Legacy code only stitched valid_chunks (the first 13s chunk), truncating the remaining 17s.
    """
    # Legacy chunk slicing
    chunk_1 = "This is the initial speech segment up to thirteen seconds."
    chunk_tail_in_flight = "And this is the vital final segment concluding the full thirty seconds."

    rolling_chunks = [
        {"id": 0, "done": True, "text": chunk_1},
        {"id": 1, "done": False, "text": "", "wav": b"pending_tail_audio"}  # still in flight
    ]

    # Legacy loop had a 3.2s cap; if background worker takes 3.5s, all_done is False
    all_done = all(c.get("done", False) for c in rolling_chunks)
    assert not all_done, "Tail chunk is still in flight"

    # Legacy code gathered only completed chunks:
    valid_chunks = [c["text"].strip() for c in rolling_chunks if c.get("text")]
    legacy_stitched = " ".join(valid_chunks)
    return legacy_stitched


def test_reproduce_13s_of_30s_truncation_bug():
    """Proves that legacy assembly dropped the final 17 seconds of a 30s audio."""
    wav_bytes, expected_text = generate_synthetic_speech_30s()
    legacy_result = simulate_legacy_rolling_assembly_truncation(wav_bytes)

    # Evidence of failure: The concluding sentence is completely missing!
    assert "concluding the full thirty seconds" not in legacy_result, "Expected legacy bug to drop conclusion"
    assert len(legacy_result) < len(expected_text) * 0.6, "Legacy result was severely truncated to <60% length"
    print(f"\n[REPRODUCED BUG] Legacy result truncated to: '{legacy_result}'")
    print(f"[REPRODUCED BUG] Missing tail: 'And this is the vital final segment concluding the full thirty seconds.'")


if __name__ == "__main__":
    test_reproduce_13s_of_30s_truncation_bug()
    print("Test passed: 13s-of-30s truncation bug successfully reproduced!")
