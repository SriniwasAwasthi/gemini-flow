"""
Acoustic Audio Chunker and Suffix-Prefix Transcript Merger.
Provides silence-aligned audio chunking (max 25s, 1.5s overlap) and
overlap deduplication via longest common word-suffix/prefix matching.
"""
import io
import re
import wave
import logging
from typing import List, Tuple, Optional
import numpy as np

logger = logging.getLogger("GeminiFlow.Chunker")


def get_audio_info(wav_bytes: bytes) -> Tuple[float, int, int, int]:
    """Returns (duration_seconds, samplerate, channels, nframes)."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        fr = wf.getframerate()
        nc = wf.getnchannels()
        nf = wf.getnframes()
        dur = nf / float(fr) if fr > 0 else 0.0
        return dur, fr, nc, nf


def split_at_silence_boundaries(
    wav_bytes: bytes,
    max_chunk_sec: float = 25.0,
    min_chunk_sec: float = 12.0,
    overlap_sec: float = 1.5
) -> List[Tuple[float, float, bytes]]:
    """
    Splits audio longer than 25s into chunks of at most 25s with 1.5s overlap at natural silence pauses.
    Returns list of (start_sec, end_sec, chunk_wav_bytes).
    """
    if not wav_bytes or len(wav_bytes) < 1000:
        return [(0.0, 0.0, wav_bytes)] if wav_bytes else []

    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        fr = wf.getframerate()
        nc = wf.getnchannels()
        sw = wf.getsampwidth()
        nf = wf.getnframes()
        pcm = wf.readframes(nf)

    total_sec = nf / float(fr) if fr > 0 else 0.0
    if total_sec <= max_chunk_sec or total_sec <= 0.0:
        return [(0.0, total_sec, wav_bytes)]

    dtype = np.int16 if sw == 2 else np.int8
    samples = np.frombuffer(pcm, dtype=dtype)
    if nc > 1:
        samples = samples.reshape(-1, nc)[:, 0]

    chunks = []
    current_frame = 0
    total_frames = nf

    block_size = int(0.05 * fr)  # 50ms energy block

    while current_frame < total_frames:
        remaining_frames = total_frames - current_frame
        remaining_sec = remaining_frames / float(fr)

        if remaining_sec <= max_chunk_sec:
            start_sec = current_frame / float(fr)
            end_sec = total_frames / float(fr)
            chunk_pcm = pcm[current_frame * nc * sw :]
            out_io = io.BytesIO()
            with wave.open(out_io, "wb") as out_wf:
                out_wf.setnchannels(nc)
                out_wf.setsampwidth(sw)
                out_wf.setframerate(fr)
                out_wf.writeframes(chunk_pcm)
            chunks.append((start_sec, end_sec, out_io.getvalue()))
            break

        # Search window for silence pause: [min_chunk_sec, max_chunk_sec]
        search_start_f = current_frame + int(min_chunk_sec * fr)
        search_end_f = current_frame + int(max_chunk_sec * fr)
        search_samples = samples[search_start_f:search_end_f]

        split_frame = search_end_f
        if len(search_samples) > block_size * 2:
            num_blocks = len(search_samples) // block_size
            blocks = search_samples[: num_blocks * block_size].reshape(num_blocks, block_size)
            rms = np.sqrt(np.mean(blocks.astype(np.float32) ** 2, axis=1) + 1e-9)
            best_block = int(np.argmin(rms))
            split_frame = search_start_f + best_block * block_size + (block_size // 2)

        start_sec = current_frame / float(fr)
        end_sec = split_frame / float(fr)

        chunk_pcm = pcm[current_frame * nc * sw : split_frame * nc * sw]
        out_io = io.BytesIO()
        with wave.open(out_io, "wb") as out_wf:
            out_wf.setnchannels(nc)
            out_wf.setsampwidth(sw)
            out_wf.setframerate(fr)
            out_wf.writeframes(chunk_pcm)
        chunks.append((start_sec, end_sec, out_io.getvalue()))

        # Advance with overlap: next start = split_frame - overlap_sec
        overlap_frames = int(overlap_sec * fr)
        current_frame = max(current_frame + int(min_chunk_sec * fr), split_frame - overlap_frames)

    return chunks


def merge_overlapping_transcripts(transcripts: List[str]) -> str:
    """
    Merges a list of transcripts from overlapping chunks by computing
    the longest common word-suffix/prefix match and removing duplicated overlap words.
    """
    if not transcripts:
        return ""
    if len(transcripts) == 1:
        return transcripts[0].strip()

    merged = transcripts[0].strip()

    for next_raw in transcripts[1:]:
        next_chunk = next_raw.strip()
        if not next_chunk:
            continue
        if not merged:
            merged = next_chunk
            continue

        prev_words = merged.split()
        next_words = next_chunk.split()

        # Search for longest common suffix of prev_words matching prefix of next_words
        max_overlap_words = min(12, len(prev_words), len(next_words))
        best_match_k = 0

        for k in range(max_overlap_words, 0, -1):
            p_slice = [re.sub(r'[^\w]', '', w).lower() for w in prev_words[-k:]]
            n_slice = [re.sub(r'[^\w]', '', w).lower() for w in next_words[:k]]
            if p_slice == n_slice and all(len(w) > 0 for w in p_slice):
                best_match_k = k
                break

        if best_match_k > 0:
            remaining_next = " ".join(next_words[best_match_k:])
            if remaining_next:
                if merged.endswith((".", "!", "?", ",", ";", ":")):
                    merged = merged + " " + remaining_next
                else:
                    merged = merged + " " + remaining_next
        else:
            # No word overlap match; append with appropriate spacing
            if merged.endswith(("\n", "\n\n")):
                merged = merged + next_chunk
            elif merged.endswith((".", "!", "?", ",", ";", ":")):
                merged = merged + " " + next_chunk
            else:
                merged = merged + " " + next_chunk

    return merged.strip()


def detect_hallucination_loop(text: str) -> bool:
    """
    Detects hallucination loops (repeated n-grams, typical YouTube subtitle ghosts, or empty loops).
    """
    if not text:
        return False

    lower = text.lower().strip()
    ghost_phrases = [
        "thank you for watching",
        "thanks for watching",
        "subtitles by",
        "please subscribe",
        "like and subscribe",
        "amara.org",
        "translated by"
    ]
    if any(gp in lower for gp in ghost_phrases) and len(text.split()) < 15:
        return True

    words = lower.split()
    if len(words) >= 6:
        # Check for 3-gram repetition 3 or more times
        triplets = [" ".join(words[i:i+3]) for i in range(len(words)-2)]
        for t in triplets:
            if triplets.count(t) >= 3:
                return True

    return False
