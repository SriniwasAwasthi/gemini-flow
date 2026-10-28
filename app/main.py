"""
Gemini Flow — AI-Powered Real-Time Voice Dictation Assistant (Wispr Flow Alternative)
Main Application Entrypoint & Coordinator.
"""
import sys
import os
import time
import logging
import threading
import winsound
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List, Callable

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
import pyperclip

MUTEX_NAME = "Global\\GeminiFlow_SingleInstance_Mutex"
IPC_PIPE_NAME = "GeminiFlow_SingleInstance_IPC"
PID_FILE = Path(os.environ.get("APPDATA", Path.home())) / "GeminiFlow" / "gemini_flow.pid"
_mutex_handle = None


def acquire_app_mutex() -> bool:
    """Acquires the global single-instance Named Mutex. Returns True if this is the primary instance."""
    global _mutex_handle
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183
        handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        err = kernel32.GetLastError()
        if err == ERROR_ALREADY_EXISTS:
            if handle:
                kernel32.CloseHandle(handle)
            return False
        _mutex_handle = handle
        return True
    except Exception:
        return True


def release_app_mutex():
    """Releases the global single-instance Named Mutex immediately."""
    global _mutex_handle
    if _mutex_handle:
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(_mutex_handle)
            _mutex_handle = None
            logger.info("Single-instance mutex released successfully.")
        except Exception as e:
            logger.warning(f"Error releasing single instance mutex: {e}")


def get_codebase_last_modified() -> float:
    """Returns the latest modification timestamp of all source python files in the project."""
    try:
        root = Path(__file__).parent.parent
        latest = 0.0
        for p in root.glob("*.py"):
            try:
                m = p.stat().st_mtime
                if m > latest:
                    latest = m
            except Exception:
                pass
        app_dir = root / "app"
        if app_dir.exists():
            for p in app_dir.rglob("*.py"):
                try:
                    m = p.stat().st_mtime
                    if m > latest:
                        latest = m
                except Exception:
                    pass
        return latest
    except Exception:
        return 0.0


def is_dashboard_window_visible() -> bool:
    """Checks whether the Gemini Flow settings/dashboard window is currently visible on screen."""
    try:
        import ctypes
        u32 = ctypes.windll.user32
        for title in (
            "Gemini Flow - Voice AI Settings & Dashboard - Gemini Flow — Voice AI",
            "Gemini Flow — Voice AI Settings & Dashboard - Gemini Flow — Voice AI",
            "Gemini Flow - Voice AI Settings & Dashboard",
            "Gemini Flow — Voice AI Settings & Dashboard"
        ):
            hwnd = u32.FindWindowW(None, title)
            if hwnd and u32.IsWindowVisible(hwnd):
                # Ensure it is restored and brought to top
                SW_RESTORE = 9
                u32.ShowWindow(hwnd, SW_RESTORE)
                u32.SetForegroundWindow(hwnd)
                return True

        # Fallback to EnumWindows to catch any variation in unicode dashes or locale titles
        from ctypes import wintypes
        visible_found = False
        def _enum_win(h, _):
            nonlocal visible_found
            if u32.IsWindowVisible(h):
                length = u32.GetWindowTextLengthW(h)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    u32.GetWindowTextW(h, buf, length + 1)
                    t = buf.value
                    if "Gemini Flow" in t and ("Settings" in t or "Dashboard" in t):
                        u32.ShowWindow(h, 9)
                        u32.SetForegroundWindow(h)
                        visible_found = True
                        return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        u32.EnumWindows(WNDENUMPROC(_enum_win), 0)
        return visible_found
    except Exception:
        pass
    return False


def write_pid_file():
    """Writes current process ID and timestamp to PID file for zombie recovery and update tracking."""
    try:
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(f"{os.getpid()}:{time.time():.2f}")
    except Exception as e:
        logger.debug(f"Could not write PID file: {e}")


def remove_pid_file():
    """Removes PID file on clean shutdown."""
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception:
        pass


def terminate_other_gemini_flow_instances(exclude_pid: int = None):
    """
    Terminates any other running or zombie instance of Gemini Flow / Wisper process (python, pythonw, or exe)
    using Windows taskkill and process enumeration. Ensures no zombie process ever blocks startup or requires PC reboot.
    """
    if exclude_pid is None:
        exclude_pid = os.getpid()

    # 1. Kill via PID file if present
    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                old_pid = int(content.split(":")[0]) if ":" in content else int(content)
            if old_pid != exclude_pid:
                import subprocess
                subprocess.run(["taskkill", "/F", "/PID", str(old_pid)], capture_output=True)
        except Exception:
            pass
        remove_pid_file()

    # 2. Kill only python/pythonw/Gemini Flow processes matching our project (avoid touching powershell/cmd parent shells)
    try:
        import subprocess
        ps_cmd = f"$target = {exclude_pid}; Get-CimInstance Win32_Process | Where-Object {{ ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe' -or $_.Name -like '*Gemini Flow*') -and ($_.CommandLine -like '*main_standalone.py*' -or $_.CommandLine -like '*main.py*' -or $_.CommandLine -like '*Wisper*') -and $_.ProcessId -ne $target }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True, timeout=5)
    except Exception as ex:
        logger.debug(f"Process termination note: {ex}")

    # 3. Clean up stale IPC pipe
    try:
        QLocalServer.removeServer(IPC_PIPE_NAME)
    except Exception:
        pass


def kill_zombie_process_if_any():
    """Kills any stuck or unresponsive background instance."""
    terminate_other_gemini_flow_instances()


def notify_running_instance(command: str = "SHOW") -> bool:
    """Notifies the already running instance to perform an action (e.g. SHOW, RESTART)."""
    try:
        import ctypes
        ASFW_ANY = -1
        ctypes.windll.user32.AllowSetForegroundWindow(ASFW_ANY)
    except Exception:
        pass

    socket = QLocalSocket()
    socket.connectToServer(IPC_PIPE_NAME)
    if socket.waitForConnected(1500):
        socket.write(f"{command}\n".encode("utf-8"))
        socket.waitForBytesWritten(800)
        # Wait for acknowledgment
        if socket.waitForReadyRead(5000):
            socket.readAll()
        socket.disconnectFromServer()
        return True
    return False


