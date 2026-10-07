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
   - First type mock invalid key in visible plain text (`AIzaSyD987_invalid_mock_key_demo_test_999`) -> click Test Save (red glow) -> red failure message.
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
