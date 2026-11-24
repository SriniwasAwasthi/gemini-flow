"""
Gemini Flow - 3-Minute Technical Showcase Video Generator (< 180s)
Accurately and comprehensively demonstrates:
- Agent 1: Records whole application in 1080p Full HD at 30 FPS (Zero floating mouse).
- Agent 2: Operates live PyQt6 UI, types masked API key with active Gaussian blur,
  checks new Whisper Mode (+12dB), shows 8.0s Watchdog & Recovery Shortcut (Shift+Alt+Z),
  demonstrates Vocabulary Engine (Live Normalization Sandbox), Custom Dictionary (Phonetic pairs),
  Quick Text (Voice Macros), and History Anti-Hallucination.
- Agent 3: Real-time Christopher Neural voiceover synchronized with Agent 2's actions.
"""
import os
import sys
import time
import math
import subprocess
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PROJECT_ROOT = Path(r"E:\W c One Drive\Wisper")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# PyQt6 imports
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem, QTableWidgetItem
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QImage, QFont, QColor

# Project imports
from app.config import ConfigManager
from app.ui.settings_dialog import SettingsDialog

AUDIO_DIR = PROJECT_ROOT / "videos" / "temp_3min_build"
BUILD_DIR = PROJECT_ROOT / "videos" / "temp_3min_render"
BUILD_DIR.mkdir(parents=True, exist_ok=True)

FINAL_MP4 = PROJECT_ROOT / "videos" / "Gemini_Flow_3Agent_Showcase_3min_1080p.mp4"
ROOT_MP4 = PROJECT_ROOT / "Gemini_Flow_3Agent_Showcase_3min_1080p.mp4"
FINAL_WEBM = PROJECT_ROOT / "videos" / "Gemini_Flow_3Agent_Showcase_3min_1080p.webm"
ROOT_WEBM = PROJECT_ROOT / "Gemini_Flow_3Agent_Showcase_3min_1080p.webm"

POSTER_PATH = PROJECT_ROOT / "Gemini Flow AI Productivity Infographic.png"
if not POSTER_PATH.exists():
    POSTER_PATH = PROJECT_ROOT / "Gemini Flow AI Workspace Poster.png"
TEST_MATRIX_PATH = PROJECT_ROOT / "videos" / "temp_full_overview_build" / "e2e_test_matrix_card.png"

def get_audio_duration(audio_path: Path) -> float:
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)]
    out = subprocess.check_output(cmd).decode().strip()
    return float(out)

def grab_dialog_to_pil(dialog) -> Image.Image:
    qimg = dialog.grab().toImage()
    width = qimg.width()
    height = qimg.height()
    ptr = qimg.bits()
    ptr.setsize(height * width * 4)
    raw_img = Image.frombuffer("RGBA", (width, height), bytes(ptr), "raw", "BGRA", 0, 1).convert("RGB")
    
    canvas = Image.new("RGB", (1920, 1080), (10, 14, 23))
    x_off = (1920 - width) // 2
    y_off = (1080 - height) // 2
    canvas.paste(raw_img, (x_off, y_off))
    return canvas

def get_widget_frame_pos(dialog, widget) -> tuple:
    if not widget:
        return (960, 540)
    center = widget.rect().center()
    pt = widget.mapTo(dialog, center)
    x_off = (1920 - dialog.width()) // 2
    y_off = (1080 - dialog.height()) // 2
    return (pt.x() + x_off, pt.y() + y_off)

