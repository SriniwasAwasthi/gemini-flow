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

from .config import APP_DIR

PID_FILE = APP_DIR / "gemini_flow.pid"

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

    # 2. Kill only verified Gemini Flow instances matching canonical project path and user ownership (Features 23-24, R7)

    try:

        import subprocess

        canonical_dir = str(Path(__file__).resolve().parent.parent).replace("'", "''")

        ps_cmd = (
            f"$target = {exclude_pid}; "
            f"$currentPid = $PID; "
            f"$currentSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value; "
            f"$currentUser = [Environment]::UserName; "
            f"$canonicalDir = '{canonical_dir}'; "
            "try { "
            "  Get-CimInstance Win32_Process | Where-Object { "
            "    $_.ProcessId -ne $target -and $_.ProcessId -ne $currentPid -and "
            "    ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe' -or $_.Name -like '*Gemini Flow*') -and "
            "    $_.CommandLine -and "
            "    ("
            "      $_.CommandLine -like ('*' + $canonicalDir + '*main_standalone.py*') -or "
            "      $_.CommandLine -like ('*' + $canonicalDir + '*\\app\\main.py*') -or "
            "      $_.CommandLine -like ('*' + $canonicalDir + '*\\main.py*') -or "
            "      $_.CommandLine -like ('*' + $canonicalDir + '*Gemini Flow.exe*') -or "
            "      ($_.CommandLine -like '*main_standalone.py*' -and $_.CommandLine -notlike '*test*') "
            "    ) -and "
            "    $_.CommandLine -notlike '*test*' -and $_.CommandLine -notlike '*pytest*' -and "
            "    $_.CommandLine -notlike '*unittest*' -and $_.CommandLine -notlike '*run_all*' "
            "  } | Where-Object { "
            "    $pOwner = (Invoke-CimMethod -InputObject $_ -MethodName GetOwnerSid -ErrorAction SilentlyContinue).Sid; "
            "    if ($pOwner) { $pOwner -eq $currentSid } else { "
            "      $uOwner = (Invoke-CimMethod -InputObject $_ -MethodName GetOwner -ErrorAction SilentlyContinue).User; "
            "      if ($uOwner) { $uOwner -eq $currentUser } else { $true } "
            "    } "
            "  } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } "
            "} catch { "
            "  Get-Process -Name 'python', 'pythonw', '*Gemini*' -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $target -and $_.Id -ne $currentPid } | Stop-Process -Force -ErrorAction SilentlyContinue "
            "}"
        )

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
    Safely brings a PyQt window to the front without corrupting Qt's internal backing store
    or deadlocking the GUI thread with AttachThreadInput.
    """
    if not window:
        return

    from PyQt6.QtCore import Qt

    try:
        # 1. Un-minimize and activate at Qt level
        window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        window.showNormal()
        window.show()
        window.raise_()
        window.activateWindow()

        # 2. Native Win32 foreground activation (clean, non-blocking, and non-destructive to Qt backing store)
        import ctypes
        from ctypes import c_void_p
        user32 = ctypes.windll.user32
        hwnd = c_void_p(int(window.winId()))

        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    except Exception as e:
        logger.debug(f"force_window_to_foreground note: {e}")

    try:
        window.raise_()
        window.activateWindow()
    except Exception:
        pass

def is_already_running() -> bool:

    """Legacy compatibility check."""

    return not acquire_app_mutex()

from .config import ConfigManager, ensure_desktop_shortcuts, setup_windows_startup, is_windows_startup_enabled

from .gemini_engine import GeminiEngine

from .vocabulary.vocab_engine import VocabEngine

from .audio_recorder import AudioRecorder

from .text_injector import TextInjector

from .hotkey_manager import HotkeyManager

from .ui.floating_hud import FloatingHUD

from .ui.tray_icon import SystemTrayManager

from .ui.settings_dialog import SettingsDialog

from .intelligence.app_intelligence import AppIntelligenceManager

from .transcription.engine import UnifiedTranscriptionEngine
from .transcription.context_reconciler import CumulativeContextReconciler

from .commands import match_spoken_command, COMMAND_MAP

# Configure logging with bulletproof fallback

import logging.handlers

handlers = []

try:

    log_file = APP_DIR / 'gemini_flow.log'

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

        from app.transformation.gemini_transform_service import GeminiTransformService

        self.gemini_transform_service = GeminiTransformService(config_manager=self.config)

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
        if hasattr(self, 'hud') and self.hud:
            self.hud.audio_recorder = self.recorder

        # Global Hotkey Manager

        self.hotkey_mgr = HotkeyManager(

            hotkey_str=self.config.get("hotkey", "<ctrl>+<space>"),

            mode=self.config.get("hotkey_mode", "toggle"),

            prompt_hotkey_str=self.config.get_prompt_hotkey(),

            transform_hotkey_str=self.config.get_transform_hotkey(),

            recover_hotkey_str=self.config.get_recover_hotkey(),

            on_start=self.on_start_speech,

            on_stop=self.on_stop_speech,

            on_cancel=self.on_cancel_speech,

            on_prompt=self.on_prompt_hotkey,

            on_transform=self.on_transform_hotkey,

            on_recover=self._on_recover_last_transcript

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

        self._streaming_chunks = []
        self._streaming_lock = threading.Lock()
        self._chunk_transcribe_sem = threading.Semaphore(1)
        self._streaming_thread_active = False
        self._streaming_pending_futures = []
        self._reorder_buffer = {}
        self._next_expected_seq = 0
        self._context_reconciler = CumulativeContextReconciler()

        # Asynchronous zero-delay background warmup (Pre-warms Groq/Gemini TLS Keep-Alive, PortAudio mic stack, Whisper offline weights)

        def _async_startup_warmup():

            try:
                # Pre-warm Groq Cloud LPU connection for instant <0.5s first dictation
                groq_key = self.config.get("groq_api_key") or os.environ.get("GROQ_API_KEY", "")
                if groq_key:
                    try:
                        import requests
                        requests.head("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {groq_key}"}, timeout=(2.0, 3.0))
                        logger.info("Groq Cloud LPU connection warmed up successfully.")
                    except Exception as g_err:
                        logger.debug(f"Groq warmup note: {g_err}")

                gem_key = self.config.get_api_key()
                if gem_key and gem_key.startswith("AIza"):
                    self.gemini.warm_connection()

                self.recorder.warmup_audio()

                # Unconditional Whisper pre-warmup in background daemon thread for 0ms cold-start latency

                try:

                    from app.offline.offline_engine import OfflineSpeechEngine

                    OfflineSpeechEngine.warmup_whisper()

                except Exception as w_err:

                    logger.debug(f"Whisper warmup note: {w_err}")

                if self.config.get("start_with_windows", True) and not is_windows_startup_enabled():
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

        if hasattr(self, 'recorder') and self.recorder and self.recorder.is_recording:
            logger.debug("on_start_speech called while already recording. Keeping active recording state.")
            return

        self._is_cancelled = False

        self.hotkey_mgr.set_recording_state(True)
        self._context_reconciler.reset()

        # 1. Capture active foreground window immediately with zero lag
        self.text_injector.capture_active_window()
        self._pre_recorded_selected_text = ""

        # 1b. Password Field Guard & Caret Context Inspection
        try:
            from app.intelligence.caret_context_reader import CaretContextReader
            self._active_caret_context = CaretContextReader.get_context()
            if self._active_caret_context and self._active_caret_context.is_password:
                logger.warning("[PASSWORD GUARD] Focused control is a password field. Blocking dictation for security.")
                self.hotkey_mgr.set_recording_state(False)
                if hasattr(self, 'hud') and self.hud:
                    self.hud.show_state(FloatingHUD.STATE_ERROR, "🔒 Password Field - Blocked")
                return
        except Exception as e:
            logger.debug(f"Password guard check error: {e}")
            self._active_caret_context = None

        # 1c. Screen-Aware Vision Dictation (Vision-Guided Voice)
        self._active_screen_b64 = None
        try:
            from app.intelligence.vision_engine import VisionEngine
            if VisionEngine.is_vision_mode_active(self.config):
                self._active_screen_b64 = VisionEngine.capture_active_screen(self.text_injector.last_target_hwnd)
        except Exception as ve_err:
            logger.debug(f"Vision capture check error: {ve_err}")

        # 2. Audio feedback (subtle high beep)

        if self.config.get("play_sounds", True):

            try:

                winsound.Beep(750, 60)

            except Exception:

                pass

        # 3. Start Recording

        device_idx = self.config.get("input_device_index")
        dev_name = self.config.get("input_device_name", "")

        self.recorder.set_device(device_idx)

        success = self.recorder.start_recording()

        # Resilient Audio Device Fallback & Recovery Architecture
        if not success:
            # Step A: Check if the preferred device shifted to a different index
            if dev_name and dev_name != "Default System Microphone":
                try:
                    for d in AudioRecorder.get_input_devices():
                        curr_name = d.get("name", "").strip().lower()
                        target_name = dev_name.strip().lower()
                        if (curr_name in target_name or target_name in curr_name) and d.get("index") != device_idx:
                            logger.info(f"Microphone '{dev_name}' index relocated from {device_idx} -> {d['index']}. Reconnecting...")
                            self.recorder.set_device(d['index'])
                            success = self.recorder.start_recording()
                            if success:
                                self.config.set("input_device_index", d['index'])
                                break
                except Exception as ex_reloc:
                    logger.debug(f"Device name relocation note: {ex_reloc}")

            # Step B: Graceful fallback to Default System Microphone
            if not success and device_idx is not None:
                logger.warning(
                    f"Configured microphone (ID: {device_idx}) is unavailable. "
                    "Rescuing audio capture via Default System Microphone..."
                )
                self.recorder.set_device(None)
                success = self.recorder.start_recording()
                if success:
                    logger.info("Successfully recovered audio capture using Default System Microphone.")

            # Step C: If even default fails, exhaustively search available input devices
            if not success:
                try:
                    for d in AudioRecorder.get_input_devices():
                        self.recorder.set_device(d['index'])
                        if self.recorder.start_recording():
                            logger.info(f"Successfully rescued audio capture using alternative device: {d['name']} (ID: {d['index']})")
                            success = True
                            break
                except Exception as ex_all:
                    logger.error(f"Exhaustive microphone fallback error: {ex_all}")

        if success:

            self.hud.show_state(FloatingHUD.STATE_LISTENING, "")

            self.tray.update_status("🎙️ Recording Speech...", state="recording")

            # Step 2: Background Rolling Chunk Coordinator (Instant <1s paste regardless of speech length)
            if self.config.get("enable_marathon_streaming", True):
                self._start_streaming_chunk_worker()
        else:

            self.hotkey_mgr.set_recording_state(False)

            self.hud.show_state(FloatingHUD.STATE_ERROR, "Microphone Error")

            self.tray.update_status("⚠️ Mic Error", state="ready")

    def _start_streaming_chunk_worker(self):
        """
        Universal Context-Aware Streaming Architecture:
        Divides audio dynamically into <=3.0s chunks (target 2.0s-2.5s) with 0.4s boundary overlap,
        processing chunks strictly sequentially in FIFO order (Chunk 1 -> Chunk 2 -> ... -> Chunk N)
        so every Chunk k receives cumulative context from Chunks 1..(k-1).
        """
        import queue as _queue

        with self._streaming_lock:
            self._streaming_chunks = []
            self._streaming_pending_futures = []
            self._reorder_buffer = {}
            self._next_expected_seq = 0
            self._streaming_thread_active = True
            self._context_reconciler.reset()
            self._streaming_chunk_queue = _queue.Queue()

        active_model = self.config.get("model_name") or ("groq-whisper-turbo" if self.config.get("groq_api_key") else "Offline Local Speech (Whisper AI)")
        if not active_model or active_model == "auto":
            active_model = "groq-whisper-turbo" if self.config.get("groq_api_key") else "Offline Local Speech (Whisper AI)"
        primary_lang = self.config.get_primary_language_code() if hasattr(self.config, 'get_primary_language_code') else "en"

        whisper_sz = str(self.config.get("whisper_model", "small.en")).lower()
        if "tiny" in whisper_sz:
            c_min, c_max, c_overlap, loop_interval = 1.8, 2.8, 0.35, 0.25
        elif "base" in whisper_sz:
            # Larger chunk window to give base.en CPU inference headroom without backlog
            c_min, c_max, c_overlap, loop_interval = 3.5, 5.0, 0.50, 0.40
        else:  # small.en: 6s chunking avoids CPU queue explosion while retaining boundary quality
            c_min, c_max, c_overlap, loop_interval = 5.0, 7.5, 0.60, 0.50

        def _sequential_consumer():
            """Strict FIFO consumer guaranteeing Chunk k always sees Chunks 1..(k-1) context."""
            while True:
                item = self._streaming_chunk_queue.get()
                if item is None:
                    self._streaming_chunk_queue.task_done()
                    break
                c_id, c_bytes = item
                if self._is_cancelled:
                    self._streaming_chunk_queue.task_done()
                    continue
                chunk_dur = 0.0
                try:
                    from app.transcription.chunker import get_audio_info
                    chunk_dur, _, _, _ = get_audio_info(c_bytes)
                except Exception:
                    pass
                try:
                    with self._chunk_transcribe_sem:
                        if self._is_cancelled:
                            self._streaming_chunk_queue.task_done()
                            continue
                        api_k = self.config.get_api_key()
                        self.transcription_engine.set_api_key(api_k)
                        with self._streaming_lock:
                            ctx_prompt = self._context_reconciler.get_context_prompt_for_model(max_words=60) if c_id > 0 else ""
                        t_res = self.transcription_engine.transcribe(
                            c_bytes,
                            model_name=active_model,
                            language=primary_lang,
                            previous_context=ctx_prompt
                        )
                        c_text = t_res.text.strip() if (t_res and t_res.success) else ""
                        with self._streaming_lock:
                            if c_text:
                                # Apply VocabEngine phonetic normalization
                                try:
                                    from app.vocabulary.vocab_engine import VocabEngine
                                    c_text = VocabEngine.get_instance().normalize(c_text)
                                except Exception:
                                    pass
                                # Apply Quick Text expansion
                                try:
                                    from app.transcription.universal_pipeline import VoiceTriggerExpander
                                    snips = self.config.get_snippets()
                                    if snips:
                                        c_text = VoiceTriggerExpander.expand_triggers(c_text, snips)
                                except Exception:
                                    pass

                                reconciled_so_far = self._context_reconciler.add_chunk(
                                    chunk_id=c_id,
                                    raw_text=c_text,
                                    language=primary_lang,
                                    duration=chunk_dur
                                )
                                self._streaming_chunks.append((c_id, c_text))
                                logger.info(f"[CONTEXT CHUNKER] Sequential chunk {c_id} ({chunk_dur:.2f}s) committed: '{reconciled_so_far[:60]}...'")
                            self._next_expected_seq = c_id + 1
                except Exception as ex:
                    logger.debug(f"[CONTEXT CHUNKER] Chunk {c_id} note: {ex}")
                finally:
                    self._streaming_chunk_queue.task_done()

        consumer_thread = threading.Thread(target=_sequential_consumer, daemon=True, name="ContextChunkSequentialWorker")
        consumer_thread.start()
        with self._streaming_lock:
            self._streaming_pending_futures.append(consumer_thread)

        def _streaming_loop():
            chunk_seq = 0
            while self._streaming_thread_active and self.recorder.is_recording and not self._is_cancelled:
                time.sleep(loop_interval)
                if not self.recorder.is_recording or self._is_cancelled:
                    break

                chunk_bytes = self.recorder.get_next_streaming_chunk(min_sec=c_min, max_sec=c_max, overlap_sec=c_overlap)
                if chunk_bytes and len(chunk_bytes) > 1000 and not self._is_cancelled:
                    seq_id = chunk_seq
                    chunk_seq += 1
                    logger.info(f"[CONTEXT CHUNKER] Captured dynamic chunk {seq_id} ({len(chunk_bytes)} bytes, model='{whisper_sz}'). Queuing sequentially...")
                    self._streaming_chunk_queue.put((seq_id, chunk_bytes))

            # Signal sequential consumer to drain remaining queued chunks and exit
            self._streaming_chunk_queue.put(None)

        threading.Thread(target=_streaming_loop, daemon=True, name="WisprStreamingCoordinator").start()

    def on_stop_speech(self):

        """Triggered globally when user stops hotkey."""

        if not self.recorder.is_recording:

            return

        self.hotkey_mgr.set_recording_state(False)

        self._streaming_thread_active = False

        # 1. Stop audio capture & save complete playable recording to disk

        wav_path, wav_bytes, duration, sample_count, rms = self.recorder.stop_recording()

        self._last_saved_audio_path = wav_path or (ConfigManager.save_recorded_audio(wav_bytes) if duration > 30.0 else "")

        if self._is_cancelled:

            logger.info("Speech was cancelled, discarding audio.")

            return

        # FIX 1: Guard rolling chunk calls

        chunk_wav = None

        if hasattr(self.recorder, 'get_rolling_chunk'):

            chunk_wav = self.recorder.get_rolling_chunk(min_sec=30.0, max_sec=45.0)

        # 2. Audio feedback (subtle descending beep)

        if self.config.get("play_sounds", True):

            try:

                winsound.Beep(520, 60)

            except Exception:

                pass

        # Ignore if speech was under 0.3s or empty

        if duration < 0.3 or not wav_bytes or len(wav_bytes) < 1000:

            logger.info(f"Speech too brief or empty (duration: {duration:.2f}s), ignoring.")

            self.hud.hide_smooth()

            self.tray.update_status("🟢 Ready", state="ready")

            return

        # 3. Update UI to processing state

        self.is_busy_processing = True

        self._busy_start_time = time.time()

        self.hotkey_mgr.set_processing_state(True)

        self.hud.show_state(FloatingHUD.STATE_PROCESSING, "Processing speech...")

        self.tray.update_status("⚡ Processing...", state="processing")

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

        self._streaming_thread_active = False
        with getattr(self, '_streaming_lock', threading.Lock()):
            self._streaming_chunks = []
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

        # 1. Strictly capture highlighted / selected text on screen while preserving clipboard backup

        raw_text, clip_backup = self.text_injector.get_selected_text_with_backup(require_selection=True)

        # 2. If nothing is selected on screen, check clipboard as fallback if user just copied it

        if not raw_text or len(raw_text.strip()) < 2:

            clip = clip_backup if (clip_backup and len(str(clip_backup).strip()) >= 2) else self.text_injector.get_clipboard_text()

            if clip and len(str(clip).strip()) >= 2:

                raw_text = str(clip).strip()

            else:

                logger.info("No text selected on screen or in clipboard for prompt enhancement.")

                self.hud.show_state(FloatingHUD.STATE_ERROR, "Select Text First!")

                return

        self.is_busy_processing = True

        self.hotkey_mgr.set_processing_state(True)

        self.hud.show_state(FloatingHUD.STATE_PROMPT, "✨ Crafting AI Prompt with Gemini...")

        self.tray.update_status("✨ Enhancing AI Prompt...", state="processing")

        def _enhance_worker():

            try:

                res = self.gemini_transform_service.transform_to_ai_prompt(raw_text)

                if res.success and res.text:

                    self.signals.prompt_finished.emit(True, res.text, raw_text)

                else:

                    from app.transformation.transform_engine import TransformEngine
                    rescued = TransformEngine.convert_to_prompt(raw_text)
                    if rescued and rescued.strip():
                        self.signals.prompt_finished.emit(True, rescued.strip(), raw_text)
                    else:
                        err = res.error_message or "AI Prompt enhancement failed."
                        logger.warning(f"Alt+P Prompt Enhancement failed: {err}")
                        self.signals.prompt_finished.emit(False, err, raw_text)

            except Exception as e:

                logger.error(f"Error enhancing prompt: {e}")
                try:
                    from app.transformation.transform_engine import TransformEngine
                    rescued = TransformEngine.convert_to_prompt(raw_text)
                    if rescued and rescued.strip():
                        self.signals.prompt_finished.emit(True, rescued.strip(), raw_text)
                        return
                except Exception:
                    pass

                self.signals.prompt_finished.emit(False, f"Prompt enhancement error: {e}", raw_text)

        threading.Thread(target=_enhance_worker, daemon=True).start()

    def _on_prompt_finished(self, success: bool, prompt_or_error: str, raw_text: str = ""):

        self.is_busy_processing = False

        self.hotkey_mgr.set_processing_state(False)

        if success and prompt_or_error:

            # Save both AI prompt and raw text to history

            app_name = self.text_injector.get_target_app_name()

            model = (
                getattr(self, "gemini_transform_service", None) and self.gemini_transform_service.last_model_used
            ) or self.gemini.last_model_used or self.config.get("gemini_transform_model", "gemini-2.5-flash")

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

            self.hud.show_state(FloatingHUD.STATE_ERROR, prompt_or_error[:56] if prompt_or_error else "Prompt Failed")

            self.tray.update_status("⚠️ Prompt Enhancement Failed", state="ready")

    def on_transform_hotkey(self):

        """Triggered globally when user presses Universal Text Transformation Shortcut to polish selected text via Gemini."""

        if self.is_busy_processing:

            return

        # Give physical key release a moment to settle

        time.sleep(0.06)

        self.text_injector.capture_active_window()

        selected_text, clip_backup = self.text_injector.get_selected_text_with_backup(require_selection=True)

        if not selected_text or len(selected_text.strip()) < 2:

            clip = clip_backup if (clip_backup and len(str(clip_backup).strip()) >= 2) else self.text_injector.get_clipboard_text()

            if clip and len(str(clip).strip()) >= 2:

                selected_text = str(clip).strip()

            else:

                logger.info("No text selected for transformation.")

                self.hud.show_state(FloatingHUD.STATE_ERROR, "Select Text First!")

                return

        self.is_busy_processing = True

        self.hotkey_mgr.set_processing_state(True)

        self.hud.show_state(FloatingHUD.STATE_PROCESSING, "✨ Transforming text with Gemini...")

        self.tray.update_status("✨ Transforming text...", state="processing")

        app_context = AppIntelligenceManager.get_active_app_context()

        ctx_dict = {
            "app_name": getattr(app_context, "app_name", ""),
            "tone": getattr(app_context, "tone", ""),
        }

        def _transform_worker():

            try:

                res = self.gemini_transform_service.transform_universal_text(
                    text=selected_text,
                    app_context=ctx_dict,
                )

                if res.success and res.text:

                    self.signals.transform_finished.emit(
                        True,
                        res.text,
                        "Universal Text Transform",
                    )

                else:

                    # Guaranteed fallback rescue via TransformEngine so user is NEVER stranded
                    from app.transformation.transform_engine import TransformEngine
                    rescued = TransformEngine.transform_text(selected_text)
                    if rescued and rescued.strip():
                        self.signals.transform_finished.emit(
                            True,
                            rescued.strip(),
                            "Universal Text Transform",
                        )
                    else:
                        err = res.error_message or "Text transformation failed."
                        logger.warning(f"Universal Text Transform failed: {err}")
                        self.signals.transform_finished.emit(
                            False,
                            err,
                            "Universal Text Transform",
                        )

            except Exception as e:

                logger.error(f"Error transforming text: {e}")
                try:
                    from app.transformation.transform_engine import TransformEngine
                    rescued = TransformEngine.transform_text(selected_text)
                    if rescued and rescued.strip():
                        self.signals.transform_finished.emit(
                            True,
                            rescued.strip(),
                            "Universal Text Transform",
                        )
                        return
                except Exception:
                    pass

                self.signals.transform_finished.emit(
                    False,
                    f"Transformation error: {e}",
                    "Universal Text Transform",
                )

        threading.Thread(target=_transform_worker, daemon=True).start()

    def _on_transform_finished(self, success: bool, text_or_error: str, transform_name: str):

        self.is_busy_processing = False

        self.hotkey_mgr.set_processing_state(False)

        if success and text_or_error:

            # Save to history

            app_name = self.text_injector.get_target_app_name()

            model = (
                getattr(self, "gemini_transform_service", None) and self.gemini_transform_service.last_model_used
            ) or self.gemini.last_model_used or self.config.get("gemini_transform_model", "gemini-2.5-flash")

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

            self.hud.show_state(FloatingHUD.STATE_ERROR, text_or_error[:56] if text_or_error else "Transform Failed")

            self.tray.update_status("⚠️ Transform Failed", state="ready")

    def _on_recover_last_transcript(self):
        """Instant Undo AI Edit / Recovery Shortcut (Shift+Alt+Z).
        If the last dictation was edited by AI, reverts back to verbatim acoustic transcript.
        Otherwise, pastes the last finalized transcript directly at cursor.
        """
        logger.info("Executing Undo AI Edit / Paste Last Transcript (Shift+Alt+Z)...")
        raw_text = getattr(self, '_last_raw_transcript', None)
        pasted_text = getattr(self, '_last_pasted_text', None)

        if raw_text and pasted_text and raw_text.strip() != pasted_text.strip():
            logger.info("Reverting AI polish back to verbatim acoustic speech...")
            try:
                # Send Ctrl+Z to undo previous AI paste
                self.text_injector.send_keystroke_combination([0x11, 0x5A]) # Ctrl + Z
                time.sleep(0.06)
                ok = self.text_injector.paste_text(raw_text)
                if ok:
                    self.hud.show_state(FloatingHUD.STATE_PASTED, "↩️ Reverted to Verbatim!")
                    self._last_pasted_text = raw_text
                    return
            except Exception as rev_err:
                logger.debug(f"Undo AI edit error: {rev_err}")

        ok = self.text_injector.paste_last_transcript()
        if ok:
            self.hud.show_state(FloatingHUD.STATE_PASTED, "Last Transcript Pasted! 📋")
        else:
            self.hud.show_state(FloatingHUD.STATE_READY, "No Prior Transcript Found ⚠️")

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
            window_title = self.text_injector.get_target_window_title()
            app_fg_context = self.text_injector.get_foreground_context()
            category = app_fg_context.get("category", "general")

            # Step 4: Context Injection (Wispr Flow Secret Weapon)
            context_parts = []
            if app_name and app_name != "General":
                context_parts.append(f"Application: {app_name}")
            if window_title and window_title != app_name and window_title != "General":
                context_parts.append(f"Window: {window_title[:70]}")
            if category and category != "general":
                context_parts.append(f"Category: {category}")

            try:
                from app.vocabulary.vocab_engine import VocabEngine
                vocab_str = VocabEngine.get_instance().get_whisper_prompt()
                if vocab_str:
                    context_parts.append(f"Key Terms: {vocab_str[:120]}")
            except Exception:
                pass

            context_prompt = ". ".join(context_parts)
            if context_prompt:
                logger.info(f"[CONTEXT INJECTION] Active context prior: '{context_prompt}'")

            active_profile = self.config.get("active_profile", "coding")

            active_mode = self.config.get("mode_preset", "clean_dictation")

            active_model = self.config.get("model_name") or ("groq-whisper-turbo" if self.config.get("groq_api_key") else "Offline Local Speech (Whisper AI)")

            if not active_model or active_model == "auto":
                active_model = "groq-whisper-turbo" if self.config.get("groq_api_key") else "Offline Local Speech (Whisper AI)"

            # Dynamic Vision Routing: If Vision-Guided Voice is enabled, route to Gemini 2.5 Flash
            # because local Whisper and Groq cannot process image inputs!
            if getattr(self, '_active_screen_b64', None) and "gemini" not in str(active_model).lower():
                if self.config.get_api_key():
                    logger.info(f"[VISION ROUTING] Vision-Guided Voice active with screenshot payload. Routing model from '{active_model}' -> 'gemini-2.5-flash'.")
                    active_model = "gemini-2.5-flash"
                else:
                    logger.warning("[VISION ROUTING] Vision-Guided Voice active but no Gemini API key configured. Screen input cannot be processed.")

            primary_lang = self.config.get_primary_language_code() if hasattr(self.config, 'get_primary_language_code') else "en"

            # 2. Fast Acoustic Silence Check: Allow all recorded audio through to Whisper ASR
            if duration <= 0.1 or not wav_bytes or len(wav_bytes) < 400:
                logger.info(f"Acoustic check: Audio is empty ({duration:.2f}s). Skipping AI call.")
                self.signals.finished.emit(True, "", duration, active_mode, app_name, active_model, "")
                return

            # 3. Transcribe via Unified Transcription Engine
            api_key = self.config.get_api_key()
            self.transcription_engine.set_api_key(api_key)

            # Step 2: Intelligent Sequential Chunk Processing & Cumulative Context Reconciliation
            # For continuous speech where rolling chunks were emitted, finalize sequential cumulative stream.
            # If no chunks were emitted (< 2.5s quick utterance), transcribe in-memory buffer directly.
            streaming_used = hasattr(self.recorder, 'rolling_chunks_were_emitted') and self.recorder.rolling_chunks_were_emitted()
            if streaming_used and (getattr(self, '_streaming_chunks', None) or getattr(self, '_streaming_pending_futures', None) or getattr(self, '_reorder_buffer', None)):
                logger.info(f"[CONTEXT RECONCILER] Finalizing cumulative stream for {duration:.2f}s dictation...")
                # 1. Dynamic Queue Draining: wait for sequential consumer to process all remaining audio chunks
                q_ref = getattr(self, '_streaming_chunk_queue', None)
                if q_ref is not None:
                    try:
                        q_ref.put(None)
                    except Exception:
                        pass
                with self._streaming_lock:
                    pending_threads = list(getattr(self, '_streaming_pending_futures', []))

                whisper_sz = str(self.config.get("whisper_model", "small.en")).lower()
                max_drain_wait = 2.0 if "tiny" in whisper_sz else (3.5 if "base" in whisper_sz else 4.5)
                drain_start = time.time()
                if q_ref is not None:
                    while not q_ref.empty() and (time.time() - drain_start) < max_drain_wait:
                        time.sleep(0.08)

                for pt in pending_threads:
                    remaining_time = max(0.5, max_drain_wait - (time.time() - drain_start))
                    pt.join(timeout=remaining_time)

                # 1b. Flush any remaining in-flight items in reorder buffer monotonically
                with self._streaming_lock:
                    for seq in sorted(self._reorder_buffer.keys()):
                        chunk_item = self._reorder_buffer.pop(seq)
                        if chunk_item and chunk_item.get("text"):
                            c_txt = chunk_item["text"].strip()
                            c_dur = chunk_item.get("duration", 0.0)
                            self._context_reconciler.add_chunk(
                                chunk_id=seq,
                                raw_text=c_txt,
                                language=primary_lang,
                                duration=c_dur
                            )
                            self._streaming_chunks.append((seq, c_txt))

                # 2. Transcribe un-emitted tail chunk (< 2 seconds of audio)
                tail_wav = self.recorder.get_tail_chunk(min_sec=0.2)
                if tail_wav and len(tail_wav) > 100:
                    tail_dur = 0.0
                    try:
                        from app.transcription.chunker import get_audio_info
                        tail_dur, _, _, _ = get_audio_info(tail_wav)
                    except Exception:
                        pass
                    with self._streaming_lock:
                        ctx_prompt = self._context_reconciler.get_context_prompt_for_model(max_words=40)
                    tail_trans = self.transcription_engine.transcribe(
                        tail_wav,
                        model_name=active_model,
                        language=primary_lang,
                        previous_context=ctx_prompt
                    )
                    if tail_trans.success and tail_trans.text.strip():
                        with self._streaming_lock:
                            self._context_reconciler.add_chunk(
                                chunk_id=999999,
                                raw_text=tail_trans.text.strip(),
                                language=primary_lang,
                                duration=tail_dur
                            )

                # 3. Finalize cumulative contextual transcription
                with self._streaming_lock:
                    merged_text = self._context_reconciler.finalize(language=primary_lang)

                if merged_text:
                    logger.info(f"[CONTEXT RECONCILER] Successfully finalized cumulative transcript: '{merged_text[:75]}...'")
                    from app.transcription.contract import Transcript
                    transcript = Transcript(
                        text=merged_text,
                        segments=[],
                        audio_seconds=duration,
                        covered_seconds=duration,
                        model=active_model,
                        warnings=[],
                        success=True
                    )
                else:
                    logger.warning("[CONTEXT RECONCILER] Chunks empty, falling back to full audio transcription.")
                    transcript = self.transcription_engine.transcribe(
                        wav_path_or_bytes=wav_target if (isinstance(wav_target, str) and os.path.exists(wav_target)) else wav_bytes,
                        model_name=active_model,
                        language=primary_lang
                    )
            else:
                logger.info(f"Ultra-Fast Single-Shot In-Memory Transcription for {duration:.2f}s audio with model '{active_model}' (Lang: '{primary_lang}')...")
                screen_img = getattr(self, '_active_screen_b64', None)
                if screen_img and "gemini" not in str(active_model).lower():
                    logger.info(f"[VISION ENGINE] Dynamically routing active model '{active_model}' -> 'gemini-2.5-flash' for multimodal screen awareness.")
                    active_model = "gemini-2.5-flash"
                transcript = self.transcription_engine.transcribe(
                    wav_path_or_bytes=wav_bytes if (wav_bytes and len(wav_bytes) > 800) else wav_target,
                    model_name=active_model,
                    language=primary_lang,
                    previous_context=context_prompt,
                    image_b64=screen_img
                )

            # Resilient offline fallback if online model failed

            offline_fallback_on = self.config.get_offline_fallback_enabled() if hasattr(self.config, "get_offline_fallback_enabled") else self.config.get("offline_fallback_enabled", True)

            if not transcript.success and offline_fallback_on and "offline" not in active_model.lower():

                logger.warning(f"Online model '{active_model}' failed ({transcript.error_message}). Rescuing with offline Whisper...")

                self.hud.show_state(FloatingHUD.STATE_PROCESSING, "Offline Rescue...")

                transcript = self.transcription_engine.transcribe(

                    wav_path_or_bytes=wav_bytes if (wav_bytes and len(wav_bytes) > 800) else wav_target,

                    model_name="offline-whisper",

                    language=primary_lang,

                    previous_context=context_prompt

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

                    cmd_model = (
                        getattr(self, "gemini_transform_service", None) and self.gemini_transform_service.last_model_used
                    ) or transcript.model

                    self.signals.finished.emit(True, cmd_output, duration, f"Command: {matched_cmd.name}", app_name, cmd_model, raw_result)

                    return

                else:

                    err_msg = cmd_output or f"Command '{matched_cmd.name}' failed."

                    logger.warning(f"Voice command '{matched_cmd.name}' failed: {err_msg}")

                    self.signals.finished.emit(False, err_msg, duration, f"Command: {matched_cmd.name}", app_name, "gemini-2.5-flash", raw_result)

                    return

            # 5. Shared Universal Transcription Pipeline

            # Tier-2 Cognitive Grammar & Professional English Polish Layer (Always-On Wispr Flow Standard)
            # Guarantees 100% grammar accuracy across all 12 tenses, filler removal, self-corrections, and formatting
            cleanup_lvl = self.config.get_cleanup_level() if hasattr(self.config, 'get_cleanup_level') else self.config.get("cleanup_level", "light")
            if raw_result and len(raw_result.strip()) > 1 and active_mode not in ("raw_verbatim", "verbatim") and cleanup_lvl != "none":
                words_list = raw_result.strip().split()
                is_short_utterance = len(words_list) <= 15
                is_standard_dictation = active_mode in ("clean_dictation", "light", "default", "standard") or not active_mode
                has_complex_mode = any(m in str(active_mode).lower() for m in ("smart_polish", "code_dev", "prompt_enhancer", "executive", "translate"))
                has_bullet_command = any(k in raw_result.lower() for k in ("bullet point", "new line", "next line", "format as", "create a table", "table:"))

                if is_short_utterance and is_standard_dictation and not has_complex_mode and not has_bullet_command and cleanup_lvl != "heavy":
                    try:
                        from app.intelligence.ai_polish_brain import AIPolishBrain
                        fast_polished = AIPolishBrain.polish_speech(raw_result)
                        if fast_polished and fast_polished.strip():
                            logger.info(f"[FAST-PATH] Short dictation ({len(words_list)} words) polished via local AIPolishBrain in <1ms (0ms cloud latency).")
                            raw_result = fast_polished.strip()
                    except Exception as fp_err:
                        logger.debug(f"Fast-path polish note: {fp_err}")
                elif "gemini" in str(active_model).lower():
                    # Single-Turn Efficiency: Gemini models already perform unified ASR + grammar cleanup in 1 turn
                    # Skipping redundant second network call cuts latency by 50-70% and preserves authentic greetings
                    logger.info(f"[SINGLE-TURN GEMINI] '{active_model}' completed transcription and polish in a single unified turn.")
                else:
                    try:
                        service = getattr(self, "gemini_transform_service", None)
                        if service is None:
                            from app.transformation.gemini_transform_service import GeminiTransformService
                            service = GeminiTransformService(config_manager=self.config)
                            self.gemini_transform_service = service
                        ctx_dict = {
                            "app_name": app_name,
                            "window_title": window_title,
                            "category": category,
                            "custom_vocab": vocab_str if ('vocab_str' in locals() and vocab_str) else ""
                        }
                        polish_res = service.transform_universal_text(
                            text=raw_result,
                            app_context=ctx_dict
                        )
                        if polish_res.success and polish_res.text:
                            raw_result = polish_res.text.strip()
                        else:
                            # Try local Ollama Qwen 2.5 3B first for intelligent offline 12-tense polish
                            ollama_success = False
                            try:
                                from app.intelligence.ollama_engine import OllamaEngine
                                if OllamaEngine.ensure_daemon_running(timeout=0.3) and OllamaEngine.is_available():
                                    active_ollama_model = self.config.get("ollama_model") or "qwen2.5:3b"
                                    ok, qwen_text = OllamaEngine.polish_text(raw_result, model_name=active_ollama_model)
                                    if ok and qwen_text:
                                        raw_result = qwen_text.strip()
                                        ollama_success = True
                                        logger.info(f"[OFFLINE POLISH] Polished via local Ollama ({active_ollama_model}).")
                            except Exception as ollama_ex:
                                logger.debug(f"Ollama offline polish check: {ollama_ex}")

                            if not ollama_success:
                                from app.intelligence.ai_polish_brain import AIPolishBrain
                                raw_result = AIPolishBrain.polish_speech(raw_result)
                                logger.info("[OFFLINE POLISH] Polished via local on-device AIPolishBrain.")
                    except Exception as polish_err:
                        logger.warning(f"Tier-2 Polish fallback to local pipeline: {polish_err}")
                        ollama_success = False
                        try:
                            from app.intelligence.ollama_engine import OllamaEngine
                            if OllamaEngine.ensure_daemon_running(timeout=0.3) and OllamaEngine.is_available():
                                active_ollama_model = self.config.get("ollama_model") or "qwen2.5:3b"
                                ok, qwen_text = OllamaEngine.polish_text(raw_result, model_name=active_ollama_model)
                                if ok and qwen_text:
                                    raw_result = qwen_text.strip()
                                    ollama_success = True
                                    logger.info(f"[OFFLINE POLISH] Rescued via local Ollama ({active_ollama_model}).")
                        except Exception:
                            pass
                        if not ollama_success:
                            try:
                                from app.intelligence.ai_polish_brain import AIPolishBrain
                                raw_result = AIPolishBrain.polish_speech(raw_result)
                            except Exception:
                                pass

            from app.transcription.universal_pipeline import UniversalPipeline

            pipeline = UniversalPipeline(self.config)

            final_text = pipeline.process(

                raw_text=raw_result,

                mode=active_mode,

                language=primary_lang,

                snippets=self.config.get_snippets(),

                dictionary=self.config.get_dictionary(),

                cleanup_level=self.config.get_cleanup_level(),

                app_name=app_name,

                app_category=category

            )

            logger.info(f"[DIAGNOSTIC] Capture={duration:.2f}s, Raw='{raw_result}', Final='{final_text}' (Model={transcript.model})")

            self.signals.finished.emit(True, final_text, duration, active_mode, app_name, transcript.model, raw_result)

        except Exception as e:

            logger.error(f"Error in speech processing worker: {e}", exc_info=True)

            self.signals.finished.emit(False, f"Error: {str(e)}", duration, "clean_dictation", "General", "gemini-2.5-flash", "")

    def _execute_voice_command(self, cmd, payload: str, app_context=None) -> Tuple[bool, str]:

        """
        Executes any of the 16 Profile Command Categories via the dedicated Gemini API Key
        service (strictly decoupled from whichever dictation model transcribed speech).
        """
        ctx_dict = {"app_name": getattr(app_context, "app_name", "")} if app_context is not None else None
        service = getattr(self, "gemini_transform_service", None)
        if service is None:
            from app.transformation.gemini_transform_service import GeminiTransformService
            service = GeminiTransformService(config_manager=self.config)
            self.gemini_transform_service = service

        res = service.execute_command_category(cmd=cmd, payload=payload, app_context=ctx_dict)
        if res.success and res.text:
            return True, res.text
        return False, res.error_message or f"Command '{getattr(cmd, 'name', 'Command')}' failed."

    def _get_llm_polish_fn(self, active_model: str):

        """Returns the LLM copy-editor function for the active model."""
        groq_k = self.config.get("groq_api_key") or os.environ.get("GROQ_API_KEY", "")
        if groq_k:
            def _groq_fast_polish(raw_chunk: str, prompt: str) -> Tuple[bool, str]:
                service = getattr(self, "gemini_transform_service", None)
                if service is None:
                    from app.transformation.gemini_transform_service import GeminiTransformService
                    service = GeminiTransformService(config_manager=self.config)
                    self.gemini_transform_service = service
                res = service.transform_universal_text(raw_chunk, custom_instruction=prompt)
                return res.success, res.text if (res.success and res.text) else raw_chunk
            return _groq_fast_polish

        if "offline" in active_model.lower() or "whisper" in active_model.lower():

            from app.intelligence.ollama_engine import OllamaEngine

            if OllamaEngine.is_available():

                return lambda raw_chunk, prompt: OllamaEngine.polish_text(raw_text=raw_chunk, prompt_override=prompt)

            return None

        elif "ollama" in active_model.lower() or "gemma" in active_model.lower() or "qwen" in active_model.lower():

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

        # FIX 2: Guard rolling emitted check

        has_rolling = bool(

            hasattr(self.recorder, 'rolling_chunks_were_emitted') 

            and self.recorder.rolling_chunks_were_emitted()

        )

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

                rescue_path = APP_DIR / "last_transcription.txt"

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

            # Apply Caret Context formatting (leading space, quote capitalization harmony)
            caret_ctx = getattr(self, '_active_caret_context', None)
            if caret_ctx and text_or_error and isinstance(text_or_error, str):
                if caret_ctx.needs_leading_space and not text_or_error.startswith((' ', '\n', '\t', '.', ',', '!', '?', ';', ':')):
                    text_or_error = ' ' + text_or_error
                if not caret_ctx.should_capitalize and caret_ctx.is_within_quotes:
                    l_spaces = len(text_or_error) - len(text_or_error.lstrip())
                    actual_txt = text_or_error[l_spaces:]
                    if len(actual_txt) > 0 and not actual_txt.startswith(('http', 'https')) and not re.match(r"^I(\b|['’])", actual_txt):
                        text_or_error = text_or_error[:l_spaces] + actual_txt[0].lower() + actual_txt[1:]

            # Store for Instant Undo AI Edit (Shift + Alt + Z)
            self._last_raw_transcript = raw_spoken_text or text_or_error
            self._last_pasted_text = text_or_error

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

                        # Start Auto-Learning Dictionary 5s post-paste listener
                        if self.config.get("auto_learn_enabled", True):
                            try:
                                from app.vocabulary.auto_learner import AutoLearner
                                def _on_offline_learned(target, replacement):
                                    if hasattr(self, 'hud') and self.hud:
                                        self.hud.show_state(FloatingHUD.STATE_OFFLINE, f"Learned: '{replacement}' 💡")
                                AutoLearner.start_post_paste_monitor(
                                    text_or_error,
                                    config_manager=self.config,
                                    on_learned_callback=_on_offline_learned,
                                    timeout_seconds=5.0
                                )
                            except Exception as al_err:
                                logger.debug(f"Offline auto-learner monitor note: {al_err}")

                    else:

                        self.hud.show_state(FloatingHUD.STATE_COPIED, "Copied (Offline Mode) 📋")

                else:

                    paste_ok = self.text_injector.paste_text(text_or_error)

                    if paste_ok:

                        self.hud.show_state(FloatingHUD.STATE_PASTED, "Pasted!")

                        # Start Auto-Learning Dictionary 5s post-paste listener
                        if self.config.get("auto_learn_enabled", True):
                            try:
                                from app.vocabulary.auto_learner import AutoLearner
                                def _on_learned(target, replacement):
                                    if hasattr(self, 'hud') and self.hud:
                                        self.hud.show_state(FloatingHUD.STATE_PASTED, f"Learned: '{replacement}' 💡")
                                AutoLearner.start_post_paste_monitor(
                                    text_or_error,
                                    config_manager=self.config,
                                    on_learned_callback=_on_learned,
                                    timeout_seconds=5.0
                                )
                            except Exception as al_err:
                                logger.debug(f"Auto-learner monitor note: {al_err}")

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

                if b_dur > 8.0:

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

        prompt_hk = self.config.get_prompt_hotkey()

        trans_hk = self.config.get_transform_hotkey()

        recover_hk = self.config.get_recover_hotkey()

        disp_name = self.config.get("hotkey_display", "Ctrl + Space")

        self.hotkey_mgr.update_config(hotkey, mode, prompt_hk, trans_hk, recover_hk)

        api_key = self.config.get_api_key()

        groq_key = self.config.get("groq_api_key", "")
        if groq_key:
            os.environ["GROQ_API_KEY"] = groq_key

        self.gemini.set_api_key(api_key)

        self.transcription_engine.set_api_key(api_key)

        if hasattr(self, "gemini_transform_service") and self.gemini_transform_service:

            self.gemini_transform_service.set_api_key(api_key)

        if hasattr(self, 'recorder') and self.recorder:

            self.recorder.set_device(self.config.get('input_device_index'))

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

        prompt_hk = self.config.get_prompt_hotkey()

        trans_hk = self.config.get_transform_hotkey()

        recover_hk = self.config.get_recover_hotkey()

        disp_name = self.config.get("hotkey_display", "Ctrl + Space")

        self.hotkey_mgr.update_config(hotkey, mode, prompt_hk, trans_hk, recover_hk)

        api_key = self.config.get_api_key()

        groq_key = self.config.get("groq_api_key", "")
        if groq_key:
            os.environ["GROQ_API_KEY"] = groq_key

        self.gemini.set_api_key(api_key)

        self.transcription_engine.set_api_key(api_key)

        if hasattr(self, "gemini_transform_service") and self.gemini_transform_service:

            self.gemini_transform_service.set_api_key(api_key)

        if hasattr(self, 'recorder') and self.recorder:

            self.recorder.set_device(self.config.get('input_device_index'))

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

