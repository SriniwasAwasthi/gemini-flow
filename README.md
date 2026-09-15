<div align="center">

# ⚡ Gemini Flow (Wispr Flow AI Alternative)

**Supercharge your typing with lightning-fast, context-aware AI voice dictation and prompt engineering powered by Google Gemini.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-Qt6-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://pypi.org/project/PyQt6/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Flash%203.5%20%2F%203.6-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![Windows](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<br />

[Features](#-key-features) • [Application Showcase](#-application-showcase--ui-tour) • [Architecture](#-system-architecture) • [Setup Guide](#-step-by-step-implementation--setup-guide) • [How to Use](#-how-to-use) • [Shortcuts](#-keyboard-shortcuts-reference) • [Verification Tests](#-verification--test-suite) • [License](#-license)

</div>

---

## 📖 Overview

**Gemini Flow** is an open-source, high-performance, and privacy-conscious AI voice dictation desktop assistant for Windows. Designed as a free, customizable alternative to *Wispr Flow*, Gemini Flow connects directly to **Google Gemini 3.5 & 3.6 Flash** models via your personal Google AI Studio API key.

Speak naturally in any Windows software—VS Code, Microsoft Word, Slack, WhatsApp, Telegram, or your favorite web browser—and Gemini Flow will filter background noise, remove verbal hesitation and stuttering, polish Indian English/Hinglish idioms, format structured markdown lists, and type the refined text directly at your cursor location.

---

## ✨ Key Features

- 🎙️ **Universal Auto-Typing**: Hold or toggle a global hotkey anywhere in Windows to speak; text types out smoothly into whatever field or editor has focus.
- ⚡ **3-Style AI Dictation Engine**:
  - **Clean Speech & Grammar Enhancement**: Flawless punctuation, clean paragraphs, removes verbal fillers (`uh`, `um`, `ah`, `basically`, `means`, `matlab`, `yaani`), and stutters (`12 12 12` $\rightarrow$ `12`, `12th 12th` $\rightarrow$ `12th`).
  - **Smart Executive Polish**: Converts stream-of-consciousness thoughts into structured executive-grade prose with clean bullet points (`• `) and paragraph breaks.
  - **Developer Code & Technical Assistant**: Transcribes programming terminology, variable names in `camelCase`/`snake_case`, syntax, and terminal commands cleanly.
- 🇮🇳 **Hinglish & Indian Idiom Polish**: Preserves everyday cultural expressions (`bhai`, `jugaad`, `lakhs/crores`, `prepone`) while eliminating broken grammar or translation glitches.
- 🎧 **DSP Audio Filter & Ceiling Fan Gate**:
  - Real-time 85 Hz Butterworth High-Pass Filter cuts motor drone and fan rumble.
  - Adaptive RMS Noise Gate suppresses ambient background noise when silent.
- 📶 **Offline Emergency Fallback**: Seamlessly switches to local Windows Speech Recognition (SAPI) whenever internet connection drops or API rate limits are reached.
- 🎨 **Sleek Glassmorphic Floating HUD**: Minimal, non-intrusive floating overlay with dynamic pulse audio waveforms, status badges, and subtle glow animations.
- 🎛️ **Intelligent Cost Economizer & Token Tracking**: Per-API key token tracker, daily 1,000,000 free token monitor, cost productivity calculator, and automatic cost-saving model selector.
- 📚 **Custom Vocabulary & Sound-Alikes**: Define technical terms, acronyms, and phonetic substitutions to ensure 100% transcription accuracy for custom terminology.
- 📜 **Expanded Searchable History**: Stores up to 5,000 previous dictations with quick search, app filtering, and instant one-click clipboard copy.

---

## 🖼️ Application Showcase & UI Tour

Explore the core modules and visual interface of Gemini Flow:

### 1. Minimalist Glassmorphic Floating HUD
![Glassmorphic Floating HUD](images/00_floating_hud.png)
> **Real-Time Dynamic Audio Waveform**: Displays pulsating sound wave bars in real-time as you speak and provides subtle visual status updates during AI processing.  
> **Non-Intrusive Floating Overlay**: Stays floating above your active workspace without stealing keyboard focus, fading away smoothly once dictation completes.

---

### 2. API Configuration & General Preferences
![API & General Settings](images/01_api_general.png)
> **Secure API Key Management**: Easily configure your free personal Google Gemini API key with built-in connection validation and latency diagnostics.  
> **Customizable Application Defaults**: Control system tray startup, audio sound cues, auto-launch behavior, and visual themes to match your workflow.

---

### 3. Interactive Global Hotkey Recorder
![Hotkeys & Triggers Config](images/02_hotkeys_mode.png)
> **Custom Shortcut Hooks**: Record custom key combinations for Push-to-Talk and Hands-Free Toggle modes with an interactive key listener.  
> **Flexible Triggers**: Full support for single keys, multi-modifier combinations (`Ctrl+Shift+Space`, `Win+Alt`), function keys, and mouse triggers.

---

### 4. Cost Productivity & Token Economizer
![Cost Productivity & Token Economizer](images/03_cost_productivity.png)
> **Real-Time Token Usage Tracking**: Accurately monitors your daily token usage against the 1,000,000 free tokens/day Google Gemini quota.  
> **Smart Economizer & Productivity Metrics**: Computes estimated monetary savings and automatically selects optimal models to maximize efficiency.

---

### 5. Contextual Vocabulary & Jargon Engine
![Vocabulary Engine](images/04_vocabulary_engine.png)
> **Technical Terminology Guarantee**: Define programming libraries, company names, and technical terms to ensure 100% transcription accuracy.  
> **Domain-Aware Prompt Injection**: Automatically supplements Gemini's context window with relevant terminology based on active applications.

---

### 6. Custom Phonetic Dictionary & Sound-Alikes
![Custom Dictionary](images/05_custom_dictionary.png)
> **Phonetic Sound-Alike Mapping**: Map commonly misheard words, proper nouns, and regional names to their exact intended spellings.  
> **Accent Robustness**: Eliminates acoustic ambiguities across diverse regional accents and pronunciation styles.

---

### 7. Quick Text Snippets & Auto-Expansion
![Quick Text & Voice Snippets](images/06_quick_text.png)
> **Voice-Activated Macro Expansions**: Trigger multi-line templates, email signatures, and boilerplate code using simple spoken shortcut keywords.  
> **Productivity Booster**: Accelerates repetitive typing tasks across client communications, code snippets, and daily reporting.

---

### 8. Searchable Dictation History & Export
![Dictation History & Search](images/07_history.png)
> **Comprehensive Activity Log**: Search, review, and filter all previous dictations by date, active application, or AI model used.  
> **Instant Clipboard Copy**: One-click quick-copy chips let you retrieve earlier notes and snippets effortlessly.

---

### 9. Context-Aware Application Profiles
![Application Profiles](images/08_profiles.png)
> **Adaptive Behavior per App**: Automatically adjusts dictation style, tone, and vocabulary based on the foreground application.  
> **Tailored Presets**: Switches dynamically between clean code formatting in IDEs, formal prose in Word, and casual tone in chat apps.

---

### 10. Multi-Mode AI Dictation & Prompt Library
![AI Dictation & Polish Modes](images/09_ai_dictation.png)
> **Versatile Transformation Modes**: Seamlessly switch between *Clean Speech*, *Smart Executive Polish*, and *Developer Code*.  
> **Instant Activation & Custom Vocab Input**: Quickly edit or switch prompts with real-time preset syncing and direct vocabulary definition.

---

### 11. Intelligent AI Model Router & Orchestrator
![AI Model Router](images/10_ai_model_router.png)
> **Dynamic Load Balancing**: Automatically routes speech requests between Gemini 3.5 Flash, 3.6 Flash, and Flash-Lite for lowest latency.  
> **Model Synchronization**: Bidirectionally synchronizes active models between General Settings and the Router orchestrator.

---

### 12. Audio Device & Ceiling Fan DSP Filter
![Audio Device & Ceiling Fan DSP Filter](images/11_audio_device.png)
> **Acoustic Noise Reduction**: Features a real-time 85 Hz Butterworth high-pass filter that eliminates ceiling fan drone and motor hum.  
> **Adaptive RMS Noise Gate**: Suppresses ambient room chatter and background noise when you pause or finish speaking.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    A[🎤 Microphone Audio Capture] --> B[🎧 Audio DSP Pipeline]
    B -->|85Hz Butterworth High-Pass| C[🔇 RMS Noise Gate]
    C --> D[📦 PyAudio Stream Recorder]
    
    D --> E{🌐 Internet Connected?}
    E -- Yes --> F[🚀 Google Gemini API Engine]
    E -- No / Timeout --> G[💻 Windows SAPI Offline Engine]
    
    F --> H[🧠 Smart Model Router]
    H -->|Gemini 3.5 / 3.6 Flash| I[📝 Context & Prompt Formatter]
    I -->|Hinglish Polish & Custom Vocab| J[✨ Clean & Polished Text]
    
    G --> J
    
    J --> K[⌨️ Universal Auto-Typer / Clipboard Injection]
    K --> L[🖥️ Target Active Windows Application]
    
    subgraph UI & Controls
        M[🪟 Glassmorphic Floating HUD]
        N[⚙️ Settings Control Center - 11 Modules]
        O[⌨️ Global Keyboard Hooks]
    end
    
    O --> D
    D -.-> M
    J -.-> M
    N -.-> H
```


---

## 🚀 Step-by-Step Implementation & Setup Guide

Follow these simple steps to set up and run Gemini Flow on your Windows machine:

### Step 1: Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python**: Version `3.10`, `3.11`, or `3.12` installed and added to your `PATH`
- **Microphone**: Any built-in or external USB microphone

---

### Step 2: Obtain Your Free Google Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click **Get API key** → **Create API key in new project**.
4. Copy your API key (starts with `AIzaSy...` or `AQ...`).  
   *(Google provides 1,000,000 free tokens per day for Gemini Flash models!)*

---

### Step 3: Clone the Repository
Open PowerShell or Command Prompt:

```bash
git clone https://github.com/SriniwasAwasthi/gemini-flow.git
cd gemini-flow
```

---

### Step 4: Create a Virtual Environment (Recommended)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

---

### Step 5: Install Required Dependencies

```powershell
pip install -r requirements.txt
```

---

### Step 6: Launch Gemini Flow

You can start the application using either method:

#### Option A: Quick-Launch Script (Easiest)
Double-click `run.bat` or run in terminal:
```cmd
run.bat
```

#### Option B: Standard Python Command
```powershell
python main.py
```

*Tip: For silent background operation without a console window, use `pythonw main.py`.*

---

## 💡 How to Use

1. **Initial Setup**:
   - When Gemini Flow launches, open **Settings** by right-clicking the system tray icon or clicking the HUD gear icon.
   - In **API & General**, enter your Gemini API Key and click **Test Connection**.
   - In **Audio Device**, select your microphone and verify the live volume bar.
2. **Standard Voice Dictation (Ctrl + Space)**:
   - Place your cursor in any application (VS Code, Word, Chrome, WhatsApp, etc.).
   - Press **`Ctrl + Space`** (or your custom hotkey).
   - In **Toggle Mode**: Tap once to start speaking, tap again to finish and auto-type.
   - In **Push-to-Talk Mode**: Hold keys down while speaking, release to finish and auto-type.
3. **AI Prompt Engineering Mode (Ctrl + Shift + P)**:
   - Press **`Ctrl + Shift + P`** to dictate instructions. Gemini Flow will convert your spoken thoughts into a structured LLM meta-prompt (Role, Objective, Steps, Output) and type it into your active AI window.
4. **In-Place Text Transformation (Ctrl + Shift + T)**:
   - Highlight any existing text in any application and press **`Ctrl + Shift + T`** to open the Quick Transform bar or polish selected text directly in place.
5. **Emergency Offline Fallback**:
   - If your internet disconnects, Gemini Flow automatically switches to Windows SAPI speech recognition so your typing workflow never stops.

---

## ⌨️ Keyboard Shortcuts Reference

| Shortcut | Action | Description |
|---|---|---|
| `Ctrl + Space` | **Voice Dictation** | Primary trigger for voice typing. Supports both Hands-Free Toggle and Push-to-Talk (configurable in Settings). |
| `Ctrl + Shift + P` | **AI Prompt Mode** | Dictate ideas and generate structured meta-prompts for ChatGPT, Claude, or Gemini. |
| `Ctrl + Shift + T` | **Text Transformer** | Highlight text in any application and transform/polish it in-place using Gemini AI. |
| `Esc` | **Cancel Recording** | Instantly aborts the active recording, discards audio, and hides the HUD. |


---

## 🧪 Verification & Test Suite

Gemini Flow comes with an exhaustive test suite to ensure system stability, grammar transformation accuracy, and background lifecycle resilience:

```powershell
# Run Component Level Unit Tests
python tests/test_components.py

# Run Full UI & 11-Tab Settings Audit
python tests/test_full_suite.py

# Run Multi-Model Grammar Polish & Query Verification Suite
python tests/test_grammar_and_queries.py

# Run Process Lifecycle & Multi-Cycle Stress Test
python tests/test_stress_lifecycle.py
```

---

## 🔒 Privacy & API Key Security

- **Strictly Local Storage**: Your Google Gemini API Key is stored securely on your local PC in `%APPDATA%\GeminiFlow\config.json`.
- **Zero Third-Party Servers**: Audio streams are sent exclusively to Google's official AI Studio API endpoints directly from your computer.
- **No Telemetry / Data Sharing**: Your transcribed text, voice snippets, and history are kept entirely on your local machine.

---

## 📂 Project Structure

```text
gemini-flow/
├── app/
│   ├── audio_recorder.py       # PyAudio stream, 85Hz high-pass filter & RMS noise gate
│   ├── config.py               # Settings manager & local JSON persistence
│   ├── cost_awareness.py       # Token economizer, quota tracking & savings estimator
│   ├── gemini_engine.py        # Google Gemini API client, latency tracker & regex cleaners
│   ├── hotkey_manager.py       # Global Windows keyboard & mouse hooks with debounce
│   ├── main.py                 # Core application controller & system tray integration
│   ├── text_injector.py        # Simulated keystroke & clipboard injection engine
│   ├── intelligence/           # Context-aware application detection
│   ├── intent/                 # Spoken intent classification engine
│   ├── offline/
│   │   └── offline_engine.py   # Windows SAPI offline speech fallback module
│   ├── profiles/               # Per-application customization profiles
│   ├── reliability/            # Fallback handlers and connection retry policies
│   ├── router/
│   │   └── model_router.py     # Intelligent AI model router & dynamic load balancer
│   ├── security/
│   │   └── security_manager.py # Windows DPAPI secret encryption module
│   ├── transformation/
│   │   └── transform_engine.py # In-place text transformation engine
│   ├── vocabulary/
│   │   └── vocab_engine.py     # Custom jargon & phonetic vocabulary engine
│   ├── resources/              # UI checkmarks, radio buttons, and SVG assets
│   └── ui/
│       ├── floating_hud.py     # Glassmorphic Qt floating overlay window
│       └── settings_dialog.py  # 11-module Settings Control Center
├── images/                     # Refreshed UI screenshots and visual documentation assets
├── tests/                      # Exhaustive test & verification suites
├── requirements.txt            # Python package dependencies
├── run.bat                     # Windows one-click launcher script
├── main.py                     # Root application entry point
├── LICENSE                     # MIT License
└── README.md                   # Comprehensive documentation
```

---

## 🛠️ Built With

- **[PyQt6](https://pypi.org/project/PyQt6/)** - Modern desktop graphical user interface
- **[Google Generative AI SDK](https://github.com/google-gemini/generative-ai-python)** - Ultra-fast Gemini 3.5 & 3.6 Flash models
- **[PyAudio & SciPy](https://pypi.org/project/PyAudio/)** - Low-latency audio streaming & Butterworth DSP noise filtering
- **[Pynput & PyWin32](https://pypi.org/project/pynput/)** - Global Windows hotkey hooks and simulated keystroke typing
- **[Windows SAPI](https://docs.microsoft.com/en-us/previous-versions/windows/desktop/ee125663(v=vs.85))** - Local offline speech recognition fallback


---

## 📄 License

This project is licensed under the **MIT License** - see the [`LICENSE`](LICENSE) file for details.

---

## 💖 Thank You for Exploring Gemini Flow!

Thank you for visiting and exploring the **Gemini Flow** repository! If you find this project helpful for your daily productivity and voice workflows, please consider giving it a ⭐ **Star** on GitHub.

Feel free to open an [Issue](https://github.com/SriniwasAwasthi/gemini-flow/issues) or submit a [Pull Request](https://github.com/SriniwasAwasthi/gemini-flow/pulls) if you have suggestions, feature ideas, or improvements!

<div align="center">
  <sub>Crafted with passion by <b>Sriniwas Awasthi</b> • Powered by Google Gemini AI</sub>
</div>