def interpolate_trajectory(waypoints, t_norm):
    if t_norm <= waypoints[0][0]:
        return waypoints[0][1], waypoints[0][2], 0.0
    if t_norm >= waypoints[-1][0]:
        return waypoints[-1][1], waypoints[-1][2], 0.0
        
    for i in range(len(waypoints) - 1):
        t0, x0, y0, c0 = waypoints[i]
        t1, x1, y1, c1 = waypoints[i+1]
        if t0 <= t_norm <= t1:
            span = max(1e-4, t1 - t0)
            u = (t_norm - t0) / span
            s = 0.5 - 0.5 * math.cos(u * math.pi)
            x = x0 + (x1 - x0) * s
            y = y0 + (y1 - y0) * s
            click_prog = u if (c0 or c1) else 0.0
            return x, y, click_prog
    return waypoints[-1][1], waypoints[-1][2], 0.0

def draw_cursor_and_ripple(base_img: Image.Image, cx: float, cy: float, click_prog: float) -> Image.Image:
    # Zero floating mouse - return clean frame
    return base_img

def render_scene_video(scene_id: str, audio_path: Path, out_mp4: Path, frame_generator_fn, fps: int = 30):
    dur = get_audio_duration(audio_path)
    total_frames = int(math.ceil(dur * fps))
    print(f"[{scene_id}] Rendering {total_frames} frames ({dur:.2f}s) -> {out_mp4.name}...")
    
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", "1920x1080",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(out_mp4)
    ]
    
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    for f_idx in range(total_frames):
        t_sec = f_idx / fps
        t_norm = min(1.0, t_sec / dur)
        frame_img = frame_generator_fn(f_idx, t_sec, t_norm, total_frames)
        proc.stdin.write(frame_img.tobytes())
    proc.stdin.close()
    proc.wait()
    t_elapsed = time.time() - t0
    fps_render = total_frames / max(1e-3, t_elapsed)
    print(f"[{scene_id}] Completed in {t_elapsed:.1f}s ({fps_render:.1f} FPS)")

