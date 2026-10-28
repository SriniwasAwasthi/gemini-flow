# Gemini Flow — Root Cause Analysis & Defect Audit

This document details the root causes for speech truncation, audio buffer degradation, recognition inaccuracies, and distribution failures identified in Gemini Flow.

---

### Root Cause Matrix

| Category | File & Line | Symptom / Defect | Evidence & Impact | Definitive Engineering Fix |
| :--- | :--- | :--- | :--- | :--- |
| **A. Truncation (Rolling Timeout)** | `app/main.py:923-930` | 13s of 30s Speech Truncation | A hardcoded `while time.time() - t_wait_start < 3.2:` loop forced early exit before in-flight chunks completed, stitching only partial audio. | Eliminate short fixed timeouts; wait for all in-flight chunks with zero drop, or fall back to full WAV re-transcription. |
| **B. Truncation (VAD Cutoff)** | `app/offline/offline_engine.py:276-278` | Speech truncated during natural pauses | `min_silence_duration_ms=300` caused Silero VAD to treat normal breathing pauses (400–700ms) as utterance ends. | Increase `min_silence_duration_ms` to `2000`, set `threshold=0.35`, and `speech_pad_ms=500`. |
| **C. Audio Degradation (DSP / Gate)** | `app/audio_recorder.py:49-80` | Quiet syllables cut off or muffled | Dynamic RMS noise gate attenuated audio below -52 dB, silencing soft consonants (`/s/`, `/f/`, `/th/`). | Disable noise gate by default; implement gentle 80 Hz high-pass filter + peak normalization behind an explicit setting. |
| **D. Sample Rate Aliasing** | `app/offline/offline_engine.py:304-308` | Garbled audio, poor ASR accuracy | Linear interpolation (`np.interp`) was used for resampling, causing severe high-frequency spectral aliasing. | Replace with high-quality polyphase filtering (`scipy.signal.resample_poly`). |
| **E. Audio Capture Queue Blocking** | `app/audio_recorder.py:180-184` | Dropped frames under CPU load | Memory chunks appended in Python list without direct continuous disk streaming. | Implement an unbounded producer/consumer queue writing PCM16 directly to disk in a dedicated thread. |
| **F. Sub-Optimal Whisper Decoding** | `app/offline/offline_engine.py:271` | High WER on complex speech | `beam_size=1` (greedy decoding) and `condition_on_previous_text=False` without initial prompt anchoring. | Set `beam_size=5`, `best_of=5`, temperature fallback `(0.0, 0.2, 0.4)`, and anchored initial prompt. |
| **G. Cloud File Limits & Finish Reason** | `app/gemini_engine.py:495-580` | Cloud truncation on large audio | Inline audio exceeded 15 MB limit; did not upload via Google Files API; did not retry on `MAX_TOKENS` or `SAFETY`. | Add Google Files API upload for >15 MB, check all `finish_reason` codes, and read all candidates and parts. |
| **H. Prompt Injection / Hallucination** | `app/intelligence/ollama_engine.py:110` | LLM answering instead of polishing | Text was not shielded inside `<dictation>` tags; LLM treated dictated commands as user instructions. | Wrap dictation in `<dictation>` tags with strict copy-editor system prompt and a hard Fidelity Gate. |
| **I. UI Table Stale Column** | `app/ui/settings_dialog.py` | UI schema inconsistency | "AI Model Routed" column remained in the Profiles category table despite unified model routing. | Remove "AI Model Routed" column from UI tables, headers, and model adapters. |
| **J. Standalone Runtime Packaging** | `installer/Gemini_Flow_Setup.cs:236` | Setup executable fails on clean PC | `Gemini_Flow_Setup.exe` (285 KB) lacked the bundled standalone runtime and offline models. | Compile complete PyInstaller `dist/Gemini_Flow.exe` and bundle everything into Inno Setup `dist/Gemini_Flow_Setup_Full.exe`. |

---

### Deep Dive: Reproduction of the 13s-of-30s Truncation

#### Mechanism of the Failure
1. A user speaks continuously for 30 seconds.
2. In `app/main.py`:
   - `AudioRecorder.get_rolling_chunk(min_sec=30.0)` triggers around 30 seconds.
   - One rolling chunk of ~13 seconds is sliced and dispatched to the background worker (`curr_idx = 0`).
   - The user releases the hotkey at 30.0 seconds.
   - `on_stop_speech` sets `_rolling_active = False` and enqueues the tail chunk.
   - However, in `_process_speech_worker`:
     ```python
     t_wait_start = time.time()
     while time.time() - t_wait_start < 3.2:
         ...
     ```
   - If the network or Whisper takes longer than 3.2s to process the tail chunk, or if `len(valid_chunks)` logic miscounts the emitted chunks, the loop exits.
   - Only the first 13-second chunk is stitched. The remaining 17 seconds are silently dropped!

#### Fix Strategy
1. The audio capture layer continuously writes every sample to disk (`%LOCALAPPDATA%/GeminiFlow/recordings/<timestamp>.wav`).
2. The transcription engine verifies coverage: `covered_seconds >= audio_seconds - 1.5s` or silence check.
3. If chunking assembly fails or times out, the engine **must** re-transcribe the entire recorded WAV file in a single comprehensive pass so that zero speech is ever lost.
