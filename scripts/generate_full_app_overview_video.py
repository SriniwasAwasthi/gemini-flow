"""
Gemini Flow - Master Structured Application Video Overview & AI Voice Walkthrough (Clean UI)
Full 1080p Full HD (1920x1080, 30fps) authentic screen walkthrough video with Christopher Neural TTS narration.
All obstructive top/bottom banners and overlay boxes removed for 100% clean UI.
"""
import os
import sys
import asyncio
import subprocess
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Set up paths
PROJECT_ROOT = Path(r"E:\W c One Drive\Wisper")
SCREENSHOTS_DIR = PROJECT_ROOT / "docs" / "screenshots"
POSTER_PATH = PROJECT_ROOT / "Gemini Flow AI Productivity Infographic.png"
if not POSTER_PATH.exists():
    POSTER_PATH = PROJECT_ROOT / "Gemini Flow AI Workspace Poster.png"
TEMP_DIR = PROJECT_ROOT / "videos" / "temp_full_overview_build"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

OUT_MP4_PATH = PROJECT_ROOT / "videos" / "Gemini_Flow_Overview_Walkthrough_1080p.mp4"
ROOT_MP4_COPY = PROJECT_ROOT / "Gemini_Flow_Overview_Walkthrough_1080p.mp4"
OUT_WEBM_PATH = PROJECT_ROOT / "videos" / "Gemini_Flow_Overview_Walkthrough_1080p.webm"
ROOT_WEBM_COPY = PROJECT_ROOT / "Gemini_Flow_Overview_Walkthrough_1080p.webm"

