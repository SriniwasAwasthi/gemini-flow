"""
Gemini Flow - LinkedIn Production Walkthrough Generator (< 2 Minutes)
Generates a synchronized, 1080p 30fps video explaining every section of Gemini Flow:
1. Title / Architecture Overview
2. Section 01: API General
3. Section 02: Hotkeys Mode
4. Section 03: Cost & Productivity
5. Section 04: Vocabulary Engine
6. Section 05: Custom Dictionary
7. Section 06: Quick Text
8. Section 07: History
9. Section 08: Profiles
10. Section 09: AI Dictation
11. Section 10: Audio Device
12. Outro & GitHub Summary
"""
import os
import sys
import asyncio
import subprocess
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Set up paths
PROJECT_ROOT = Path(r"E:\W c One Drive\Wisper")
SCREENSHOTS_DIR = PROJECT_ROOT / "docs" / "screenshots"
POSTER_PATH = PROJECT_ROOT / "Gemini Flow AI Workspace Poster.png"
TEMP_DIR = PROJECT_ROOT / "videos" / "temp_linkedin_build"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

OUT_VIDEO_PATH = PROJECT_ROOT / "videos" / "Gemini_Flow_LinkedIn_Walkthrough_1080p.mp4"
ROOT_VIDEO_COPY = PROJECT_ROOT / "Gemini_Flow_LinkedIn_Walkthrough_1080p.mp4"

