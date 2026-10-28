"""
Generates synthetic and speech test audio for Gemini Flow automated testing.
Uses Windows SAPI to generate clean WAV files at 16 kHz mono with exact natural duration.
"""
import os
import wave
import json
from pathlib import Path
import numpy as np
import win32com.client

AUDIO_DIR = Path(__file__).resolve().parent / "audio_synthetic"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# SAPI speech ~2.2 words per second. Craft exact texts so speech naturally spans the target durations.
TEST_SPEECHES = {
    "clip_5s": (
        "Welcome to Gemini Flow. Fast, accurate speech dictation for Windows.",
        5.0
    ),
    "clip_30s": (
        "Welcome to Gemini Flow. This is an end to end verification test of our speech recognition engine. "
        "We are validating that thirty seconds of spoken English audio is transcribed accurately from the first word "
        "to the last word without any truncation or dropped sentences. Every single word in this paragraph must be "
        "captured with high fidelity, proper punctuation, and complete grammar. Modern voice workflows demand "
        "rock solid stability and zero data loss on Windows desktop.",
        30.0
    ),
    "clip_60s": (
        "This is a one minute benchmark audio recording designed to measure offline Whisper performance and coverage. "
        "We need to ensure that the entire transcript from the beginning of the sentence to the very end of the paragraph "
        "is captured with zero truncation. When building production software on Windows, stability and fidelity are paramount. "
        "Whether dictating emails, writing documentation, or authoring code, every single word matters. "
        "The system processes speech continuously in real time, preserving all critical context. "
        "In addition, our architecture leverages polyphase resampling, unbounded queuing, and silence aligned chunking "
        "to guarantee that long form continuous speech never suffers from buffer overflows or arbitrary timeouts. "
        "As we approach the end of this sixty second test, the audio engine continues capturing every acoustic detail "
        "with pristine clarity and high signal to noise ratio.",
        60.0
    ),
    "clip_120s": (
        "This is an extended two minute stress test for the Gemini Flow dictation architecture. "
        "In modern knowledge work, professionals frequently dictate long form memos, technical architecture reviews, "
        "and comprehensive meeting summaries without pause. A common flaw in legacy speech applications is buffer overrun "
        "or premature timeout truncation, where only the first thirteen seconds of a thirty second speech are captured. "
        "Gemini Flow completely eliminates this failure mode through unbounded streaming queues, high fidelity polyphase resampling, "
        "and silence aligned audio chunking with longest common substring deduplication. "
        "Furthermore, all dictation text is treated strictly as data rather than instructions. "
        "This guarantees that speaking prompts or commands never causes unexpected actions or hallucinations. "
        "Whether running offline on CPU with INT8 quantization or online via the Gemini API, "
        "the final output retains complete fidelity from the very first word to the very last word. "
        "In the second minute of continuous dictation, we observe how memory usage remains constant "
        "and how CPU utilization remains predictable across multiple threads. "
        "The underlying ctranslate2 engine handles acoustic feature extraction and beam search decoding "
        "with optimal numerical stability. Punctuation marks, capitalization, and numbers are correctly restored. "
        "No audio frames are dropped, no tail segments are abandoned, and the final transcript matches the spoken audio. "
        "As this comprehensive two minute benchmark concludes, all background worker threads terminate cleanly "
        "and deliver the verified transcript to the user interface.",
        120.0
    ),
    "clip_numbers_code": (
        "Project update for 2026. The total cost is $1,500 with 18% tax. "
        "We benchmarked the Python API using snake case functions and camel case variables. "
        "The constant pi is approximately 3.14. All tests passed.",
        25.0
    )
}


def synthesize_speech_wav(text: str, target_wav_path: Path):
    """Synthesizes speech to WAV using Windows SAPI (16 kHz mono 16-bit PCM)."""
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    stream = win32com.client.Dispatch("SAPI.SpFileStream")
    
    # 22 is SAFT16kHz16BitMono
    stream.Format.Type = 22
    stream.Open(str(target_wav_path), 3, False)
    voice.AudioOutputStream = stream
    voice.Rate = 0  # Normal rate
    voice.Volume = 100
    voice.Speak(text)
    stream.Close()


def generate_silence_wav(target_wav_path: Path, duration_sec: float = 10.0):
    """Generates pure digital silence WAV."""
    sample_rate = 16000
    num_samples = int(duration_sec * sample_rate)
    silence = np.zeros(num_samples, dtype=np.int16)
    with wave.open(str(target_wav_path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(silence.tobytes())


def generate_noise_wav(target_wav_path: Path, duration_sec: float = 10.0):
    """Generates low-amplitude white noise / fan noise WAV."""
    sample_rate = 16000
    num_samples = int(duration_sec * sample_rate)
    noise = (np.random.normal(0, 0.003, num_samples) * 32767).astype(np.int16)
    with wave.open(str(target_wav_path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(noise.tobytes())


def generate_all_test_audio():
    print("Generating natural test audio dataset in tests/audio_synthetic/...")
    metadata = {}
    for key, (text, target_dur) in TEST_SPEECHES.items():
        wav_path = AUDIO_DIR / f"{key}.wav"
        print(f"Synthesizing {key}...")
        synthesize_speech_wav(text, wav_path)
        with wave.open(str(wav_path), 'rb') as wf:
            actual_dur = wf.getnframes() / float(wf.getframerate())
        metadata[key] = {
            "path": str(wav_path),
            "text": text,
            "duration": actual_dur
        }
        print(f" -> Generated: {wav_path.name} (Duration: {actual_dur:.2f}s)")

    # Silence & Noise
    silence_path = AUDIO_DIR / "silence_10s.wav"
    generate_silence_wav(silence_path, 10.0)
    metadata["silence_10s"] = {"path": str(silence_path), "text": "", "duration": 10.0}

    noise_path = AUDIO_DIR / "noise_10s.wav"
    generate_noise_wav(noise_path, 10.0)
    metadata["noise_10s"] = {"path": str(noise_path), "text": "", "duration": 10.0}

    meta_path = AUDIO_DIR / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print("Natural test audio generation complete!")


if __name__ == "__main__":
    generate_all_test_audio()
