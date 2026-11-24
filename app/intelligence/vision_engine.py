"""
Screen-Aware Multimodal Vision Engine for Gemini Flow (Vision-Guided Voice).
Captures lightweight active window / screen context at the moment dictation begins,
enabling Gemini 2.5 Flash to 'see' what the user is talking about:
- Fixing code errors shown on screen
- Replying to an open email or chat message
- Filling in forms or writing relative to visible diagrams
"""
import io
import base64
import logging
import ctypes
from ctypes import wintypes, byref, Structure
from typing import Optional, Tuple, Any
from PIL import ImageGrab

logger = logging.getLogger("GeminiFlow.VisionEngine")
user32 = ctypes.windll.user32


class RECT(Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class VisionEngine:
    _vision_mode_active: bool = False

    @classmethod
    def set_vision_mode(cls, active: bool):
        cls._vision_mode_active = bool(active)

    @classmethod
    def set_enabled(cls, active: bool):
        cls._vision_mode_active = bool(active)

    @classmethod
    def is_vision_mode_active(cls, config_manager: Optional[Any] = None) -> bool:
        if config_manager and hasattr(config_manager, "get"):
            return bool(config_manager.get("vision_guided_enabled", cls._vision_mode_active))
        return cls._vision_mode_active

    @classmethod
    def is_enabled(cls, config_manager: Optional[Any] = None) -> bool:
        return cls.is_vision_mode_active(config_manager)

    @classmethod
    def toggle_vision_mode(cls, config_manager: Optional[Any] = None) -> bool:
        new_val = not cls.is_vision_mode_active(config_manager)
        cls._vision_mode_active = new_val
        if config_manager and hasattr(config_manager, "set"):
            config_manager.set("vision_guided_enabled", new_val)
        return new_val

    @staticmethod
    def capture_active_screen(hwnd: Optional[int] = None, max_dim: int = 1280, quality: int = 75) -> Optional[str]:
        """
        Captures the active foreground window (or screen if window is minimized/invalid),
        scales down to max_dim for sub-100ms transfer, and returns base64-encoded JPEG.
        Supports multi-monitor desktop setups including monitors with negative virtual coordinates.
        """
        try:
            bbox = None
            if hwnd:
                rect = RECT()
                if user32.GetWindowRect(hwnd, byref(rect)):
                    # Guard against collapsed or zero-size rects
                    if rect.right > rect.left and rect.bottom > rect.top:
                        bbox = (rect.left, rect.top, rect.right, rect.bottom)

            # Grab image across all monitors (supports negative virtual coordinates)
            if bbox:
                try:
                    img = ImageGrab.grab(bbox=bbox, all_screens=True)
                except Exception:
                    img = ImageGrab.grab(all_screens=True)
            else:
                img = ImageGrab.grab(all_screens=True)

            if img is None:
                return None

            # Downsample to preserve bandwidth and keep payload ~100 KB
            img.thumbnail((max_dim, int(max_dim * 0.75)))

            bio = io.BytesIO()
            img.save(bio, format="JPEG", quality=quality, optimize=True)
            jpeg_bytes = bio.getvalue()

            b64_str = base64.b64encode(jpeg_bytes).decode("utf-8")
            logger.info(f"[VISION ENGINE] Captured screen snippet: {img.size[0]}x{img.size[1]} ({len(jpeg_bytes)} bytes)")
            return b64_str
        except Exception as e:
            logger.warning(f"[VISION ENGINE] Failed to capture active screen: {e}")
            return None
