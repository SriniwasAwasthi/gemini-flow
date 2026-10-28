# Changelog

All notable changes to the **Gemini Flow** project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-10-28

### 🚀 Major Breakthrough: Zero-Truncation & Clean-PC Architecture
This milestone transforms Gemini Flow into an enterprise-grade Windows speech dictation engine with guaranteed zero truncation, 100% offline neural models, full voice command intents, and clean-PC packaging.

### Added
- **Zero-Truncation Audio Capture**:
  - Hardware-native sample-rate recording via `sounddevice` with high-quality polyphase resampling (`scipy.signal.resample_poly`) to 16 kHz mono float32.
  - Producer-consumer lock-free queue with continuous background disk streaming (`%LOCALAPPDATA%\GeminiFlow\recordings\<timestamp>.wav`).
  - Strict 30-minute recording safety cap with audible and visual alerts (no silent cuts).
- **Silence-Aligned Audio Chunking**:
  - Intelligent splitting of long audio (>25s) at acoustic silence boundaries with 1.5s overlap deduplication.
  - VAD energy gating to skip background noise and silence frames.
- **Copy-Editor Fidelity Gate**:
  - Mathematical edit validation ($\le 15\%$ length difference, $\le 25\%$ word edit distance) preventing LLM hallucinations, answering, or conversational commentary.
  - `<dictation>` text isolation tags treating speech strictly as data, never instructions.
- **Unified 16 Voice Commands Registry**:
  - Native regex matching for all 16 command categories triggered strictly by leading phrase (e.g. "Professional email:", "Summarize this:", "Bullet points:").
  - Deprecated legacy "AI Model Routed" column completely removed from UI and configuration.
  - Synthetic test benchmark validating 1,600 spoken variations across all 16 categories.
- **Clean-PC Packaging & Zero-Dependency Installers**:
  - Native C# host launcher (`Gemini_Flow.exe`) compiled via Microsoft .NET `csc.exe` with auto-path resolution for isolated Python 3.10 runtime.
  - Full Windows Installation Wizard (`Gemini_Flow_Setup_Full.exe`) creating Desktop/Start Menu shortcuts and clean Windows uninstaller (`uninstall.cmd`).
  - Self-contained distribution archive (`Gemini_Flow_Setup_Full.zip`) bundling embedded Python 3.10, PyPI dependencies, and pre-trained Whisper weights (`models/small.en`, `models/base.en`, `models/tiny.en`).
- **Hardware Mic Card & Fan Filter**:
  - Live visual VU level meter and device dropdown with dynamic hardware detection.
  - Gentle 80 Hz high-pass filter + peak normalization (OFF by default for optimal WER).
- **Developer & User Setup Scripts**:
  - `scripts/setup_windows.ps1` for automated 1-click environment bootstrap.
  - `scripts/download_models.py` with resume support and integrity verification.
  - `scripts/build.ps1` for clean-room C# compilation and packaging.
  - `run.bat` and `run.ps1` with virtual environment detection.

### Changed
- Replaced aggressive DSP bandpass filters with gentle high-pass filtering (tested: 4.00% raw WER vs 6.67% filtered WER).
- Updated SettingsDialog with glassmorphic dark theme, executive brand header, and hardware mic monitoring card.
- Updated all README documentation and screenshots in `docs/screenshots/` to match latest v2.0 UI.

### Fixed
- Fixed audio truncation where 30s recordings were truncated to 13s due to fixed-size buffers.
- Fixed hotkey bouncing and rapid toggle lockups with thread-safe timestamp debouncing.
- Fixed Faster-Whisper generator truncation where only first segment was consumed.
- Fixed Ollama Gemma integration to act purely as text polish after speech-to-text.

---

## [1.2.0] - 2026-10-20

### Added
- Local AI Brain support via Ollama (`gemma:2b`) for 100% offline text cleanup.
- Cost and productivity analytics dashboard tracking WPM and saved typing time.
- Custom vocabulary engine with phonetic and sound-alike matching.
- Spoken-to-written custom dictionary and voice snippet expansions.

---

## [1.0.0] - 2026-09-12

### Initial Release
- Global Windows dictation trigger (`Ctrl+Space`).
- Cloud Gemini 2.5 Flash and Gemini 2.5 Pro transcription integration.
- Faster-Whisper offline transcription engine.
- Floating glassmorphic HUD overlay and system tray integration.
