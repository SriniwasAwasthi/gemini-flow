# Gemini Flow — Engineering Assumptions & Design Contracts

This document records the foundational assumptions, operating parameters, and design contracts adopted for the Gemini Flow Windows dictation system across all phases of implementation.

---

### 1. Target Operating Environment
* **Operating Systems**: 64-bit Microsoft Windows 10 (Build 19041+) and Windows 11.
* **Clean PC Target**: The target machine has no pre-installed Python, no Visual Studio build tools, no Git, no active internet connection for offline models, and no pre-existing environment variables.
* **User Permissions**: Standard user and Administrator permissions both supported. Default installation targets `%LOCALAPPDATA%\Programs\GeminiFlow` (per-user zero-UAC installation) or `%ProgramFiles%\GeminiFlow` when run with administrative elevation.

---

### 2. Audio Pipeline & Resampling
* **Device Capture**: Input microphones on Windows report native sampling rates (typically 44,100 Hz, 48,000 Hz, or 96,000 Hz) and multi-channel configurations (stereo or mono). Capture occurs at the hardware's native rate to avoid PortAudio driver distortion.
* **Resampling Standard**: Downsampling to 16,000 Hz 1-channel (mono) float32 uses polyphase filtering (`scipy.signal.resample_poly`), avoiding linear interpolation artifacts.
* **Zero Frame Drops**: The sounddevice audio callback only enqueues raw byte arrays into a thread-safe producer/consumer queue. All disk writing (`%LOCALAPPDATA%\GeminiFlow\recordings\<timestamp>.wav`) occurs in a dedicated background worker thread with unbounded queue capacity to ensure zero frame drops under heavy CPU load.
* **Duration Enforcement**: Recording continues indefinitely until the user presses `Ctrl+Space` (toggle) or the UI Stop button. A hard safety limit of 30 minutes is enforced with an on-screen warning toast, preventing runaway disk consumption while never truncating normal dictation.

---

### 3. Model Architecture & Responsibilities
Gemini Flow supports four distinct model pipelines with strict boundaries:
1. **Gemini 2.5 Flash (`gemini-2.5-flash`)**: Cloud flagship speech dictation. Audio is sent inline (<=15 MB) or via Google Files API (>15 MB) with chunking for sessions >5 minutes. Zero hallucination contract prompt.
2. **Gemini 2.5 Pro (`gemini-2.5-pro`)**: High-reasoning dictation for deep architectural specs, legal prose, and research.
3. **Faster-Whisper int8 (`offline-whisper`)**: 100% on-device speech-to-text powered by `faster-whisper` (CTranslate2) utilizing local bundled model weights (`small.en`, `base.en`, `tiny.en`).
4. **Ollama Gemma (`ollama-gemma2`)**: **Two-stage offline pipeline**:
   * *Stage 1 (ASR)*: 100% on-device speech-to-text via `faster-whisper`.
   * *Stage 2 (Text Clean-up)*: Text post-processing via local Gemma 2B running on Ollama (`http://localhost:11434`).
   * *Clarification*: Gemma is strictly an LLM (text-to-text); raw audio bytes are **never** passed directly to Ollama/Gemma.

---

### 4. Post-Processing & Fidelity Gate
* **Data Isolation**: Spoken dictation is treated as literal data, never as prompt instructions. Inputs are shielded inside `<dictation>...</dictation>` boundaries.
* **Deterministic Baseline**: A deterministic rule-based cleaner always runs first (whitespace, capitalization, contraction repair, spoken punctuation expansion).
* **Fidelity Gate Rules**:
  * Length change between polished and raw text must not exceed ±15%.
  * Content word replacement must not exceed 25%.
  * Named entities, currency amounts, dates, and numbers must remain intact.