def force_window_to_foreground(window):
    """
    Guarantees a PyQt window is un-minimized, restored, and forced to the foreground
    over active apps (Edge, Chrome, Antigravity, etc.) using native Win32 APIs with 64-bit pointer safety.
    """
    if not window:
        return

    # 1. Qt level restore & show
    from PyQt6.QtCore import Qt, QTimer
    window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
    window.showNormal()
    window.show()

    # 2. Win32 Level Foreground Force
    try:
        import ctypes
        from ctypes import c_void_p, c_int, c_uint, c_ulong, byref
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        hwnd = c_void_p(int(window.winId()))

        # Ensure taskbar visibility via WS_EX_APPWINDOW so user can always see and click it
        GWL_EXSTYLE = -20
        WS_EX_APPWINDOW = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080
        get_long = getattr(user32, 'GetWindowLongPtrW', getattr(user32, 'GetWindowLongW', None))
        set_long = getattr(user32, 'SetWindowLongPtrW', getattr(user32, 'SetWindowLongW', None))
        if get_long and set_long:
            get_long.argtypes = [c_void_p, c_int]
            get_long.restype = ctypes.c_ssize_t
            set_long.argtypes = [c_void_p, c_int, ctypes.c_ssize_t]
            set_long.restype = ctypes.c_ssize_t
            cur_style = get_long(hwnd, GWL_EXSTYLE)
            set_long(hwnd, GWL_EXSTYLE, (cur_style | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW)

        # Un-minimize
        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_RESTORE)

        # Simulate Alt key to unlock Windows foreground lock
        VK_MENU = 0x12
        KEYEVENTF_KEYUP = 0x0002
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

        # AttachThreadInput trick to steal foreground lock from active app
        fore_hwnd = c_void_p(user32.GetForegroundWindow())
        cur_thread = kernel32.GetCurrentThreadId()
        fore_pid = c_ulong()
        fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, byref(fore_pid))

        if fore_thread != cur_thread and fore_thread != 0:
            user32.AttachThreadInput(fore_thread, cur_thread, True)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            user32.AttachThreadInput(fore_thread, cur_thread, False)
        else:
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)

        # Set HWND_TOPMOST with 64-bit pointer safety so it pops directly on top of Antigravity / active app
        HWND_TOPMOST = c_void_p(-1)
        HWND_NOTOPMOST = c_void_p(-2)
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        SWP_FRAMECHANGED = 0x0020
        flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW | SWP_FRAMECHANGED
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)

        # After 1200ms, demote HWND_TOPMOST back to normal so it doesn't stay permanently locked on top
        def _demote_topmost():
            try:
                user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED)
            except Exception:
                pass
        QTimer.singleShot(1200, _demote_topmost)

    except Exception as e:
        logger.warning(f"force_window_to_foreground note: {e}")

    window.raise_()
    window.activateWindow()


def is_already_running() -> bool:
    """Legacy compatibility check."""
    return not acquire_app_mutex()

from .config import ConfigManager, ensure_desktop_shortcuts, setup_windows_startup
from .gemini_engine import GeminiEngine
from .vocabulary.vocab_engine import VocabEngine
from .audio_recorder import AudioRecorder
from .text_injector import TextInjector
from .hotkey_manager import HotkeyManager
from .ui.floating_hud import FloatingHUD
from .ui.tray_icon import SystemTrayManager
from .ui.settings_dialog import SettingsDialog
from .intelligence.app_intelligence import AppIntelligenceManager
from .intent.intent_system import IntentClassifier, IntentCategory, INTENT_TO_TRANSFORM_MAP
from .transformation.transform_engine import TransformType, TransformEngine
from .profiles.profile_manager import ProfileManager
from .reliability.fallback_handler import FallbackHandler
from .transcription.engine import UnifiedTranscriptionEngine
from .commands import match_spoken_command, COMMAND_MAP

# Configure logging with bulletproof fallback
import logging.handlers
handlers = []
try:
    log_file = Path(os.environ.get('APPDATA', Path.home())) / 'GeminiFlow' / 'gemini_flow.log'
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handlers.append(logging.handlers.RotatingFileHandler(str(log_file), maxBytes=5 * 1024 * 1024, backupCount=2, encoding='utf-8'))
except Exception:
    try:
        local_log = Path(__file__).parent.parent / 'gemini_flow.log'
        handlers.append(logging.handlers.RotatingFileHandler(str(local_log), maxBytes=5 * 1024 * 1024, backupCount=2, encoding='utf-8'))
    except Exception:
        pass
if sys.stdout is not None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    handlers=handlers
)
logger = logging.getLogger("GeminiFlow.Main")

