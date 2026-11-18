# Gemini Flow Workspace Standards & LinkedIn Walkthrough Video Memory

## 🎬 LinkedIn Walkthrough Video Production Standards
Whenever requested to create, script, or automate a walkthrough video or LinkedIn post for any web application or project:

1. **Resolution & Aspect Ratio**:
   - `1920x1080` (1080p Full HD), 16:9 widescreen, 30 FPS.
   - Deliver both `.mp4` (H.264/AAC) and `.webm` (VP8/Opus) multiplexed files to both root `./` and `videos/`.

2. **Zero Floating Mouse**:
   - Never render floating or simulated mouse pointers anywhere across the video.

3. **Authentic, Crisp UI**:
   - Never blur history or data screens.
   - Never obscure more than 15-20% of the screen with overlay boxes.

4. **Live Credential Typing Simulation**:
   - First type mock invalid key in visible plain text (`AIzaSy_MOCK_INVALID_KEY_DEMO_TEST_999`) -> click Test Save (red glow) -> red failure message.
   - Clear field -> type real key securely masked with bullet dots (`••••••••••••••••••••`) -> click Test Save (green glow) -> green verified active message.
   - Never expose real credentials in plain text.

5. **Clean Typography**:
   - Use clean ASCII arrows (`->`) and badge pills to avoid missing unicode font glyph boxes (`[]`).

6. **Dedicated Hero Workspace Poster Outro**:
   - In Step 0, remind the user to provide their high-resolution workspace poster or marketing graphic (`[Project Name] AI Workspace Poster.png`).
   - Starting from the final ~20 seconds (e.g. 03:17+), display this high-resolution poster full-screen with top-right pulsing Full HD badge and GitHub CTA.

7. **Voiceover Synchronization & Transitions**:
   - Frame-synchronized TTS narration via `chapters_meta.json`.
   - Tight 1.0s - 1.2s transitions between chapters (zero awkward long pauses).

8. **Deliverables Package**:
   - Direct file paths for both MP4 and WebM in root and `videos/`.
   - Second-by-second chapter timeline table.
   - Ready-to-post LinkedIn showcase caption (< 2,900 characters) with hook, numbered features, and hashtags.

---

## 🏛️ System Architectural Directives & Resilient Routing Blueprint

### 1. Universal Fallback & Fast-Fail Routing
- **Cloud Models (Gemini, Groq)**: Enforce connect timeout = 2.0s, read timeout = 6.0s (maximum 10.0s for long audio).
- **Instant Fast-Fail**: If cloud returns HTTP 400, 401, or 403 (invalid key / authentication failure), immediately fast-fail to Offline Whisper AI without retrying secondary cloud models with the same invalid credentials.
- **Local Fallback**: If Moonshine ONNX or Sherpa-ONNX model weights are missing or packages fail to load, immediately rescue via Offline Whisper AI.
- **Ollama**: If the local Ollama daemon is offline or Stage 2 polish fails, fall back cleanly to the Universal Pipeline.

### 2. Model-Adaptive Audio Chunking & Thread Serialization
- Audio chunk boundaries must adapt to model scale:
  - `tiny.en`:  min_sec=2.0s, max_sec=3.2s, interval=0.30s, join_timeout=1.5s
  - `base.en`:  min_sec=3.0s, max_sec=4.5s, interval=0.45s, join_timeout=2.5s
  - `small.en`: min_sec=3.8s, max_sec=5.8s, interval=0.65s, join_timeout=4.5s
- Single-worker serialization (`threading.Semaphore(1)`) ensures chunks never compete for CPU cores simultaneously.
- Relax Silero VAD for short sub-chunks (< 3.5s: `vad_filter=False`) to prevent clipping boundary syllables.

### 3. Push-to-Talk & Hotkey Recording Guard
- In Push-to-Talk mode, maintain a 35ms kernel hardware watchdog (`ctypes.windll.user32.GetAsyncKeyState`) to detect physical key release instantly, independent of low-level hook drops.
- When recording hotkeys in the UI, map control characters (`ord < 32`) back to their true characters (`chr(ord(c) + 64)`) and verify virtual key codes (`k.vk`) so combinations like `Ctrl + Alt + T` and `Ctrl + Shift + I` are saved without corruption.
- Intercept all default Windows system keys (`Win + 1..9`, `Win + I`, `Win + Ctrl + Shift + B`, `Alt + F4`, `Win + D`, `Win + L`, `Win + E`, `Win + Tab`, `Alt + Tab`), display `⚠️ default windows key: <KEY> (Reserved Windows Key)`, and prevent assignment to safeguard OS shortcuts.

### 4. Linguistic Accuracy Across All 12 Tenses & Punctuation
- Remove conversational hesitations (`uh`, `um`, `ah`, `er`) while strictly preserving authentic spoken verbs and nouns. Never substitute words with arbitrary synonyms.
- Correct grammar and subject-verb agreements across all 12 tenses (past, present, future).
- Apply proper capitalization, commas at pauses, periods at terminal clauses, and question marks on interrogatives.
- Only trigger self-correction replacements on explicit compound cues (`no, wait`, `or actually`, `sorry, wait`, `I mean`, `correction`). Never treat single words like `no` or `actually` as deletion triggers in continuous sentences.

### 5. GitHub Reference Benchmarks & Open-Source Speech Patterns
- **SYSTRAN/faster-whisper** (https://github.com/SYSTRAN/faster-whisper):
  - Whisper native 30-second context windowing without artificial 2.5s external slicing.
  - Optimal INT8 CPU parameters: `beam_size=1` for streaming chunks, `beam_size=3` for single/final dictations, `condition_on_previous_text=False` to prevent hallucination cascades, `temperature=0.0`.
- **snakers4/silero-vad** (https://github.com/snakers4/silero-vad):
  - Distant speech thresholding: `threshold=0.18`, `min_silence_duration_ms=600`, `speech_pad_ms=350` to prevent chopping sentence ends at 50 cm.
- **m-bain/whisperX** (https://github.com/m-bain/whisperX):
  - VAD-guided natural pause splitting (only split on pauses > 600ms), never fixed-interval hard cuts.
- **xiph/rnnoise** (https://github.com/xiph/rnnoise):
  - Energy-floor noise gating: Never amplify audio below speech SNR; cap normalization gain (max 2.5x) to prevent amplifying laptop fan hiss.
- **chidiwilliams/buzz** (https://github.com/chidiwilliams/buzz):
  - Non-blocking sequential audio chunk consumption with strict thread-safe buffer draining.