# Scene Definitions (Tuned for ~95s total duration, strictly < 120s)
SCENES = [
    {
        "id": "scene_00_intro",
        "title": "GEMINI FLOW • ENTERPRISE DESKTOP VOICE AI",
        "badge": "OVERVIEW",
        "image": str(POSTER_PATH),
        "bullets": "⚡ Google Gemini 3.5/3.7 Flash  •  🔒 Local Whisper int8 Fallback  •  🖥️ Native Windows 11 Desktop",
        "caption": "Meet Gemini Flow: an open-source, ultra-low latency voice dictation and prompt engineering workspace for Windows.",
        "script": "Meet Gemini Flow — an open-source, ultra-low latency AI voice dictation workspace for Windows, powered by Google Gemini and local Whisper AI."
    },
    {
        "id": "scene_01_api_general",
        "title": "SECTION 01 • API GENERAL & SECURITY",
        "badge": "01 / 10",
        "image": str(SCREENSHOTS_DIR / "01-main-dashboard.png"),
        "bullets": "🔑 Windows DPAPI Key Encryption  •  ⚡ Live Latency Checks  •  🛡️ Auto Whisper AI Fallback",
        "caption": "Section 1: API General — Multi-model routing across Gemini Flash, DPAPI encryption, and automatic offline failover.",
        "script": "API General: configure Gemini Flash models with live latency checks, Windows DPAPI encryption, and automatic offline Whisper fallback."
    },
    {
        "id": "scene_02_hotkeys",
        "title": "SECTION 02 • HOTKEYS & TRIGGER MODES",
        "badge": "02 / 10",
        "image": str(SCREENSHOTS_DIR / "03-hotkeys-mode.png"),
        "bullets": "🎙️ Hands-Free Toggle vs Push-to-Talk  •  ✨ AI Prompt Transform (Ctrl+Shift+Space)  •  🔔 Sound Feedback",
        "caption": "Section 2: Hotkeys Mode — Global hardware keyboard triggers with instant hands-free toggle or push-to-talk.",
        "script": "Hotkeys Mode: toggle hands-free or push-to-talk dictation with customizable global keybindings and instant audio feedback."
    },
    {
        "id": "scene_03_cost_productivity",
        "title": "SECTION 03 • COST & PRODUCTIVITY",
        "badge": "03 / 10",
        "image": str(SCREENSHOTS_DIR / "04-cost-productivity.png"),
        "bullets": "💰 Real-Time Token Economics ($0.0001/req)  •  📚 29 Writing Milestones  •  🚀 3.5x Faster Than Typing",
        "caption": "Section 3: Cost & Productivity — Live token usage metrics, dollar savings tracking, and gamified writing milestones.",
        "script": "Cost and Productivity: track real-time token savings, typing speed multipliers, and twenty-nine gamified writing milestones."
    },
    {
        "id": "scene_04_vocabulary",
        "title": "SECTION 04 • VOCABULARY ENGINE",
        "badge": "04 / 10",
        "image": str(SCREENSHOTS_DIR / "05-vocabulary-engine.png"),
        "bullets": "🧠 Technical Jargon Priming  •  🔊 Phonetic Sound-Alikes  •  💾 Developer Dictionaries",
        "caption": "Section 4: Vocabulary Engine — Primes custom jargon, camelCase functions, and names so they are never misheard.",
        "script": "Vocabulary Engine: prime technical jargon, camelCase functions, and names with phonetic sound-alikes so nothing is misheard."
    },
    {
        "id": "scene_05_custom_dictionary",
        "title": "SECTION 05 • CUSTOM DICTIONARY",
        "badge": "05 / 10",
        "image": str(SCREENSHOTS_DIR / "06-custom-dictionary.png"),
        "bullets": "🔍 Regex Word-Boundary Rules  •  🎯 Exact Substitution ('pie torch' ➔ PyTorch)  •  ⚙️ Acronym Standardization",
        "caption": "Section 5: Custom Dictionary — Exact regex boundary replacement to eliminate speech recognition errors.",
        "script": "Custom Dictionary: exact regex word-boundary rules eliminate recognition errors and standardize domain acronyms."
    },
    {
        "id": "scene_06_quick_text",
        "title": "SECTION 06 • QUICK TEXT (VOICE SNIPPETS)",
        "badge": "06 / 10",
        "image": str(SCREENSHOTS_DIR / "07-quick-text.png"),
        "bullets": "⚡ Spoken Trigger Words  •  📝 Multi-Line Template Expansion  •  🚀 Zero-Latency Clipboard Injection",
        "caption": "Section 6: Quick Text — Voice macro snippets expanding spoken keywords into pre-formatted text blocks.",
        "script": "Quick Text: voice macros expanding spoken trigger words into complex, pre-formatted multi-line text templates."
    },
    {
        "id": "scene_07_history",
        "title": "SECTION 07 • HISTORY & SAFEGUARD AUDIT",
        "badge": "07 / 10",
        "image": str(SCREENSHOTS_DIR / "08-history.png"),
        "bullets": "📑 Dual-View: Converted AI Prompt vs Raw Speech  •  🔎 Search & Filter  •  📋 One-Click Copy & Export",
        "caption": "Section 7: History — Comprehensive searchable log with dual-view tabs comparing AI prompts against raw spoken speech.",
        "script": "History: searchable audit logs with dual-view tabs comparing converted AI prompts against raw spoken speech safeguards."
    },
    {
        "id": "scene_08_profiles",
        "title": "SECTION 08 • PROFILES & APPLICATION CONTEXT",
        "badge": "08 / 10",
        "image": str(SCREENSHOTS_DIR / "09-profiles-commands.png"),
        "bullets": "🖥️ Foreground HWND App Detection (VS Code, Slack, Email)  •  🗣️ 16 Built-in Voice Command Categories",
        "caption": "Section 8: Profiles — Context-aware engine auto-adjusting tone and prompt rules based on your active window.",
        "script": "Profiles: context-aware intelligence automatically adapts tone and prompt rules based on your active app, like VS Code or Slack."
    },
    {
        "id": "scene_09_ai_dictation",
        "title": "SECTION 09 • AI DICTATION & FORMATTING",
        "badge": "09 / 10",
        "image": str(SCREENSHOTS_DIR / "10-ai-dictation.png"),
        "bullets": "🧹 Disfluency & Stutter Removal ('um', 'ah')  •  🇮🇳 Indian English / Hinglish Grounding  •  ✨ Clean Markdown",
        "caption": "Section 9: AI Dictation — Intelligent text cleaning eliminating verbal filler words and formatting crisp text.",
        "script": "AI Dictation: automatically strips filler words, removes stutters, formats clean Markdown, and normalizes Indian English idioms."
    },
    {
        "id": "scene_10_audio_device",
        "title": "SECTION 10 • AUDIO DEVICE & HARDWARE DSP",
        "badge": "10 / 10",
        "image": str(SCREENSHOTS_DIR / "02-audio-device.png"),
        "bullets": "🎙️ Real-Time VU Level Meter  •  🎛️ 85Hz High-Pass Rumble Filter  •  🔇 Dynamic Soft-Knee Noise Gate (-42dB)",
        "caption": "Section 10: Audio Device — Hardware mic selection with live VU meters, 85Hz filter, and dynamic noise gating.",
        "script": "Audio Device: hardware mic selection with live VU monitoring, an eighty-five Hertz high-pass filter, and dynamic noise gating."
    },
    {
        "id": "scene_11_outro",
        "title": "GEMINI FLOW • PRODUCTION READY & OPEN SOURCE",
        "badge": "GITHUB READY",
        "image": str(POSTER_PATH),
        "bullets": "⭐ 100% Open Source on GitHub  •  🛠️ Built with PyQt6, Python & Google Gemini  •  🚀 Built by Sriniwas Awasthi",
        "caption": "Gemini Flow: voice-to-text engineered for developers. Built with PyQt6 and Gemini. Open source on GitHub!",
        "script": "Gemini Flow: voice-to-text engineered for developers. Built with PyQt6 and Gemini. Open source on GitHub!"
    }
]

async def generate_speech(text: str, out_path: Path):
    import edge_tts
    # Christopher is an articulate, warm, executive tech voice at +8% rate for brisk professional pacing
    communicator = edge_tts.Communicate(text, "en-US-ChristopherNeural", rate="+8%")
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