# Global unhandled exception hooks to ensure 100% crash resilience
def _global_excepthook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("Global Unhandled Exception:", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = _global_excepthook

if hasattr(threading, "excepthook"):
    def _thread_excepthook(args):
        logger.critical(f"Thread Unhandled Exception in {args.thread.name}:", exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
    threading.excepthook = _thread_excepthook


class WorkerSignals(QObject):
    """Signals for background speech processing thread to communicate with Qt UI."""
    finished = pyqtSignal(bool, str, float, str, str, str, str)   # (success, text_or_error, duration, mode, app_name, model_used, raw_text)
    cancelled = pyqtSignal()
    prompt_finished = pyqtSignal(bool, str, str)   # (success, prompt_text, raw_text)
    transform_finished = pyqtSignal(bool, str, str)  # (success, result_text, transform_name)


class GeminiFlowApp:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("Gemini Flow")
        self.app.setApplicationDisplayName("Gemini Flow — Voice AI")

        # Set Windows taskbar AppUserModelID and Window Icon
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('GeminiFlow.VoiceAI.Assistant.1.0')
        except Exception:
            pass

        icon_path = Path(__file__).parent.parent / "app_icon.ico"
        if icon_path.exists():
            from PyQt6.QtGui import QIcon
            self.app.setWindowIcon(QIcon(str(icon_path)))

        # Core components
        self.config = ConfigManager()
        active_model = self.config.get("model_name") or self.config.get("model_mode", "auto")
        self.gemini = GeminiEngine(
            api_key=self.config.get_api_key(),
            model_name=active_model
        )
        self.transcription_engine = UnifiedTranscriptionEngine(
            api_key=self.config.get_api_key(),
            config_manager=self.config
        )
        self.text_injector = TextInjector()
        self.signals = WorkerSignals()
        self.signals.finished.connect(self._on_transcription_finished)
        self.signals.cancelled.connect(self._on_speech_cancelled)
        self.signals.prompt_finished.connect(self._on_prompt_finished)
        self.signals.transform_finished.connect(self._on_transform_finished)

        # UI Components
        self.hud = FloatingHUD(self.config)
        self.tray = SystemTrayManager(self)
        self.settings_dialog = None

        # Audio Recorder with amplitude hook & real-time DSP fan/gate filters
        self.recorder = AudioRecorder(
            sample_rate=16000,
            channels=1,
            on_amplitude=self._on_audio_amplitude,
            config_manager=self.config
        )
        self.recorder.set_device(self.config.get("input_device_index"))

        # Global Hotkey Manager
        self.hotkey_mgr = HotkeyManager(
            hotkey_str=self.config.get("hotkey", "<ctrl>+<space>"),
            mode=self.config.get("hotkey_mode", "toggle"),
            prompt_hotkey_str=self.config.get("prompt_hotkey", "<ctrl>+<shift>+p"),
            transform_hotkey_str=self.config.get("transform_hotkey", "<ctrl>+<shift>+t"),
            on_start=self.on_start_speech,
            on_stop=self.on_stop_speech,
            on_cancel=self.on_cancel_speech,
            on_prompt=self.on_prompt_hotkey,
            on_transform=self.on_transform_hotkey
        )

        # Single Instance IPC Server
        self.server = QLocalServer(self.app)
        QLocalServer.removeServer(IPC_PIPE_NAME)
        self.server.newConnection.connect(self._on_ipc_connection)
        if not self.server.listen(IPC_PIPE_NAME):
            logger.warning(f"QLocalServer listen retry needed on '{IPC_PIPE_NAME}': {self.server.errorString()}")
            QLocalServer.removeServer(IPC_PIPE_NAME)
            self.server.listen(IPC_PIPE_NAME)

        # Standby / Sleep / Inactivity Watchdog Timer (fires every 5 seconds)
        from PyQt6.QtCore import QTimer
        self._last_watchdog_time = time.time()
        self.watchdog_timer = QTimer(self.app)
        self.watchdog_timer.timeout.connect(self._on_watchdog_tick)
        self.watchdog_timer.start(5000)

        self.is_busy_processing = False
        self._busy_start_time = 0.0
        self._last_saved_audio_path: str = ""
        self._is_cancelled = False
        self._rolling_chunks = []
        self._rolling_lock = threading.Lock()
        self._rolling_active = False
        self._startup_code_mtime = get_codebase_last_modified()

        # Asynchronous zero-delay background warmup (Pre-warms Gemini TLS Keep-Alive, PortAudio mic stack, Whisper offline weights, Windows startup)
        def _async_startup_warmup():
            try:
                self.gemini.warm_connection()
                self.recorder.warmup_audio()
                # Unconditional Whisper pre-warmup in background daemon thread for 0ms cold-start latency
                try:
                    from app.offline.offline_engine import OfflineSpeechEngine
                    OfflineSpeechEngine.warmup_whisper()
                except Exception as w_err:
                    logger.debug(f"Whisper warmup note: {w_err}")
                if self.config.get("start_with_windows", True):
                    setup_windows_startup(True)
                ensure_desktop_shortcuts()
            except Exception as ex:
                logger.debug(f"Async startup warmup note: {ex}")

        threading.Thread(target=_async_startup_warmup, daemon=True, name="AppStartupWarmup").start()
        QTimer.singleShot(1500, self._lazy_preinit_settings)

    def _lazy_preinit_settings(self):
        """Silently instantiates SettingsDialog on the main thread during idle for instant opening."""
        if getattr(self, 'settings_dialog', None) is None:
            try:
                self.settings_dialog = SettingsDialog(self.config, self.gemini, self.text_injector, main_app=self)
                self.settings_dialog.settings_applied.connect(self._on_settings_applied)
                self.settings_dialog.finished.connect(self._on_settings_closed)
            except Exception as e:
                logger.debug(f"Lazy pre-init settings note: {e}")

    def _on_audio_amplitude(self, amp: float):
        if self.recorder.is_recording:
            self.hud.update_volume(amp)

    def on_start_speech(self):
        """Triggered globally when user presses hotkey to speak."""
        if self.is_busy_processing:
            # Auto-recovery: If busy for > 12 seconds, forcefully reset and allow user to dictate immediately
            busy_duration = time.time() - getattr(self, '_busy_start_time', 0.0) if getattr(self, '_busy_start_time', 0.0) > 0 else 999.0
            if busy_duration > 12.0:
                logger.warning(f"Previous processing took too long ({busy_duration:.1f}s). Force-resetting busy state to accept new speech.")
                self.is_busy_processing = False
                self._busy_start_time = 0.0
                self.hotkey_mgr.set_processing_state(False)
            else:
                logger.warning("Still processing previous speech, ignoring new start.")
                self.hotkey_mgr.set_recording_state(False)
                if hasattr(self, 'hud') and self.hud:
                    self.hud.show_state(FloatingHUD.STATE_PROCESSING, "Finalizing previous speech...")
                return

        self._is_cancelled = False
        with self._rolling_lock:
            self._rolling_chunks = []
        self._rolling_active = True
        self.hotkey_mgr.set_recording_state(True)

        # 1. Capture active foreground window and any highlighted text for command triggers
        self.text_injector.capture_active_window()
        self._pre_recorded_selected_text = ""
        try:
            sel = self.text_injector.get_selected_text(require_selection=True)
            if sel and len(sel.strip()) >= 2:
                self._pre_recorded_selected_text = sel.strip()
        except Exception:
            pass

        # 2. Audio feedback (subtle high beep)
        if self.config.get("play_sounds", True):
            try:
                winsound.Beep(750, 60)
            except Exception:
                pass

        # 3. Start Recording
        device_idx = self.config.get("input_device_index")
        self.recorder.set_device(device_idx)
        success = self.recorder.start_recording()

        if success:
            self.hud.show_state(FloatingHUD.STATE_LISTENING, "")
            self.tray.update_status("🎙️ Recording Speech...", state="recording")
            self._start_rolling_transcription()
        else:
            self.hotkey_mgr.set_recording_state(False)
            self.hud.show_state(FloatingHUD.STATE_ERROR, "Microphone Error")
            self.tray.update_status("⚠️ Mic Error", state="ready")

    def _start_rolling_transcription(self):
        """Asynchronously slices and transcribes 25-38s chunks in real-time during long recordings."""
        def _rolling_loop():
            chunk_idx = 0
            while self.recorder.is_recording and not self._is_cancelled and self._rolling_active:
                time.sleep(0.15)
                if not self.recorder.is_recording or self._is_cancelled or not self._rolling_active:
                    break

                chunk_wav = self.recorder.get_rolling_chunk(min_sec=30.0, max_sec=45.0)
                if chunk_wav and len(chunk_wav) > 2000:
                    curr_idx = chunk_idx
                    chunk_idx += 1
                    with self._rolling_lock:
                        self._rolling_chunks.append({
                            "id": curr_idx,
                            "done": False,
                            "text": "",
                            "wav": chunk_wav
                        })

                    target_hwnd = getattr(self.text_injector, "last_target_hwnd", None)
                    app_context = AppIntelligenceManager.get_active_app_context(target_hwnd)
                    user_profile = self.config.get("active_profile")
                    active_profile = user_profile if user_profile else (app_context.profile_id if (app_context and app_context.profile_id) else "coding")
                    active_mode = self.config.get("mode_preset", "clean_dictation")
                    prompt = self.config.get_system_prompt(preset_override=active_mode, app_context=app_context, profile_id_override=active_profile)
                    auto_cost_mode = self.config.get("auto_cost_mode", True)
                    offline_fallback_on = self.config.get_offline_fallback_enabled() if hasattr(self.config, "get_offline_fallback_enabled") else self.config.get("offline_fallback_enabled", True)

                    primary_lang = self.config.get_primary_language_code() if hasattr(self.config, 'get_primary_language_code') else None

                    def _transcribe_slice(c_idx, c_bytes):
                        ok = False
                        txt = ""
                        try:
                            ok, txt = self.gemini.transcribe_audio(
                                wav_bytes=c_bytes,
                                system_instruction=prompt,
                                app_context=app_context,
                                profile_id=active_profile,
                                auto_cost_mode=auto_cost_mode,
                                offline_fallback_enabled=offline_fallback_on,
                                offline_language=primary_lang
                            )
                        except Exception as ex:
                            logger.debug(f"Rolling slice {c_idx} online error: {ex}")
                            ok = False

                        # Immediate local offline Whisper rescue if online transcription failed or returned empty
                        if (not ok or not txt or not txt.strip()) and offline_fallback_on:
                            try:
                                from app.offline.offline_engine import OfflineSpeechEngine
                                ok_off, txt_off = OfflineSpeechEngine.transcribe_wav(c_bytes, language=primary_lang)
                                if ok_off and txt_off and txt_off.strip():
                                    ok, txt = True, txt_off
                            except Exception as off_ex:
                                logger.debug(f"Rolling slice {c_idx} offline fallback error: {off_ex}")

                        with self._rolling_lock:
                            if c_idx < len(self._rolling_chunks):
                                self._rolling_chunks[c_idx]["text"] = txt.strip() if (ok and txt) else ""
                                self._rolling_chunks[c_idx]["done"] = True
                                if ok and txt:
                                    self._rolling_chunks[c_idx]["wav"] = None

                    threading.Thread(target=_transcribe_slice, args=(curr_idx, chunk_wav), daemon=True).start()

        threading.Thread(target=_rolling_loop, daemon=True, name="RollingAudioMonitor").start()

    def on_stop_speech(self):
        """Triggered globally when user stops hotkey."""
        if not self.recorder.is_recording:
            return

        self._rolling_active = False
        self.hotkey_mgr.set_recording_state(False)

        # 1. Stop audio capture & save complete playable recording to disk
        wav_path, wav_bytes, duration, sample_count, rms = self.recorder.stop_recording()
        self._last_saved_audio_path = wav_path or ConfigManager.save_recorded_audio(wav_bytes)

        if self._is_cancelled:
            logger.info("Speech was cancelled, discarding audio.")
            return

        # 2. Audio feedback (subtle descending beep)
        if self.config.get("play_sounds", True):
            try:
                winsound.Beep(520, 60)
            except Exception:
                pass

        # Ignore if speech was under 0.3s or empty (only when no background rolling chunks were emitted)
        has_rolling = self.recorder.rolling_chunks_were_emitted()
        if duration < 0.3 or (not has_rolling and (not wav_bytes or len(wav_bytes) < 1000)):
            logger.info(f"Speech too brief or empty (duration: {duration:.2f}s, rolling: {has_rolling}), ignoring.")
            self.hud.hide_smooth()
            self.tray.update_status("🟢 Ready", state="ready")
            return

        # 3. Update UI to processing state
        self.is_busy_processing = True
        self._busy_start_time = time.time()
        self.hotkey_mgr.set_processing_state(True)
        self.hud.show_state(FloatingHUD.STATE_PROCESSING, "Refining with Gemini...")
        self.tray.update_status("⚡ Processing with Gemini...", state="processing")

        # 4. Dispatch background AI worker thread
        threading.Thread(
            target=self._process_speech_worker,
            args=(self._last_saved_audio_path, wav_bytes, duration),
            daemon=True
        ).start()

    def on_cancel_speech(self):
        """Triggered globally when Escape is pressed during recording or processing."""
        logger.info("Cancelling speech session...")
        self._is_cancelled = True
        self._rolling_active = False
        with self._rolling_lock:
            self._rolling_chunks = []
        self.is_busy_processing = False
        self._busy_start_time = 0.0
        self.hotkey_mgr.set_recording_state(False)
        self.hotkey_mgr.set_processing_state(False)

        if self.recorder.is_recording:
            self.recorder.stop_recording()

        self.signals.cancelled.emit()

    def _on_speech_cancelled(self):
        """UI Thread handler for speech cancellation."""
        self.hotkey_mgr.reset_keys()
        if self.config.get("play_sounds", True):
            try:
                winsound.Beep(350, 70)
            except Exception:
                pass
        self.hud.show_state(FloatingHUD.STATE_CANCELLED, "Speech Cancelled 🚫")
        self.tray.update_status("🟢 Ready", state="ready")

    def on_prompt_hotkey(self):
        """Triggered globally when user presses Alt + P to enhance highlighted text into a structured AI Prompt."""
        if self.is_busy_processing:
            return

        time.sleep(0.06)
        self.text_injector.capture_active_window()

        # 1. Strictly capture highlighted / selected text on screen
        raw_text = self.text_injector.get_selected_text(require_selection=True)

        # 2. If nothing is selected on screen, alert user immediately - do NOT use stale clipboard data!
        if not raw_text or len(raw_text.strip()) < 2:
            logger.info("No text selected on screen for prompt enhancement.")
            self.hud.show_state(FloatingHUD.STATE_ERROR, "Select Text First!")
            return

        self.is_busy_processing = True
        self.hotkey_mgr.set_processing_state(True)
        self.hud.show_state(FloatingHUD.STATE_PROMPT, "✨ Crafting AI Prompt with Gemini...")
        self.tray.update_status("✨ Enhancing AI Prompt...", state="processing")

        def _enhance_worker():
            success, result_prompt = self.gemini.enhance_to_ai_prompt(raw_text)
            self.signals.prompt_finished.emit(success, result_prompt, raw_text)

        threading.Thread(target=_enhance_worker, daemon=True).start()

    def _on_prompt_finished(self, success: bool, prompt_or_error: str, raw_text: str = ""):
        self.is_busy_processing = False
        self.hotkey_mgr.set_processing_state(False)

        if success and prompt_or_error:
            # Save both AI prompt and raw text to history
            app_name = self.text_injector.get_target_app_name()
            model = self.gemini.last_model_used or self.config.get("model_name", "gemini-2.5-flash")
            self.config.add_history_entry(
                text=prompt_or_error,
                duration_sec=1.0,
                mode="prompt_enhancer",
                app_name=app_name,
                model=model,
                raw_text=raw_text or prompt_or_error,
                prompt=prompt_or_error
            )
            if self.settings_dialog and self.settings_dialog.isVisible():
                self.settings_dialog.notify_history_changed()

            # Always copy the enhanced AI Prompt into clipboard so user can paste it anywhere
            try:
                pyperclip.copy(prompt_or_error)
            except Exception:
                pass

            if self.config.get("auto_paste", True):
                paste_ok = self.text_injector.paste_text(prompt_or_error)
                if paste_ok:
                    self.hud.show_state(FloatingHUD.STATE_PASTED, "✨ AI Prompt Pasted & Copied! 📋")
                else:
                    self.hud.show_state(FloatingHUD.STATE_COPIED, "✨ AI Prompt Copied to Clipboard 📋")
            else:
                self.hud.show_state(FloatingHUD.STATE_COPIED, "✨ AI Prompt Copied to Clipboard 📋")

            disp_name = self.config.get("hotkey_display", "Ctrl + Space")
            self.tray.update_status(f"🟢 Ready ({disp_name})", state="ready")
        else:
            self.hud.show_state(FloatingHUD.STATE_ERROR, prompt_or_error[:35] if prompt_or_error else "Prompt Failed")
            self.tray.update_status("⚠️ Prompt Enhancement Failed", state="ready")

    def on_transform_hotkey(self):
        """Triggered globally when user presses Ctrl + Shift + T to transform selected text anywhere on Windows."""
        if self.is_busy_processing:
            return

        # Give physical key release a moment to settle
        time.sleep(0.06)
        self.text_injector.capture_active_window()
        selected_text = self.text_injector.get_selected_text()

        if not selected_text or len(selected_text.strip()) < 2:
            logger.info("No text selected for transformation.")
            self.hud.show_state(FloatingHUD.STATE_ERROR, "Select Text First!")
            return

        self.is_busy_processing = True
        self.hotkey_mgr.set_processing_state(True)
        self.hud.show_state(FloatingHUD.STATE_PROCESSING, "✨ Transforming text with Gemini...")
        self.tray.update_status("✨ Transforming text...", state="processing")

        app_context = AppIntelligenceManager.get_active_app_context()
        active_profile = self.config.get("active_profile", "coding")

        def _transform_worker():
            exec_res = self.gemini.transform_text(
                raw_text=selected_text,
                transform_type=TransformType.IMPROVE,
                app_context=app_context,
                profile_id=active_profile
            )
            self.signals.transform_finished.emit(
                exec_res.success,
                exec_res.text if exec_res.success else exec_res.error_message,
                "Improve Writing"
            )

        threading.Thread(target=_transform_worker, daemon=True).start()

    def _on_transform_finished(self, success: bool, text_or_error: str, transform_name: str):
        self.is_busy_processing = False
        self.hotkey_mgr.set_processing_state(False)

        if success and text_or_error:
            # Save to history
            app_name = self.text_injector.get_target_app_name()
            model = self.gemini.last_model_used or self.config.get("model_name", "gemini-2.5-flash")
            self.config.add_history_entry(text_or_error, 1.0, f"Transform: {transform_name}", app_name=app_name, model=model)
            if self.settings_dialog and self.settings_dialog.isVisible():
                self.settings_dialog.notify_history_changed()

            # Auto-paste into active app
            if self.config.get("auto_paste", True):
                paste_ok = self.text_injector.paste_text(text_or_error)
                if paste_ok:
                    self.hud.show_state(FloatingHUD.STATE_PASTED, "Transformed & Pasted! ✨")
                else:
                    self.hud.show_state(FloatingHUD.STATE_COPIED, "Copied to Clipboard!")
            else:
                pyperclip.copy(text_or_error)
                self.hud.show_state(FloatingHUD.STATE_COPIED, "Copied to Clipboard!")

            disp_name = self.config.get("hotkey_display", "Ctrl + Win")
            self.tray.update_status(f"🟢 Ready ({disp_name})", state="ready")
        else:
            self.hud.show_state(FloatingHUD.STATE_ERROR, text_or_error[:35] if text_or_error else "Transform Failed")
            self.tray.update_status("⚠️ Transform Failed", state="ready")

    def _process_speech_worker(self, wav_target: any, wav_bytes: bytes, duration: float):
        """
        Unified Speech Processing Worker for Gemini Flow.
        Guarantees:
        - G1: Zero truncation for any speech duration.
        - G2: High-fidelity transcription with grammar and punctuation.
        - G3: Zero hallucination, dictation is data never instructions.
        - G4: Strict first-words-only matching for all 16 command categories.
        """
        try:
            if self._is_cancelled:
                return

            # 1. Resolve Application Context
            target_hwnd = getattr(self.text_injector, "last_target_hwnd", None)
            app_context = AppIntelligenceManager.get_active_app_context(target_hwnd)
            app_name = app_context.app_name if app_context else self.text_injector.get_target_app_name()

            active_profile = self.config.get("active_profile", "coding")
            active_mode = self.config.get("mode_preset", "clean_dictation")
            active_model = self.config.get("model_name") or self.config.get("model_mode", "gemini-2.5-flash")
            primary_lang = self.config.get_primary_language_code() if hasattr(self.config, 'get_primary_language_code') else "en"

            # 2. Fast Acoustic Silence Check
            if duration <= 0.1 or not AudioRecorder.contains_speech(wav_bytes):
                logger.info(f"Acoustic check: Audio contains zero speech energy ({duration:.2f}s). Skipping AI call.")
                self.signals.finished.emit(True, "", duration, active_mode, app_name, active_model, "")
                return

            # 3. Transcribe via Unified Transcription Engine
            api_key = self.config.get_api_key()
            self.transcription_engine.set_api_key(api_key)

            logger.info(f"Initiating Unified Transcription for {duration:.2f}s audio with model '{active_model}' (Lang: '{primary_lang}')...")
            transcript = self.transcription_engine.transcribe(
                wav_path_or_bytes=wav_target if (isinstance(wav_target, str) and os.path.exists(wav_target)) else wav_bytes,
                model_name=active_model,
                language=primary_lang
            )

            # Resilient offline fallback if online model failed
            offline_fallback_on = self.config.get_offline_fallback_enabled() if hasattr(self.config, "get_offline_fallback_enabled") else self.config.get("offline_fallback_enabled", True)
            if not transcript.success and offline_fallback_on and "offline" not in active_model.lower():
                logger.warning(f"Online model '{active_model}' failed ({transcript.error_message}). Rescuing with offline Whisper...")
                self.hud.show_state(FloatingHUD.STATE_PROCESSING, "Offline Rescue...")
                transcript = self.transcription_engine.transcribe(
                    wav_path_or_bytes=wav_target if (isinstance(wav_target, str) and os.path.exists(wav_target)) else wav_bytes,
                    model_name="offline-whisper",
                    language=primary_lang
                )

            if not transcript.success:
                logger.error(f"Transcription failed: {transcript.error_message}")
                self.signals.finished.emit(False, transcript.error_message or "Transcription failed.", duration, active_mode, app_name, active_model, "")
                return

            raw_result = transcript.text.strip()
            if not raw_result:
                logger.info("Speech transcription returned empty text.")
                self.signals.finished.emit(True, "", duration, active_mode, app_name, transcript.model, "")
                return

            # 4. Voice Intent & Command Routing (All 16 Profile Categories)
            clipboard_text = getattr(self, "_pre_recorded_selected_text", "") or ""
            if not clipboard_text:
                try:
                    clipboard_text = self.text_injector.get_selected_text() or pyperclip.paste() or ""
                except Exception:
                    pass

            matched_cmd_info = match_spoken_command(raw_result, selected_text=clipboard_text)
            if matched_cmd_info is not None:
                matched_cmd, cmd_payload = matched_cmd_info
                logger.info(f"Voice Command Triggered: {matched_cmd.name} (Trigger: first words matched, Payload: '{cmd_payload[:60]}...')")
                self.hud.show_state(FloatingHUD.STATE_PROCESSING, f"⚡ Command: {matched_cmd.name}...")

                cmd_success, cmd_output = self._execute_voice_command(matched_cmd, cmd_payload, app_context)
                if cmd_success and cmd_output:
                    cmd_output = GeminiEngine.apply_dictionary(cmd_output, self.config.get_dictionary())
                    self.signals.finished.emit(True, cmd_output, duration, f"Command: {matched_cmd.name}", app_name, transcript.model, raw_result)
                    return
                else:
                    logger.warning(f"Voice command execution failed ({cmd_output}). Continuing with clean dictation.")

            # 5. Post-Processing Pipeline & Hard Fidelity Gate (Phase 3)
            from app.intelligence.post_processing import post_process_transcript
            polish_enabled = self.config.get("grammar_polish", True)
            voice_punct = self.config.get("voice_punctuation", True)
            remove_fillers = self.config.get("remove_fillers", False)

            polish_fn = self._get_llm_polish_fn(active_model)
            final_text = post_process_transcript(
                raw_text=raw_result,
                grammar_polish_enabled=polish_enabled,
                polish_fn=polish_fn,
                voice_punctuation=voice_punct,
                remove_fillers=remove_fillers
            )

            final_text = GeminiEngine.apply_dictionary(final_text, self.config.get_dictionary())
            final_text = GeminiEngine.apply_snippets(final_text, self.config.get_snippets())

            logger.info(f"[DIAGNOSTIC] Capture={duration:.2f}s, Raw='{raw_result}', Final='{final_text}' (Model={transcript.model})")
            self.signals.finished.emit(True, final_text, duration, active_mode, app_name, transcript.model, raw_result)

        except Exception as e:
            logger.error(f"Error in speech processing worker: {e}", exc_info=True)
            self.signals.finished.emit(False, f"Error: {str(e)}", duration, "clean_dictation", "General", "gemini-2.5-flash", "")

    def _execute_voice_command(self, cmd, payload: str, app_context=None) -> Tuple[bool, str]:
        """Executes a validated command via the centralized command executor."""
        from app.commands import execute_command
        active_model = self.config.get("model_name") or "gemini-2.5-flash"

        def _llm_fn(sys_prompt: str, user_content: str, temp: float, max_tok: int) -> str:
            if "ollama" in active_model.lower() or "gemma" in active_model.lower():
                from app.intelligence.ollama_engine import OllamaEngine
                full_prompt = f"{sys_prompt}\n\nUSER INPUT:\n{user_content}"
                ok, txt = OllamaEngine.polish_text(raw_text=user_content, prompt_override=full_prompt)
                if ok and txt:
                    return txt
                raise RuntimeError("Ollama local command execution failed.")
            elif "offline" in active_model.lower() or "whisper" in active_model.lower():
                from app.intelligence.ollama_engine import OllamaEngine
                if OllamaEngine.is_available():
                    full_prompt = f"{sys_prompt}\n\nUSER INPUT:\n{user_content}"
                    ok, txt = OllamaEngine.polish_text(raw_text=user_content, prompt_override=full_prompt)
                    if ok and txt:
                        return txt
                return user_content
            else:
                api_key = self.config.get_api_key()
                if not api_key:
                    raise RuntimeError("Gemini API key missing.")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent"
                payload_data = {
                    "contents": [{"parts": [{"text": f"{sys_prompt}\n\nUSER INPUT:\n{user_content}"}]}],
                    "generationConfig": {"temperature": temp, "maxOutputTokens": max_tok}
                }
                res = self.gemini.session.post(
                    url,
                    headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                    json=payload_data,
                    timeout=(4.0, 20.0)
                )
                if res.status_code == 200:
                    data = res.json()
                    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    txt = "".join([p.get("text", "") for p in parts])
                    return txt.strip()
                raise RuntimeError(f"Gemini API returned status {res.status_code}")

        return execute_command(cmd, payload, _llm_fn)

    def _get_llm_polish_fn(self, active_model: str):
        """Returns the LLM copy-editor function for the active model."""
        if "offline" in active_model.lower() or "whisper" in active_model.lower():
            from app.intelligence.ollama_engine import OllamaEngine
            if OllamaEngine.is_available():
                return lambda raw_chunk, prompt: OllamaEngine.polish_text(raw_text=raw_chunk, prompt_override=prompt)
            return None
        elif "ollama" in active_model.lower() or "gemma" in active_model.lower():
            from app.intelligence.ollama_engine import OllamaEngine
            return lambda raw_chunk, prompt: OllamaEngine.polish_text(raw_text=raw_chunk, prompt_override=prompt)
        else:
            api_key = self.config.get_api_key()
            if not api_key:
                return None
            def _gemini_polish(raw_chunk: str, prompt: str) -> Tuple[bool, str]:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent"
                payload_data = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 2048}
                }
                try:
                    res = self.gemini.session.post(
                        url,
                        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                        json=payload_data,
                        timeout=(4.0, 10.0)
                    )
                    if res.status_code == 200:
                        data = res.json()
                        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                        return True, "".join([p.get("text", "") for p in parts]).strip()
                except Exception as e:
                    logger.debug(f"Gemini polish request note: {e}")
                return False, ""
            return _gemini_polish

    def retranscribe_last_recording(self):
        """Re-transcribes the most recent audio recording on demand."""
        target_path = getattr(self, "_last_saved_audio_path", "")
        if not target_path or not os.path.exists(target_path):
            orphaned = AudioRecorder.get_orphaned_recordings()
            if orphaned:
                target_path = str(orphaned[0])
                self._last_saved_audio_path = target_path

        if not target_path or not os.path.exists(target_path):
            if hasattr(self, "hud") and self.hud:
                self.hud.show_state(FloatingHUD.STATE_ERROR, "No Recording Found")
            return

        try:
            with open(target_path, "rb") as f:
                wav_bytes = f.read()
            from app.transcription.chunker import get_audio_info
            duration, _, _, _ = get_audio_info(wav_bytes)

            self.is_busy_processing = True
            self._busy_start_time = time.time()
            if hasattr(self, "hud") and self.hud:
                self.hud.show_state(FloatingHUD.STATE_PROCESSING, "Re-transcribing last audio...")
            if hasattr(self, "tray") and self.tray:
                self.tray.update_status("⚡ Re-transcribing...", state="processing")

            threading.Thread(
                target=self._process_speech_worker,
                args=(target_path, wav_bytes, duration),
                daemon=True
            ).start()
        except Exception as ex:
            logger.error(f"Failed to re-transcribe last recording: {ex}")
            if hasattr(self, "hud") and self.hud:
                self.hud.show_state(FloatingHUD.STATE_ERROR, "Re-transcribe Failed")

    def _on_transcription_finished(
        self,
        success: bool,
        text_or_error: str,
        duration: float,
        mode: str = "clean_dictation",
        app_name: str = "General",
        model_used: str = "gemini-2.5-flash",
        raw_spoken_text: str = ""
    ):
        """Back on main Qt UI thread."""
        self.is_busy_processing = False
        self._busy_start_time = 0.0
        self.hotkey_mgr.set_processing_state(False)
        self.hotkey_mgr.reset_keys()

        if self._is_cancelled:
            return

        disp_name = self.config.get("hotkey_display", "Ctrl + Space")

        # Handle clean silence (no words spoken)
        if success and not text_or_error:
            logger.info("No speech detected in audio.")
            self.hud.show_state(FloatingHUD.STATE_READY, "No Audio Detected 🎙️")
            self.tray.update_status(f"🟢 Ready ({disp_name})", state="ready")
            return

        if success and text_or_error:
            logger.info(f"Final Processed Text [{mode}]: {text_or_error[:100]}...")

            # 1. Zero-Loss Emergency File Backup:
            # Write immediately to last_transcription.txt so user speech can NEVER be lost
            try:
                rescue_path = Path(os.environ.get("APPDATA", Path.home())) / "GeminiFlow" / "last_transcription.txt"
                with open(rescue_path, "w", encoding="utf-8") as rf:
                    rf.write(f"=== Last Dictation ({time.strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
                    rf.write(f"Target App: {app_name} | Mode: {mode} | Model: {model_used} | Duration: {duration:.1f}s\n\n")
                    rf.write(text_or_error)
            except Exception as res_err:
                logger.debug(f"Rescue file backup note: {res_err}")

            # 2. Persistent History Logging:
            # Maintain persistent log storing both the generated prompt and the raw transcription
            self.config.add_history_entry(
                text=text_or_error,
                duration_sec=duration,
                mode=mode,
                app_name=app_name,
                model=model_used,
                raw_text=raw_spoken_text or text_or_error,
                prompt=text_or_error if mode == "prompt_generation" else "",
                audio_path=getattr(self, "_last_saved_audio_path", "")
            )
            if self.settings_dialog and self.settings_dialog.isVisible():
                self.settings_dialog.notify_history_changed()
                active_prof = self.config.get("active_profile", "coding")
                self.settings_dialog.sync_active_profile(active_prof)

            # 3. AI Prompt Pasting, Voice Command Pasting & Normal Speech Clipboard Management:
            is_prompt_mode = (mode == "prompt_generation" and raw_spoken_text and raw_spoken_text.strip() != text_or_error.strip())
            is_command_mode = mode.startswith("Command:")
            is_offline_mode = "offline" in (model_used or "").lower()

            if self.config.get("auto_paste", True):
                if is_prompt_mode:
                    paste_ok = self.text_injector.paste_text(text_or_error, leave_in_clipboard=raw_spoken_text)
                    if paste_ok:
                        self.hud.show_state(FloatingHUD.STATE_PASTED, "AI Prompt Pasted! (Speech in Clipboard 📋)")
                    else:
                        pyperclip.copy(raw_spoken_text)
                        self.hud.show_state(FloatingHUD.STATE_COPIED, "Normal Speech Copied (Backup) 📋")
                elif is_command_mode:
                    paste_ok = self.text_injector.paste_text(text_or_error, leave_in_clipboard=raw_spoken_text if raw_spoken_text else None)
                    cmd_name = mode.replace("Command:", "").strip()
                    if paste_ok:
                        self.hud.show_state(FloatingHUD.STATE_PASTED, f"{cmd_name} Pasted! ✨")
                    else:
                        if raw_spoken_text:
                            pyperclip.copy(raw_spoken_text)
                        self.hud.show_state(FloatingHUD.STATE_COPIED, f"{cmd_name} Copied! 📋")
                elif is_offline_mode:
                    paste_ok = self.text_injector.paste_text(text_or_error)
                    if paste_ok:
                        self.hud.show_state(FloatingHUD.STATE_OFFLINE, "Offline Dictation Pasted! 🎙️")
                    else:
                        self.hud.show_state(FloatingHUD.STATE_COPIED, "Copied (Offline Mode) 📋")
                else:
                    paste_ok = self.text_injector.paste_text(text_or_error)
                    if paste_ok:
                        self.hud.show_state(FloatingHUD.STATE_PASTED, "Pasted!")
                    else:
                        self.hud.show_state(FloatingHUD.STATE_COPIED, "Copied to Clipboard!")
            else:
                if is_prompt_mode:
                    try:
                        pyperclip.copy(text_or_error)
                        time.sleep(0.08)
                        pyperclip.copy(raw_spoken_text)
                    except Exception:
                        pyperclip.copy(raw_spoken_text)
                    self.hud.show_state(FloatingHUD.STATE_COPIED, "Normal Speech Copied (Backup) 📋")
                elif is_command_mode:
                    cmd_name = mode.replace("Command:", "").strip()
                    pyperclip.copy(text_or_error)
                    self.hud.show_state(FloatingHUD.STATE_COPIED, f"{cmd_name} Copied! 📋")
                elif is_offline_mode:
                    pyperclip.copy(text_or_error)
                    self.hud.show_state(FloatingHUD.STATE_OFFLINE, "Offline Speech Copied! 🎙️")
                else:
                    pyperclip.copy(text_or_error)
                    self.hud.show_state(FloatingHUD.STATE_COPIED, "Copied to Clipboard!")

            self.tray.update_status(f"🟢 Ready ({disp_name})", state="ready")

        else:
            logger.warning(f"Transcription failed: {text_or_error}")
            self.hud.show_state(FloatingHUD.STATE_ERROR, text_or_error[:35])
            self.tray.update_status("⚠️ Transcription Failed", state="ready")

    def _on_watchdog_tick(self):
        """Monitors system sleep/resume, keyboard listener health, and recording safety limit."""
        try:
            now = time.time()
            # 1. Detect if laptop was suspended/asleep or clock jumped (interval exceeds 12s)
            if hasattr(self, '_last_watchdog_time') and (now - self._last_watchdog_time > 12.0):
                logger.info("System resumed from sleep or standby. Reinitializing keyboard listener and warming up sockets...")
                self.hotkey_mgr.restart()
                self.hotkey_mgr.reset_keys()
                if hasattr(self, 'gemini') and self.gemini:
                    self.gemini.warm_connection()
                if hasattr(self, 'recorder') and self.recorder:
                    threading.Thread(target=self.recorder.warmup_audio, daemon=True, name="AudioWarmupWake").start()
            else:
                self.hotkey_mgr.check_health()
            self._last_watchdog_time = now

            # Watchdog Processing Recovery: If speech processing is stuck for > 20s, release UI lock
            if self.is_busy_processing:
                b_dur = time.time() - getattr(self, '_busy_start_time', 0.0) if getattr(self, '_busy_start_time', 0.0) > 0 else 999.0
                if b_dur > 20.0:
                    logger.warning(f"Watchdog: speech processing stuck for {b_dur:.1f}s. Resetting state.")
                    self.is_busy_processing = False
                    self._busy_start_time = 0.0
                    self.hotkey_mgr.set_processing_state(False)
                    self.hotkey_mgr.reset_keys()
                    if hasattr(self, 'hud') and self.hud:
                        self.hud.show_state(FloatingHUD.STATE_READY, "Gemini Flow Ready")
                    self.tray.update_status("Ready", state="ready")

            # 2. Maximum recording duration safety net (supports 4+ hours continuous marathon dictation)
            max_recording_limit = float(self.config.get("max_recording_seconds", 14400.0))
            if hasattr(self, 'recorder') and self.recorder and self.recorder.is_recording:
                elapsed = time.time() - self.recorder.start_time
                if elapsed > max_recording_limit:
                    logger.warning(f"Recording reached maximum safety limit ({elapsed:.1f}s / {max_recording_limit:.0f}s). Auto-stopping.")
                    self.on_stop_speech()

            # Codebase mtime auto-reload intentionally removed: OneDrive background synchronization
            # touches file timestamps overnight, which previously triggered false-positive restarts.
        except Exception as e:
            logger.debug(f"Watchdog tick note: {e}")

    def _on_ipc_connection(self):
        """Called when another instance launches and pings this running instance."""
        try:
            client = self.server.nextPendingConnection()
            if client:
                if client.bytesAvailable() > 0 or client.waitForReadyRead(800):
                    data = client.readAll().data().decode("utf-8", errors="ignore")
                    if "RESTART" in data:
                        logger.info("IPC: Received RESTART request. Restarting application instance...")
                        try:
                            client.write(b"OK\n")
                            client.flush()
                        except Exception:
                            pass
                        client.disconnectFromServer()
                        self.restart_app()
                        return
                    elif "SHOW" in data:
                        logger.info("IPC: Received SHOW request from another instance. Forcing dashboard to front.")
                        self.open_settings()
                        if hasattr(self, 'hud') and self.hud:
                            self.hud.show_state(FloatingHUD.STATE_READY, "Gemini Flow — Voice AI Ready 🎙️")
                        try:
                            client.write(b"OK\n")
                            client.flush()
                        except Exception:
                            pass
                client.disconnectFromServer()
        except Exception as e:
            logger.error(f"Error handling IPC connection: {e}")

    def open_settings(self):
        if not self.settings_dialog:
            self.settings_dialog = SettingsDialog(self.config, self.gemini, self.text_injector, main_app=self)
            self.settings_dialog.settings_applied.connect(self._on_settings_applied)
            self.settings_dialog.finished.connect(self._on_settings_closed)
        else:
            self.settings_dialog._load_values()

        if not self.config.get_api_key():
            self.settings_dialog.tabs.setCurrentIndex(0)
            self.settings_dialog.api_key_input.setFocus()
            self.settings_dialog.api_key_input.selectAll()

        force_window_to_foreground(self.settings_dialog)

    def _on_settings_applied(self):
        """Called live when user clicks 'Save & Apply Changes' without closing dialog."""
        hotkey = self.config.get("hotkey", "<ctrl>+<space>")
        mode = self.config.get("hotkey_mode", "toggle")
        prompt_hk = self.config.get("prompt_hotkey", "<ctrl>+<shift>+p")
        trans_hk = self.config.get("transform_hotkey", "<ctrl>+<shift>+t")
        disp_name = self.config.get("hotkey_display", "Ctrl + Space")

        self.hotkey_mgr.update_config(hotkey, mode, prompt_hk, trans_hk)
        self.gemini.set_api_key(self.config.get_api_key())
        active_model = self.config.get("model_name") or self.config.get("model_mode", "auto")
        self.gemini.set_model(active_model)
        self.tray.update_status(f"🟢 Ready ({disp_name})", state="ready")

    def open_history(self):
        self.open_settings()
        if self.settings_dialog:
            for i in range(self.settings_dialog.tabs.count()):
                if "history" in self.settings_dialog.tabs.tabText(i).lower():
                    self.settings_dialog.tabs.setCurrentIndex(i)
                    break

    def open_cost_dashboard(self):
        self.open_settings()
        if self.settings_dialog:
            for i in range(self.settings_dialog.tabs.count()):
                if "cost" in self.settings_dialog.tabs.tabText(i).lower():
                    self.settings_dialog.tabs.setCurrentIndex(i)
                    break

    def _on_settings_closed(self, result):
        # Keep settings_dialog instance cached in memory so reopening is instant (<10ms)
        # Reload hotkey settings in listener
        hotkey = self.config.get("hotkey", "<ctrl>+<space>")
        mode = self.config.get("hotkey_mode", "toggle")
        prompt_hk = self.config.get("prompt_hotkey", "<ctrl>+<shift>+p")
        trans_hk = self.config.get("transform_hotkey", "<ctrl>+<shift>+t")
        disp_name = self.config.get("hotkey_display", "Ctrl + Space")

        self.hotkey_mgr.update_config(hotkey, mode, prompt_hk, trans_hk)
        self.gemini.set_api_key(self.config.get_api_key())
        active_model = self.config.get("model_name") or self.config.get("model_mode", "auto")
        self.gemini.set_model(active_model)
        self.tray.update_status(f"🟢 Ready ({disp_name})", state="ready")

    def quit_app(self):
        logger.info("Quitting Gemini Flow...")
        try:
            self.hotkey_mgr.stop()
        except Exception:
            pass
        if self.recorder.is_recording:
            try:
                self.recorder.stop_recording()
            except Exception:
                pass
        try:
            if hasattr(self, 'server') and self.server:
                self.server.close()
                self.server.deleteLater()
            QLocalServer.removeServer(IPC_PIPE_NAME)
        except Exception:
            pass
        release_app_mutex()
        remove_pid_file()
        QApplication.processEvents()
        self.app.quit()

    def restart_app(self):
        """Cleanly releases all resources and launches a fresh Gemini Flow instance without requiring PC reboot."""
        logger.info("Restarting Gemini Flow cleanly...")
        try:
            self.hotkey_mgr.stop()
        except Exception:
            pass
        if self.recorder.is_recording:
            try:
                self.recorder.stop_recording()
            except Exception:
                pass
        release_app_mutex()
        remove_pid_file()
        try:
            self.server.close()
            QLocalServer.removeServer(IPC_PIPE_NAME)
        except Exception:
            pass

        import subprocess
        python_exe = sys.executable
        pythonw_cand = Path(python_exe).parent / "pythonw.exe"
        if pythonw_cand.exists():
            python_exe = str(pythonw_cand)

        launcher = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main_standalone.py")
        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000
        flags = DETACHED_PROCESS | CREATE_NO_WINDOW
        try:
            subprocess.Popen([python_exe, launcher, "--force-restart"], creationflags=flags, close_fds=True)
        except Exception as e:
            logger.error(f"Failed to spawn detached process: {e}")
            subprocess.Popen([python_exe, launcher, "--force-restart"])

        self.app.quit()

    def run(self, show_window: bool = True):
        # Write active process ID
        write_pid_file()

        # Start global hotkeys
        self.hotkey_mgr.start()
        self.tray.show()

        hotkey_name = self.config.get("hotkey_display", "Ctrl + Space")
        self.tray.showMessage(
            "Gemini Flow is Active 🎙️",
            f"Press {hotkey_name} to dictate, or Ctrl + Shift + P to turn thoughts into AI Prompts!",
            SystemTrayManager.MessageIcon.Information,
            3500
        )

        # Show Dashboard window on launch (or automatically if API key is not yet configured)
        api_key = self.config.get_api_key()
        if not api_key:
            logger.info("No Gemini API key configured. Bringing settings dialog to front for setup...")
            self.open_settings()
            if self.settings_dialog:
                self.settings_dialog.tabs.setCurrentIndex(0)
                self.settings_dialog.api_key_input.setFocus()
        elif show_window:
            self.open_settings()

        try:
            ret = self.app.exec()
            logger.info(f"QApplication.exec() exited with code: {ret}")
            return ret
        except Exception as e:
            logger.critical(f"Exception during app.exec(): {e}", exc_info=True)
            raise
        finally:
            logger.info("run() finally block executing: cleaning up PID file and mutex.")
            remove_pid_file()
            release_app_mutex()


def start_app(show_window: bool = True):
    from PyQt6.QtWidgets import QApplication
    args = sys.argv[1:]
    is_force_restart = any(f in args for f in ("--force-restart", "-f"))

    if "--restart" in args and not is_force_restart:
        logger.info("Restart requested via CLI. Notifying running instance to restart...")
        if notify_running_instance(command="RESTART"):
            print("Running Gemini Flow instance notified to reload.")
            os._exit(0)
        else:
            is_force_restart = True

    if is_force_restart:
        logger.info("Restart requested via CLI. Forcefully terminating old instances and starting fresh...")
        terminate_other_gemini_flow_instances()
        release_app_mutex()
        time.sleep(0.4)

    elif "--set-api-key" in args:
        idx = args.index("--set-api-key")
        if idx + 1 < len(args):
            new_key = args[idx + 1]
            from .config import ConfigManager, sanitize_api_key
            cfg = ConfigManager()
            cfg.set_api_key(new_key)
            cleaned_preview = sanitize_api_key(new_key)[:10] + "..." if len(new_key) > 10 else "***"
            logger.info(f"Gemini API key configured via CLI: {cleaned_preview}")
            print(f"Gemini API key configured successfully: {cleaned_preview}")
            if notify_running_instance(command="RESTART"):
                print("Running Gemini Flow instance notified to reload.")
            sys.exit(0)

    if "--startup" in args or "-s" in args or "--hidden" in args:
        show_window = False

    init_app = QApplication.instance() or QApplication(sys.argv)

    # 1. Enforce atomic single-instance via Named Mutex + live IPC check + Auto Recovery
    is_primary = False
    for attempt in range(4):
        is_primary = acquire_app_mutex()
        if is_primary:
            break
        if is_force_restart:
            terminate_other_gemini_flow_instances()
            release_app_mutex()
            time.sleep(0.3)
            continue

        # Check if an existing primary instance is actually responsive
        notified = notify_running_instance("SHOW" if show_window else "PING")
        if notified:
            logger.info(f"Gemini Flow is already running and acknowledged {'SHOW' if show_window else 'PING'} over IPC.")
            if show_window:
                for _ in range(25):
                    if is_dashboard_window_visible():
                        break
                    time.sleep(0.1)
            os._exit(0)
        else:
            # Check if the process holding the PID is actually still running in Windows
            is_old_alive = False
            if PID_FILE.exists():
                try:
                    with open(PID_FILE, "r", encoding="utf-8") as f:
                        old_pid = int(f.read().strip().split(":")[0])
                    import ctypes
                    # PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                    h_proc = ctypes.windll.kernel32.OpenProcess(0x1000, False, old_pid)
                    if h_proc:
                        ctypes.windll.kernel32.CloseHandle(h_proc)
                        is_old_alive = True
                except Exception:
                    pass

            if is_old_alive and not is_force_restart and attempt < 3:
                # Primary process is alive in Windows; do not kill it, give it another moment
                time.sleep(0.6)
                continue

            if attempt < 2 and not is_force_restart:
                time.sleep(0.5)
                continue

            logger.warning(f"Named Mutex held by unresponsive instance (attempt {attempt+1}/4). Purging zombie processes...")
            terminate_other_gemini_flow_instances()
            release_app_mutex()
            try:
                QLocalServer.removeServer(IPC_PIPE_NAME)
            except Exception:
                pass
            time.sleep(0.4)
            continue

    if not is_primary:
        logger.warning("Could not acquire mutex via standard attempts. Performing final cleanup and starting fresh...")
        terminate_other_gemini_flow_instances()
        release_app_mutex()
        time.sleep(0.3)
        acquire_app_mutex()

    app = GeminiFlowApp()
    sys.exit(app.run(show_window=show_window))


if __name__ == "__main__":
    start_app()