# 15 Master Scene Definitions
SCENES = [
    {
        "id": "scene_00_intro",
        "title": "GEMINI FLOW • ENTERPRISE DESKTOP VOICE AI",
        "image": str(POSTER_PATH),
        "script": (
            "Welcome to the comprehensive overview of Gemini Flow, an open-source, ultra-low latency voice dictation and prompt engineering workspace for Windows 11. "
            "Engineered with PyQt6, Google Gemini, Groq, and offline neural engines, Gemini Flow eliminates audio truncation, accelerates typing velocity by over three times, "
            "and transforms natural speech into production-ready prompts."
        )
    },
    {
        "id": "scene_01_api_general",
        "title": "SECTION 01 • API GENERAL & SECURITY",
        "image": str(SCREENSHOTS_DIR / "01-main-dashboard.png"),
        "script": (
            "Section 1: API General. Gemini Flow securely protects API credentials using Windows Data Protection API encryption, keeping keys safely encrypted on disk with zero plain-text exposure. "
            "It features live network latency probes across Gemini Flash and Groq models, with automatic fast-fail routing to local Whisper if credentials or network connectivity ever drop."
        )
    },
    {
        "id": "scene_02_audio_device",
        "title": "SECTION 02 • AUDIO DEVICE & HARDWARE DSP",
        "image": str(SCREENSHOTS_DIR / "02-audio-device.png"),
        "script": (
            "Section 2: Audio Device. This section provides hardware microphone selection with real-time VU level monitoring. "
            "The audio pipeline incorporates WASAPI rate negotiation, stateful polyphase decimation with filter-state carryover, an eighty-five Hertz high-pass rumble filter, "
            "and dynamic peak normalization to ensure crystal-clear capture even from fifty to one hundred centimeters away."
        )
    },
    {
        "id": "scene_03_hotkeys",
        "title": "SECTION 03 • HOTKEYS & TRIGGER MODES",
        "image": str(SCREENSHOTS_DIR / "03-hotkeys-mode.png"),
        "script": (
            "Section 3: Hotkeys Mode. Users can choose between hands-free toggle dictation or push-to-talk. "
            "In push-to-talk mode, a thirty-five millisecond kernel hardware watchdog monitors physical key release to guarantee zero dropped stops. "
            "All Windows system shortcuts are actively protected, and dedicated hotkeys trigger instant text transformation and meta-prompt creation."
        )
    },
    {
        "id": "scene_04_zero_truncation",
        "title": "CORE ENGINE • ZERO-TRUNCATION CAPTURE",
        "image": str(SCREENSHOTS_DIR / "00-floating-hud.png"),
        "script": (
            "The core recording architecture features a lock-free queue with continuous background disk streaming and an audible thirty-minute safety cap. "
            "Long audio is segmented at natural acoustic silence boundaries with one-and-a-half second overlap deduplication, "
            "ensuring zero syllable clipping, zero sentence truncation, and seamless phrase continuity."
        )
    },
    {
        "id": "scene_05_multi_model",
        "title": "INTELLIGENCE • MULTI-MODEL ROUTING",
        "image": str(SCREENSHOTS_DIR / "01-main-dashboard.png"),
        "script": (
            "Gemini Flow delivers a unified transcription contract across cloud and edge. "
            "Cloud requests route through Google Gemini and Groq's Whisper Large V3 Turbo for lightning-fast cloud inference. "
            "When offline, the engine seamlessly engages local Moonshine ONNX for sub-hundred millisecond edge dictation or quantized Faster-Whisper INT8 models."
        )
    },
    {
        "id": "scene_06_cost_productivity",
        "title": "SECTION 04 • COST & PRODUCTIVITY",
        "image": str(SCREENSHOTS_DIR / "04-cost-productivity.png"),
        "script": (
            "Section 4: Cost and Productivity. Real-time telemetry tracks exact token consumption, demonstrating remarkable economy at a fraction of a cent per request. "
            "The dashboard visualizes words per minute velocity, estimated hours saved compared to manual typing, and twenty-nine gamified milestones celebrating your dictation achievements."
        )
    },
    {
        "id": "scene_07_vocabulary",
        "title": "SECTION 05 • VOCABULARY ENGINE",
        "image": str(SCREENSHOTS_DIR / "05-vocabulary-engine.png"),
        "script": (
            "Section 5: Vocabulary Engine. To prevent specialized developer terms and names from being misrecognized, the vocabulary engine primes the speech decoder "
            "with custom technical jargon, camelCase variables, and phonetic sound-alikes, guaranteeing that domain terminology like Kubernetes, PyTorch, and GraphQL are transcribed accurately."
        )
    },
    {
        "id": "scene_08_custom_dictionary",
        "title": "SECTION 06 • CUSTOM DICTIONARY",
        "image": str(SCREENSHOTS_DIR / "06-custom-dictionary.png"),
        "script": (
            "Section 6: Custom Dictionary. This module executes exact regex word-boundary substitutions post-recognition. "
            "It standardizes spoken acronyms and converts colloquial phonetic phrases into exact corporate spellings and proper nouns without affecting unrelated substrings."
        )
    },
    {
        "id": "scene_09_quick_text",
        "title": "SECTION 07 • QUICK TEXT (VOICE SNIPPETS)",
        "image": str(SCREENSHOTS_DIR / "07-quick-text.png"),
        "script": (
            "Section 7: Quick Text. Users can configure voice macros where speaking a quick keyword instantly expands into full multi-line boilerplates, "
            "standard email responses, code snippets, or contact details, injected directly into your active window with zero keystroke delay."
        )
    },
    {
        "id": "scene_10_history",
        "title": "SECTION 08 • HISTORY & FIDELITY GATE",
        "image": str(SCREENSHOTS_DIR / "08-history.png"),
        "script": (
            "Section 8: History and Safeguard Audit. Every transcription is indexed in a searchable dual-view history tab comparing raw speech against AI-enhanced text. "
            "Crucially, a mathematical copy-editor fidelity gate enforces that edited transcripts never deviate by more than fifteen percent in length, completely preventing LLM hallucination."
        )
    },
    {
        "id": "scene_11_profiles_commands",
        "title": "SECTION 09 • PROFILES & CONTEXT DETECTION",
        "image": str(SCREENSHOTS_DIR / "09-profiles-commands.png"),
        "script": (
            "Section 9: Profiles and Application Context. Gemini Flow automatically detects your foreground application—whether VS Code, Slack, or Outlook—and dynamically adapts formatting rules. "
            "It features sixteen decoupled voice command categories with strict mid-sentence protection, so conversational speech is never falsely executed as a command."
        )
    },
    {
        "id": "scene_12_prompt_engineering",
        "title": "SECTION 10 • AI DICTATION & TRANSFORMATION",
        "image": str(SCREENSHOTS_DIR / "10-ai-dictation.png"),
        "script": (
            "Section 10: AI Dictation and Transformation. Pressing Alt+T elevates raw spoken thoughts into fluent, grammatically pristine English across all twelve tenses while stripping verbal fillers. "
            "Pressing Alt+P generates the five-part XML master prompt blueprint, structuring complex engineering thoughts into role, context, task, constraints, and output format without truncation."
        )
    },
    {
        "id": "scene_13_e2e_verification",
        "title": "QUALITY ASSURANCE • 208/208 PASS RATE",
        "image": "GENERATE_TEST_CARD",
        "script": (
            "To ensure bulletproof reliability, Gemini Flow includes a comprehensive four-tier automated end-to-end test suite. "
            "All twenty-four core features—from stateful WASAPI decimation and Groq routing to single-instance mutex safeguards and clipboard integrity—achieve a perfect two hundred and eight out of two hundred and eight pass rate with zero errors."
        )
    },
    {
        "id": "scene_14_outro",
        "title": "GEMINI FLOW • PRODUCTION READY & OPEN SOURCE",
        "image": str(POSTER_PATH),
        "script": (
            "Gemini Flow is packaged with a native C-sharp launcher, full Windows installer wizard, and a clean-PC portable archive bundling embedded runtimes. "
            "Built by Sriniwas Awasthi, it is one hundred percent open source and production ready. Star the repository on GitHub and supercharge your desktop voice workflow today!"
        )
    }
]