def create_scene_frame(scene: dict, out_img_path: Path):
    W, H = 1920, 1080
    bg = Image.new("RGB", (W, H), color=(7, 10, 20))
    draw = ImageDraw.Draw(bg)

    # Fonts
    font_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 30)
    font_badge = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 18)
    font_bullets = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 22)
    font_caption = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 24)

    # Top Navigation Glassmorphic Bar (y: 15 to 85)
    bar_rect = [20, 15, W - 20, 85]
    draw.rounded_rectangle(bar_rect, radius=12, fill=(15, 23, 42), outline=(99, 102, 241), width=1)

    # Badge Pill
    badge_rect = [35, 27, 180, 73]
    draw.rounded_rectangle(badge_rect, radius=8, fill=(79, 70, 229))
    draw.text((48, 38), scene["badge"], font=font_badge, fill=(255, 255, 255))

    # Main Title in Header
    draw.text((205, 33), scene["title"], font=font_title, fill=(248, 250, 252))

    # Right branding text
    draw.text((W - 360, 38), "Gemini Flow • Windows 11", font=font_badge, fill=(148, 163, 184))

    # Center Application Screenshot Frame (available area: y: 95 to 940)
    img_path = Path(scene["image"])
    if img_path.exists():
        app_img = Image.open(img_path).convert("RGBA")
        
        # Max dimensions inside frame
        max_w, max_h = 1880, 840
        app_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        
        # Center horizontally and vertically within bounds
        pos_x = (W - app_img.width) // 2
        pos_y = 95 + (840 - app_img.height) // 2
        
        # Outer border / drop shadow box
        border_rect = [pos_x - 3, pos_y - 3, pos_x + app_img.width + 3, pos_y + app_img.height + 3]
        draw.rounded_rectangle(border_rect, radius=10, fill=(11, 15, 25), outline=(99, 102, 241), width=2)
        
        # Paste app screenshot
        bg.paste(app_img, (pos_x, pos_y), app_img)

    # Bottom Subtitle / Captions Glassmorphic Banner (y: 955 to 1065)
    bottom_rect = [20, 955, W - 20, 1065]
    draw.rounded_rectangle(bottom_rect, radius=12, fill=(11, 15, 25), outline=(99, 102, 241), width=1)

    # Technical Bullets row
    draw.text((40, 968), scene["bullets"], font=font_bullets, fill=(56, 189, 248))

    # Spoken Caption / Subtitle row
    draw.text((40, 1012), scene["caption"], font=font_caption, fill=(241, 245, 249))

    bg.save(str(out_img_path), quality=95)

def build_all():
    print("==================================================")
    print(" GEMINI FLOW - LINKEDIN WALKTHROUGH VIDEO BUILDER ")
    print(" Target: 1080p Full HD, strictly < 2 Minutes      ")
    print("==================================================")

    scene_clips = []
    total_duration = 0.0

    for idx, scene in enumerate(SCENES):
        scene_id = scene["id"]
        print(f"\n[{idx+1}/{len(SCENES)}] Processing {scene_id} ({scene['badge']})...")

        # 1. Generate Voice Audio
        audio_p = TEMP_DIR / f"{scene_id}.mp3"
        asyncio.run(generate_speech(scene["script"], audio_p))
        duration = get_audio_duration(audio_p)
        
        # Add 0.25s breathing padding per scene
        scene_duration = duration + 0.25
        total_duration += scene_duration
        print(f"  Speech Audio: {duration:.2f}s (Clip Target: {scene_duration:.2f}s)")

        # 2. Render Frame
        frame_p = TEMP_DIR / f"{scene_id}.png"
        create_scene_frame(scene, frame_p)

        # 3. Create Scene Clip with FFmpeg
        clip_p = TEMP_DIR / f"{scene_id}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-framerate", "30",
            "-t", f"{scene_duration:.2f}",
            "-i", str(frame_p),
            "-i", str(audio_p),
            "-af", f"apad=pad_dur=0.25",
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
        print(f"  Generated Clip -> {clip_p.name}")

    print(f"\nTotal Calculated Duration: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
    assert total_duration < 120.0, f"Error: Total duration {total_duration}s exceeds 2 minutes!"

    # Concat demuxer list
    concat_txt = TEMP_DIR / "concat_list.txt"
    with open(concat_txt, "w", encoding="utf-8") as f:
        for c in scene_clips:
            # Escape path for ffmpeg concat
            f.write(f"file '{c.as_posix()}'\n")

    print(f"\nConcatenating {len(scene_clips)} scenes into Master Video...")
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_txt),
        "-c", "copy",
        str(OUT_VIDEO_PATH)
    ]
    subprocess.run(cmd_concat, check=True)

    # Also copy to root Wisper for instant access
    import shutil
    shutil.copyfile(OUT_VIDEO_PATH, ROOT_VIDEO_COPY)

    final_size = OUT_VIDEO_PATH.stat().st_size / (1024 * 1024)
    print(f"\n==================================================")
    print(f"✅ SUCCESS! Master LinkedIn Video Rendered:")
    print(f"   Path: {OUT_VIDEO_PATH}")
    print(f"   Root Path: {ROOT_VIDEO_COPY}")
    print(f"   Duration: {total_duration:.1f}s (under 2 minutes!)")
    print(f"   Size: {final_size:.2f} MB")
    print("==================================================")

if __name__ == "__main__":
    build_all()