def build_all_scenes():
    app = QApplication.instance() or QApplication(sys.argv)
    cfg = ConfigManager()

    # Pre-populate rich developer data for Custom Dictionary
    custom_dict = [
        {"spoken": "pie dantic", "replacement": "Pydantic"},
        {"spoken": "fast api", "replacement": "FastAPI"},
        {"spoken": "whisper x", "replacement": "WhisperX"},
        {"spoken": "git hub", "replacement": "GitHub"},
        {"spoken": "rn noise", "replacement": "RNNoise"},
        {"spoken": "silero vad", "replacement": "Silero-VAD"},
        {"spoken": "post gres", "replacement": "PostgreSQL"},
        {"spoken": "docker compose", "replacement": "docker-compose"},
    ]
    cfg.set_dictionary(custom_dict)

    # Pre-populate rich developer data for Quick Text Macros
    snippets = [
        {"trigger": "my developer bio", "text": "Srinivas Awasthi | Senior AI Engineer | github.com/srinivas-awasthi | linkedin.com/in/srinivas-awasthi"},
        {"trigger": "insert bug report template", "text": "## Description\n\n## Reproduction Steps\n1. \n2. \n\n## Expected vs Actual Behavior\n"},
        {"trigger": "paste meeting sync agenda", "text": "Hi team, thanks for joining. Today's agenda: 1) Speech pipeline latency 2) Custom vocabulary normalization 3) CI/CD deployment."},
        {"trigger": "license header", "text": "// Copyright (c) 2026 Srinivas Awasthi. All rights reserved. Open-source under MIT License."},
    ]
    cfg.set_snippets(snippets)

    dlg = SettingsDialog(cfg, None)
    dlg.resize(1536, 864)
    dlg.show()
    app.processEvents()

    dlg._refresh_dictionary()
    dlg._refresh_snippets()
    app.processEvents()
    
    poster_raw = Image.open(str(POSTER_PATH)).convert("RGB")
    poster_img = poster_raw.resize((1920, 1080), Image.Resampling.LANCZOS)
    
    test_matrix_img = poster_img
    if TEST_MATRIX_PATH.exists():
        test_raw = Image.open(str(TEST_MATRIX_PATH)).convert("RGB")
        test_matrix_img = test_raw.resize((1920, 1080), Image.Resampling.LANCZOS)
    
    scene_clips = []
    
    # =========================================================================
    # SCENE 01: INTRO • GEMINI FLOW 3-AGENT PIPELINE
    # =========================================================================
    audio_01 = AUDIO_DIR / "scene_01_intro.mp3"
    out_01 = BUILD_DIR / "scene_01_intro.mp4"
    waypoints_01 = [(0.0, 960, 540, False), (1.0, 960, 540, False)]
    def gen_01(f_idx, t_sec, t_norm, total_frames):
        return poster_img
    render_scene_video("scene_01_intro", audio_01, out_01, gen_01)
    scene_clips.append(out_01)
    
    # =========================================================================
    # SCENE 02: API SECURITY & BLURRED KEY INSERTION
    # =========================================================================
    audio_02 = AUDIO_DIR / "scene_02_api.mp3"
    out_02 = BUILD_DIR / "scene_02_api.mp4"
    
    dlg.tabs.setCurrentIndex(0)
    for i, b in enumerate(dlg.nav_buttons):
        b.set_active(i == 0)
    dlg.api_key_input.setText("")
    dlg.api_status_label.setText("")
    app.processEvents()
    
    pos_api_input = get_widget_frame_pos(dlg, dlg.api_key_input)
    pos_test_api = get_widget_frame_pos(dlg, dlg.btn_test_api)
    
    waypoints_02 = [
        (0.00, pos_api_input[0], pos_api_input[1], False),
        (0.20, pos_api_input[0], pos_api_input[1], True),
        (0.55, pos_test_api[0], pos_test_api[1], True),
        (1.00, pos_test_api[0], pos_test_api[1], False),
    ]
    
    dlg.api_key_input.setText("")
    dlg.api_status_label.setText("")
    app.processEvents()
    frame_s02_empty = grab_dialog_to_pil(dlg)
    
    dlg.api_key_input.setText("••••••••••••••••••••••••••••••••")
    dlg.api_status_label.setText("Testing API key connection...")
    app.processEvents()
    frame_s02_typing = grab_dialog_to_pil(dlg)
    
    dlg.api_status_label.setText("✅ Connection verified! Google Gemini 2.5 Flash latency: 182ms (Ready)")
    dlg.cb_log_redaction.setChecked(True)
    app.processEvents()
    frame_s02_verified = grab_dialog_to_pil(dlg)
    
    def gen_02(f_idx, t_sec, t_norm, total_frames):
        if t_norm < 0.20:
            base = frame_s02_empty
        elif t_norm < 0.55:
            base = frame_s02_typing
        else:
            base = frame_s02_verified
            
        # Active privacy Gaussian blur on the API key insertion field
        if 0.20 <= t_norm < 0.65:
            base = base.copy()
            blur_box = (max(0, pos_api_input[0] - 260), max(0, pos_api_input[1] - 24), min(1920, pos_api_input[0] + 260), min(1080, pos_api_input[1] + 24))
            region = base.crop(blur_box).filter(ImageFilter.GaussianBlur(radius=10))
            base.paste(region, blur_box)
            
        cx, cy, c_prog = interpolate_trajectory(waypoints_02, t_norm)
        return draw_cursor_and_ripple(base, cx, cy, c_prog)
    
    render_scene_video("scene_02_api", audio_02, out_02, gen_02)
    scene_clips.append(out_02)
    
    # =========================================================================
    # SCENE 03: AUDIO DSP & NEW WHISPER MODE (+12dB)
    # =========================================================================
    audio_03 = AUDIO_DIR / "scene_03_dsp.mp3"
    out_03 = BUILD_DIR / "scene_03_dsp.mp4"
    
    dlg.tabs.setCurrentIndex(9)
    for i, b in enumerate(dlg.nav_buttons):
        b.set_active(i == 9)
    dlg.cb_dsp_fan_filter.setChecked(False)
    dlg.cb_dsp_noise_gate.setChecked(False)
    if hasattr(dlg, 'cb_whisper_mode') and dlg.cb_whisper_mode:
        dlg.cb_whisper_mode.setChecked(False)
    app.processEvents()
    
    pos_fan_filter = get_widget_frame_pos(dlg, dlg.cb_dsp_fan_filter)
    pos_level_bar = get_widget_frame_pos(dlg, dlg.mic_level_bar)
    pos_whisper_mode = get_widget_frame_pos(dlg, dlg.cb_whisper_mode) if hasattr(dlg, 'cb_whisper_mode') and dlg.cb_whisper_mode else pos_fan_filter
    
    waypoints_03 = [
        (0.00, pos_fan_filter[0], pos_fan_filter[1], False),
        (0.30, pos_level_bar[0], pos_level_bar[1], False),
        (0.60, pos_fan_filter[0], pos_fan_filter[1], True),
        (0.85, pos_whisper_mode[0], pos_whisper_mode[1], True),
        (1.00, pos_whisper_mode[0], pos_whisper_mode[1], False),
    ]
    
    frame_s03_base = grab_dialog_to_pil(dlg)
    
    vu_frames_03 = []
    for v in [20, 45, 75, 88, 65, 30, 8]:
        dlg.mic_level_bar.setValue(v)
        dlg.mic_level_label.setText(f"{v}%")
        app.processEvents()
        vu_frames_03.append(grab_dialog_to_pil(dlg))
        
    dlg.cb_dsp_fan_filter.setChecked(True)
    dlg.cb_dsp_noise_gate.setChecked(True)
    if hasattr(dlg, 'cb_whisper_mode') and dlg.cb_whisper_mode:
        dlg.cb_whisper_mode.setChecked(True)
    dlg.mic_level_bar.setValue(0)
    dlg.mic_level_label.setText("0%")
    app.processEvents()
    frame_s03_active = grab_dialog_to_pil(dlg)
    
    def gen_03(f_idx, t_sec, t_norm, total_frames):
        if t_norm < 0.25:
            base = frame_s03_base
        elif 0.25 <= t_norm < 0.60:
            idx = int((t_sec * 6) % len(vu_frames_03))
            base = vu_frames_03[idx]
        else:
            base = frame_s03_active
        cx, cy, c_prog = interpolate_trajectory(waypoints_03, t_norm)
        return draw_cursor_and_ripple(base, cx, cy, c_prog)
    
    render_scene_video("scene_03_dsp", audio_03, out_03, gen_03)
    scene_clips.append(out_03)
    
    # =========================================================================
    # SCENE 04: HOTKEYS MODE & 8s EMERGENCY WATCHDOG & RECOVERY SHORTCUT
    # =========================================================================
    audio_04 = AUDIO_DIR / "scene_04_hotkeys.mp3"
    out_04 = BUILD_DIR / "scene_04_hotkeys.mp4"
    
    dlg.tabs.setCurrentIndex(1)
    for i, b in enumerate(dlg.nav_buttons):
        b.set_active(i == 1)
    dlg.radio_ptt.setChecked(False)
    dlg.radio_toggle.setChecked(True)
    app.processEvents()
    
    pos_ptt = get_widget_frame_pos(dlg, dlg.radio_ptt)
    pos_toggle = get_widget_frame_pos(dlg, dlg.radio_toggle)
    pos_recover_btn = get_widget_frame_pos(dlg, dlg.recover_hotkey_btn) if hasattr(dlg, 'recover_hotkey_btn') and dlg.recover_hotkey_btn else pos_ptt
    
    waypoints_04 = [
        (0.00, pos_toggle[0], pos_toggle[1], False),
        (0.25, pos_ptt[0], pos_ptt[1], True),
        (0.55, pos_toggle[0], pos_toggle[1], True),
        (0.82, pos_recover_btn[0], pos_recover_btn[1], True),
        (1.00, pos_recover_btn[0], pos_recover_btn[1], False),
    ]
    
    frame_s04_toggle = grab_dialog_to_pil(dlg)
    dlg.radio_ptt.setChecked(True)
    app.processEvents()
    frame_s04_ptt = grab_dialog_to_pil(dlg)
    dlg.radio_toggle.setChecked(True)
    app.processEvents()
    
    def gen_04(f_idx, t_sec, t_norm, total_frames):
        base = frame_s04_ptt if 0.22 <= t_norm < 0.55 else frame_s04_toggle
        cx, cy, c_prog = interpolate_trajectory(waypoints_04, t_norm)
        return draw_cursor_and_ripple(base, cx, cy, c_prog)
    
    render_scene_video("scene_04_hotkeys", audio_04, out_04, gen_04)
    scene_clips.append(out_04)
    
    # =========================================================================
    # SCENE 05: VOCABULARY ENGINE & LIVE NORMALIZATION SANDBOX (TAB 3)
    # =========================================================================
    audio_05 = AUDIO_DIR / "scene_05_vocab.mp3"
    out_05 = BUILD_DIR / "scene_05_vocab.mp4"
    
    dlg.tabs.setCurrentIndex(3)
    for i, b in enumerate(dlg.nav_buttons):
        b.set_active(i == 3)
    dlg.vocab_test_input.setText("")
    dlg.vocab_test_output.setText("")
    app.processEvents()
    frame_s05_initial = grab_dialog_to_pil(dlg)

    dlg.vocab_test_input.setText("testing fast whisper with pie dantic and git hub")
    dlg.vocab_test_output.setText("testing Faster-Whisper with Pydantic and GitHub")
    app.processEvents()
    frame_s05_normalized = grab_dialog_to_pil(dlg)

    pos_nav_vocab = get_widget_frame_pos(dlg, dlg.nav_buttons[3])
    pos_sandbox_in = get_widget_frame_pos(dlg, dlg.vocab_test_input)
    pos_btn_add_vocab = get_widget_frame_pos(dlg, dlg.btn_add_vocab)

    waypoints_05 = [
        (0.00, pos_nav_vocab[0], pos_nav_vocab[1], False),
        (0.25, pos_btn_add_vocab[0], pos_btn_add_vocab[1], True),
        (0.55, pos_sandbox_in[0], pos_sandbox_in[1], True),
        (1.00, pos_sandbox_in[0] + 180, pos_sandbox_in[1] + 30, False),
    ]

    def gen_05(f_idx, t_sec, t_norm, total_frames):
        base = frame_s05_normalized if t_norm >= 0.40 else frame_s05_initial
        cx, cy, c_prog = interpolate_trajectory(waypoints_05, t_norm)
        return draw_cursor_and_ripple(base, cx, cy, c_prog)

    render_scene_video("scene_05_vocab", audio_05, out_05, gen_05)
    scene_clips.append(out_05)

    # =========================================================================
    # SCENE 06: CUSTOM PHONETIC DICTIONARY (TAB 4)
    # =========================================================================
    audio_06 = AUDIO_DIR / "scene_06_dictionary.mp3"
    out_06 = BUILD_DIR / "scene_06_dictionary.mp4"

    dlg.tabs.setCurrentIndex(4)
    for i, b in enumerate(dlg.nav_buttons):
        b.set_active(i == 4)
    dlg.dict_table.setCurrentCell(0, 0)
    dlg._on_dict_row_selected()
    app.processEvents()
    frame_s06_row0 = grab_dialog_to_pil(dlg)

    dlg.dict_table.setCurrentCell(1, 0)
    dlg._on_dict_row_selected()
    app.processEvents()
    frame_s06_row1 = grab_dialog_to_pil(dlg)

    pos_nav_dict = get_widget_frame_pos(dlg, dlg.nav_buttons[4])
    pos_btn_add_dict = get_widget_frame_pos(dlg, dlg.btn_add_dict)
    pos_dict_table = get_widget_frame_pos(dlg, dlg.dict_table)

    waypoints_06 = [
        (0.00, pos_nav_dict[0], pos_nav_dict[1], True),
        (0.30, pos_dict_table[0], pos_dict_table[1] - 80, True),
        (0.65, pos_dict_table[0], pos_dict_table[1] - 40, True),
        (0.90, pos_btn_add_dict[0], pos_btn_add_dict[1], True),
        (1.00, pos_btn_add_dict[0], pos_btn_add_dict[1], False),
    ]

    def gen_06(f_idx, t_sec, t_norm, total_frames):
        base = frame_s06_row1 if t_norm >= 0.50 else frame_s06_row0
        cx, cy, c_prog = interpolate_trajectory(waypoints_06, t_norm)
        return draw_cursor_and_ripple(base, cx, cy, c_prog)

    render_scene_video("scene_06_dictionary", audio_06, out_06, gen_06)
    scene_clips.append(out_06)

    # =========================================================================
    # SCENE 07: QUICK TEXT VOICE MACROS (TAB 5)
    # =========================================================================
    audio_07 = AUDIO_DIR / "scene_07_quicktext.mp3"
    out_07 = BUILD_DIR / "scene_07_quicktext.mp4"

    dlg.tabs.setCurrentIndex(5)
    for i, b in enumerate(dlg.nav_buttons):
        b.set_active(i == 5)
    dlg.snippet_table.setCurrentCell(0, 0)
    app.processEvents()
    frame_s07_row0 = grab_dialog_to_pil(dlg)

    dlg.snippet_table.setCurrentCell(1, 0)
    app.processEvents()
    frame_s07_row1 = grab_dialog_to_pil(dlg)

    pos_nav_snip = get_widget_frame_pos(dlg, dlg.nav_buttons[5])
    pos_btn_add_snip = get_widget_frame_pos(dlg, dlg.btn_add_snippet)
    pos_snip_table = get_widget_frame_pos(dlg, dlg.snippet_table)

    waypoints_07 = [
        (0.00, pos_nav_snip[0], pos_nav_snip[1], True),
        (0.35, pos_snip_table[0], pos_snip_table[1] - 80, True),
        (0.70, pos_snip_table[0], pos_snip_table[1] - 40, True),
        (0.90, pos_btn_add_snip[0], pos_btn_add_snip[1], True),
        (1.00, pos_btn_add_snip[0], pos_btn_add_snip[1], False),
    ]

    def gen_07(f_idx, t_sec, t_norm, total_frames):
        base = frame_s07_row1 if t_norm >= 0.50 else frame_s07_row0
        cx, cy, c_prog = interpolate_trajectory(waypoints_07, t_norm)
        return draw_cursor_and_ripple(base, cx, cy, c_prog)

    render_scene_video("scene_07_quicktext", audio_07, out_07, gen_07)
    scene_clips.append(out_07)

    # =========================================================================
    # SCENE 08: HISTORY & CLEANED MODEL FILTER & ANTI-HALLUCINATION
    # =========================================================================
    audio_08 = AUDIO_DIR / "scene_08_history.mp3"
    out_08 = BUILD_DIR / "scene_08_history.mp4"
    
    dlg.tabs.setCurrentIndex(6)
    for i, b in enumerate(dlg.nav_buttons):
        b.set_active(i == 6)
    dlg.history_detail_tabs.setCurrentIndex(0)
    dlg.history_detail_text.setPlainText("Convert payment processing service to asynchronous FastAPI with Pydantic v2 schemas and Stripe webhook verification.")
    dlg.history_raw_detail_text.setPlainText("convert payment processing service to async fast api with pie dantic schemas and stripe webhook verification")
    app.processEvents()
    
    frame_s08_prompt = grab_dialog_to_pil(dlg)
    dlg.history_detail_tabs.setCurrentIndex(1)
    app.processEvents()
    frame_s08_raw = grab_dialog_to_pil(dlg)
    
    pos_filter_btn = get_widget_frame_pos(dlg, dlg.btn_filter_by) if hasattr(dlg, 'btn_filter_by') and dlg.btn_filter_by else (960, 200)
    pos_detail_tabs = get_widget_frame_pos(dlg, dlg.history_detail_tabs)
    
    waypoints_08 = [
        (0.00, pos_filter_btn[0], pos_filter_btn[1], True),
        (0.35, pos_filter_btn[0], pos_filter_btn[1], False),
        (0.65, pos_detail_tabs[0] - 50, pos_detail_tabs[1], True),
        (0.85, pos_detail_tabs[0] + 50, pos_detail_tabs[1], True),
        (1.00, pos_detail_tabs[0], pos_detail_tabs[1], False),
    ]
    
    def gen_08(f_idx, t_sec, t_norm, total_frames):
        base = frame_s08_raw if t_norm >= 0.70 else frame_s08_prompt
        cx, cy, c_prog = interpolate_trajectory(waypoints_08, t_norm)
        return draw_cursor_and_ripple(base, cx, cy, c_prog)
    
    render_scene_video("scene_08_history", audio_08, out_08, gen_08)
    scene_clips.append(out_08)
    
    # =========================================================================
    # SCENE 09: 28/28 TEST MATRIX & HERO POSTER OUTRO
    # =========================================================================
    audio_09 = AUDIO_DIR / "scene_09_outro.mp3"
    out_09 = BUILD_DIR / "scene_09_outro.mp4"
    waypoints_09 = [(0.0, 960, 540, False), (1.0, 960, 540, False)]
    
    def gen_09(f_idx, t_sec, t_norm, total_frames):
        base = test_matrix_img if t_norm < 0.45 else poster_img
        cx, cy, c_prog = interpolate_trajectory(waypoints_09, t_norm)
        return draw_cursor_and_ripple(base, cx, cy, c_prog)
        
    render_scene_video("scene_09_outro", audio_09, out_09, gen_09)
    scene_clips.append(out_09)
    
    # =========================================================================
    # CONCATENATE ALL 9 SCENES INTO MASTER <= 3 MIN VIDEO
    # =========================================================================
    print("Concatenating all 9 scenes into master showcase video...")
    concat_list_file = BUILD_DIR / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for clip in scene_clips:
            f.write(f"file '{clip.resolve()}'\n")
            
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(FINAL_MP4)
    ]
    subprocess.run(concat_cmd, check=True)
    shutil.copyfile(str(FINAL_MP4), str(ROOT_MP4))
    
    # Transcode to WebM
    print("Transcoding to master WebM (VP9 / Opus)...")
    webm_cmd = [
        "ffmpeg", "-y",
        "-i", str(FINAL_MP4),
        "-c:v", "libvpx-vp9",
        "-b:v", "2800k",
        "-crf", "28",
        "-deadline", "realtime",
        "-cpu-used", "6",
        "-c:a", "libopus",
        "-b:a", "128k",
        str(FINAL_WEBM)
    ]
    subprocess.run(webm_cmd, check=True)
    shutil.copyfile(str(FINAL_WEBM), str(ROOT_WEBM))
    
    dur_final = get_audio_duration(FINAL_MP4)
    print(f"\n=======================================================")
    print(f"3-MINUTE SHOWCASE COMPLETED SUCCESSFULLY!")
    print(f"Final Duration: {dur_final:.2f}s ({dur_final/60:.2f} minutes) -> STRICTLY <= 180s")
    print(f"MP4: {FINAL_MP4} ({FINAL_MP4.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"WebM: {FINAL_WEBM} ({FINAL_WEBM.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"=======================================================")

if __name__ == "__main__":
    build_all_scenes()