async def generate_speech(text: str, out_path: Path):
    import edge_tts
    communicator = edge_tts.Communicate(text, "en-US-ChristopherNeural", rate="+3%")
    await communicator.save(str(out_path))

def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())

def create_e2e_test_card(out_img_path: Path):
    """Renders a clean full 1920x1080 dark luxury card summarizing the 208/208 test suite."""
    W, H = 1920, 1080
    card = Image.new("RGB", (W, H), color=(11, 15, 25))
    draw = ImageDraw.Draw(card)

    font_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 36)
    font_sub = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 22)
    font_tier_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 24)
    font_tier_stat = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 40)
    font_row = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 19)

    # Header section
    draw.text((60, 40), "Automated E2E Verification Suite", font=font_title, fill=(248, 250, 252))
    draw.text((60, 90), "Master Test Runner: tests/e2e/run_all_e2e.py  •  Status: 100% Pass Rate  •  Duration: 6.92s", font=font_sub, fill=(148, 163, 184))

    # Overall Status Pill
    draw.rounded_rectangle([W - 440, 40, W - 60, 100], radius=12, fill=(16, 185, 129))
    draw.text((W - 405, 55), "✓ 208 / 208 TESTS PASSED", font=font_tier_title, fill=(255, 255, 255))

    # 4 Tier KPI Cards (y: 135 to 285)
    tiers = [
        ("Tier 1: Feature Coverage", "120 / 120", "F1 to F24 Features (>=5 tests/feat)", (59, 130, 246)),
        ("Tier 2: Boundary & Corner", "57 / 57", "Extreme buffer & latency edges", (168, 85, 247)),
        ("Tier 3: Pairwise Combinations", "24 / 24", "Mic x Model x Chunk x Workers", (236, 72, 153)),
        ("Tier 4: Real-World Scenarios", "7 / 7", "End-to-End Workflow Workloads", (16, 185, 129)),
    ]
    card_w = (W - 120 - 45) // 4
    for i, (t_title, t_count, t_desc, accent) in enumerate(tiers):
        x0 = 60 + i * (card_w + 15)
        x1 = x0 + card_w
        draw.rounded_rectangle([x0, 135, x1, 285], radius=14, fill=(15, 23, 42), outline=accent, width=2)
        draw.text((x0 + 20, 150), t_title, font=font_tier_title, fill=(226, 232, 240))
        draw.text((x0 + 20, 188), t_count, font=font_tier_stat, fill=accent)
        draw.text((x0 + 20, 244), t_desc, font=font_row, fill=(148, 163, 184))

    # Feature Matrix Table (y: 310 to 1030)
    table_rect = [60, 310, W - 60, 1030]
    draw.rounded_rectangle(table_rect, radius=14, fill=(15, 23, 42), outline=(51, 65, 85), width=1)

    draw.text((85, 325), "FEATURE INVENTORY & INTEGRATION MATRIX (F1 to F24 ALL PASSING)", font=font_tier_title, fill=(56, 189, 248))

    feature_rows = [
        ("F1", "Stateful Resampling (zi carryover)", "Acoustic / DSP", "✓ PASS", "F13", "Boundary Deduplication", "Chunk Engine", "✓ PASS"),
        ("F2", "Dead DSP Filter Activation (85Hz)", "Hardware DSP", "✓ PASS", "F14", "Final Passage Consistency Check", "Pipeline", "✓ PASS"),
        ("F3", "WASAPI Rate Negotiation", "Audio Driver", "✓ PASS", "F15", "Alt+T Text Transformation", "Hotkeys", "✓ PASS"),
        ("F4", "Safe Device Disconnection", "Hardware Safe", "✓ PASS", "F16", "Alt+P 15-Section Prompt Template", "Prompt Meta", "✓ PASS"),
        ("F5", "Audio Capture Diagnostics", "Diagnostics", "✓ PASS", "F17", "Shortcut Pipeline Independence", "Architecture", "✓ PASS"),
        ("F6", "50cm-100cm Distance Reliability", "Mic Calibration", "✓ PASS", "F18", "Selection & Clipboard Safety", "Windows OS", "✓ PASS"),
        ("F7", "Groq Model Routing Fix", "Cloud Engine", "✓ PASS", "F19", "Remove 3 Spoken Action Triggers", "Command Safe", "✓ PASS"),
        ("F8", "Groq Client Verification", "Authentication", "✓ PASS", "F20", "Decouple Action Commands", "Architecture", "✓ PASS"),
        ("F9", "Offline Moonshine ONNX Integration", "Offline AI", "✓ PASS", "F21", "Retain Spoken Commands", "Voice Intent", "✓ PASS"),
        ("F10", "Model Settings UI Live Sync", "PyQt6 Settings", "✓ PASS", "F22", "Mid-Sentence Spoken Protection", "Linguistics", "✓ PASS"),
        ("F11", "Chunk Worker Reorder Queue", "Concurrency", "✓ PASS", "F23", "Single-Instance Win32 Mutex Audit", "OS Lifecycle", "✓ PASS"),
        ("F12", "Context-Aware Multi-Chunk Continuity", "Reconciler", "✓ PASS", "F24", "Safe Process & Directory Cleanup", "Packaging", "✓ PASS"),
    ]

    start_y = 370
    row_h = 52
    for idx, (id1, name1, cat1, st1, id2, name2, cat2, st2) in enumerate(feature_rows):
        cur_y = start_y + idx * row_h
        bg_col = (17, 24, 39) if idx % 2 == 0 else (15, 23, 42)
        draw.rectangle([65, cur_y - 2, W - 65, cur_y + row_h - 4], fill=bg_col)

        # Left Column
        draw.text((85, cur_y + 8), id1, font=font_tier_title, fill=(129, 140, 248))
        draw.text((150, cur_y + 11), name1, font=font_row, fill=(241, 245, 249))
        draw.text((600, cur_y + 11), cat1, font=font_row, fill=(148, 163, 184))
        draw.text((830, cur_y + 8), st1, font=font_tier_title, fill=(52, 211, 153))

        # Divider
        draw.line([(W // 2) - 10, cur_y - 2, (W // 2) - 10, cur_y + row_h - 4], fill=(51, 65, 85), width=1)

        # Right Column
        draw.text(((W // 2) + 20, cur_y + 8), id2, font=font_tier_title, fill=(129, 140, 248))
        draw.text(((W // 2) + 85, cur_y + 11), name2, font=font_row, fill=(241, 245, 249))
        draw.text(((W // 2) + 540, cur_y + 11), cat2, font=font_row, fill=(148, 163, 184))
        draw.text(((W // 2) + 780, cur_y + 8), st2, font=font_tier_title, fill=(52, 211, 153))

    card.save(str(out_img_path), quality=95)
    return card

def create_scene_frame(scene: dict, out_img_path: Path):
    W, H = 1920, 1080
    bg = Image.new("RGB", (W, H), color=(7, 10, 20))

    if scene.get("image") == "GENERATE_TEST_CARD":
        test_card_path = TEMP_DIR / "e2e_test_matrix_card.png"
        app_img = create_e2e_test_card(test_card_path)
        app_img.save(str(out_img_path), quality=95)
        return

    img_path = Path(scene["image"])
    if img_path.exists():
        app_img = Image.open(img_path).convert("RGBA")
        
        # Scale image to fill/fit 1920x1080 natively without borders or distortion
        app_img.thumbnail((W, H), Image.Resampling.LANCZOS)
        pos_x = (W - app_img.width) // 2
        pos_y = (H - app_img.height) // 2
        bg.paste(app_img, (pos_x, pos_y), app_img)

    # Clean UI: ZERO top banners, ZERO bottom banners, ZERO overlay boxes
    bg.save(str(out_img_path), quality=95)

def build_master_clean_overview_video():
    print("==================================================================")
    print(" GEMINI FLOW - MASTER CLEAN APPLICATION VIDEO OVERVIEW BUILDER    ")
    print(" Target: 1080p Full HD (1920x1080), 30fps                         ")
    print(" Clean UI: ZERO top/bottom banners, ZERO obstructive overlays     ")
    print("==================================================================")

    scene_clips = []
    timeline_records = []
    accumulated_time = 0.0

    for idx, scene in enumerate(SCENES):
        scene_id = scene["id"]
        print(f"\n[{idx+1}/{len(SCENES)}] Processing {scene_id} ({scene['title']})...")

        # 1. Voice Audio (Reuse pre-synthesized audio clips)
        audio_p = TEMP_DIR / f"{scene_id}.mp3"
        if not audio_p.exists() or audio_p.stat().st_size == 0:
            asyncio.run(generate_speech(scene["script"], audio_p))
        duration = get_audio_duration(audio_p)

        padding = 0.25
        scene_duration = duration + padding
        start_ts = accumulated_time
        end_ts = accumulated_time + scene_duration
        accumulated_time = end_ts

        timeline_records.append({
            "index": idx + 1,
            "id": scene_id,
            "title": scene["title"],
            "start": f"{int(start_ts // 60):02d}:{int(start_ts % 60):02d}",
            "end": f"{int(end_ts // 60):02d}:{int(end_ts % 60):02d}",
            "duration": f"{scene_duration:.1f}s"
        })
        print(f"  Speech Audio: {duration:.2f}s (Scene Clip: {scene_duration:.2f}s | {start_ts:.1f}s -> {end_ts:.1f}s)")

        # 2. Render Clean 1080p Frame
        frame_p = TEMP_DIR / f"{scene_id}_clean.png"
        create_scene_frame(scene, frame_p)

        # 3. Create Scene Video Clip with FFmpeg
        clip_p = TEMP_DIR / f"{scene_id}_clean.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-framerate", "30",
            "-t", f"{scene_duration:.2f}",
            "-i", str(frame_p),
            "-i", str(audio_p),
            "-af", f"apad=pad_dur={padding}",
            "-c:v", "libx264",
            "-preset", "faster",
            "-tune", "stillimage",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(clip_p)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        scene_clips.append(clip_p)
        print(f"  Generated Clean Clip -> {clip_p.name}")

    print(f"\n==================================================================")
    print(f"Total Video Timeline: {accumulated_time:.1f}s ({accumulated_time/60:.2f} minutes)")
    print("==================================================================")

    # Concat demuxer list
    concat_txt = TEMP_DIR / "concat_clean_list.txt"
    with open(concat_txt, "w", encoding="utf-8") as f:
        for c in scene_clips:
            f.write(f"file '{c.as_posix()}'\n")

    print(f"\n1. Concatenating into Master Clean MP4 ({OUT_MP4_PATH.name})...")
    cmd_concat_mp4 = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_txt),
        "-c", "copy",
        str(OUT_MP4_PATH)
    ]
    subprocess.run(cmd_concat_mp4, check=True)

    # Copy MP4 to root workspace
    shutil.copyfile(OUT_MP4_PATH, ROOT_MP4_COPY)

    print(f"\n2. Fast Transcoding into Master Clean WebM ({OUT_WEBM_PATH.name})...")
    cmd_webm = [
        "ffmpeg", "-y",
        "-i", str(OUT_MP4_PATH),
        "-c:v", "libvpx-vp9",
        "-deadline", "realtime",
        "-cpu-used", "6",
        "-b:v", "1200k",
        "-c:a", "libopus",
        "-b:a", "96k",
        str(OUT_WEBM_PATH)
    ]
    subprocess.run(cmd_webm, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Copy WebM to root workspace
    shutil.copyfile(OUT_WEBM_PATH, ROOT_WEBM_COPY)

    mp4_size_mb = OUT_MP4_PATH.stat().st_size / (1024 * 1024)
    webm_size_mb = OUT_WEBM_PATH.stat().st_size / (1024 * 1024)

    # Save Timeline JSON
    meta_json = PROJECT_ROOT / "videos" / "overview_chapters_meta.json"
    with open(meta_json, "w", encoding="utf-8") as f:
        import json
        json.dump(timeline_records, f, indent=2)

    print(f"\n==================================================================")
    print(f"✅ SUCCESS! CLEAN MASTER OVERVIEW VIDEO DELIVERED:")
    print(f"   MP4 Video (videos/): {OUT_MP4_PATH} ({mp4_size_mb:.2f} MB)")
    print(f"   MP4 Video (root):    {ROOT_MP4_COPY}")
    print(f"   WebM Video (videos/): {OUT_WEBM_PATH} ({webm_size_mb:.2f} MB)")
    print(f"   WebM Video (root):    {ROOT_WEBM_COPY}")
    print(f"   Total Duration:      {accumulated_time:.1f}s ({accumulated_time/60:.2f} minutes)")
    print("==================================================================")

if __name__ == "__main__":
    build_master_clean_overview_video()
