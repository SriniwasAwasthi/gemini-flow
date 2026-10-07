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
        for title in ("Gemini Flow — Voice AI Settings & Dashboard", "Gemini Flow - Voice AI Settings & Dashboard"):
            hwnd = u32.FindWindowW(None, title)
            if hwnd and u32.IsWindowVisible(hwnd):
                # Ensure it is restored and brought to top
                SW_RESTORE = 9
                u32.ShowWindow(hwnd, SW_RESTORE)
                u32.SetForegroundWindow(hwnd)
                return True
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
    if socket.waitForConnected(1200):
        socket.write(f"{command}\n".encode("utf-8"))
        socket.waitForBytesWritten(800)
        # Wait for acknowledgment
        if socket.waitForReadyRead(1000):
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
        flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)

        # After 1200ms, demote HWND_TOPMOST back to normal so it doesn't stay permanently locked on top
        def _demote_topmost():
            try:
                user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
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

# Configure logging
import logging.handlers
log_file = Path(os.environ.get("APPDATA", Path.home())) / "GeminiFlow" / "gemini_flow.log"
log_file.parent.mkdir(parents=True, exist_ok=True)
handlers = [logging.handlers.RotatingFileHandler(str(log_file), maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8")]
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
        self.gemini = GeminiEngine(
            api_key=self.config.get_api_key(),
            model_name=self.config.get("model_mode", "auto")
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
                if self.config.get("offline_fallback_enabled", True) or str(self.config.get("model_name", "")).lower() in ("offline-whisper", "offline"):
                    from app.offline.offline_engine import OfflineSpeechEngine
                    OfflineSpeechEngine.warmup_whisper()
                if self.config.get("start_with_windows", True):
                    setup_windows_startup(True)
                ensure_desktop_shortcuts()
            except Exception as ex:
                logger.debug(f"Async startup warmup note: {ex}")

        threading.Thread(target=_async_startup_warmup, daemon=True, name="AppStartupWarmup").start()

    def _on_audio_amplitude(self, amp: float):
        if self.recorder.is_recording:
            self.hud.update_volume(amp)

    def on_start_speech(self):
        """Triggered globally when user presses hotkey to speak."""
        if self.is_busy_processing:
            logger.warning("Still processing previous speech, ignoring new start.")
            return

        self._is_cancelled = False
        with self._rolling_lock:
            self._rolling_chunks = []
        self._rolling_active = True
        self.hotkey_mgr.set_recording_state(True)

        # 1. Capture active foreground window
        self.text_injector.capture_active_window()

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
            self.hud.show_state(FloatingHUD.STATE_ERROR, "Microphone Error")
            self.tray.update_status("⚠️ Mic Error", state="ready")

    def _start_rolling_transcription(self):
        """Asynchronously slices and transcribes 16-24s chunks in real-time during long recordings."""
        def _rolling_loop():
            chunk_idx = 0
            while self.recorder.is_recording and not self._is_cancelled and self._rolling_active:
                time.sleep(1.0)
                if not self.recorder.is_recording or self._is_cancelled or not self._rolling_active:
                    break

                chunk_wav = self.recorder.get_rolling_chunk(min_sec=16.0, max_sec=24.0)
                if chunk_wav and len(chunk_wav) > 2000:
                    curr_idx = chunk_idx
                    chunk_idx += 1
                    with self._rolling_lock:
                        self._rolling_chunks.append("")

                    target_hwnd = getattr(self.text_injector, "last_target_hwnd", None)
                    app_context = AppIntelligenceManager.get_active_app_context(target_hwnd)
                    active_profile = app_context.profile_id if (app_context and app_context.profile_id) else self.config.get("active_profile", "coding")
                    active_mode = self.config.get("mode_preset", "clean_dictation")
                    prompt = self.config.get_system_prompt(preset_override=active_mode, app_context=app_context, profile_id_override=active_profile)
                    auto_cost_mode = self.config.get("auto_cost_mode", True)
                    offline_fallback_on = self.config.get_offline_fallback_enabled() if hasattr(self.config, "get_offline_fallback_enabled") else self.config.get("offline_fallback_enabled", True)

                    def _transcribe_slice(c_idx, c_bytes):
                        try:
                            ok, txt = self.gemini.transcribe_audio(
                                wav_bytes=c_bytes,
                                system_instruction=prompt,
                                app_context=app_context,
                                profile_id=active_profile,
                                auto_cost_mode=auto_cost_mode,
                                offline_fallback_enabled=offline_fallback_on
                            )
                            if ok and txt:
                                with self._rolling_lock:
                                    if c_idx < len(self._rolling_chunks):
                                        self._rolling_chunks[c_idx] = txt.strip()
                        except Exception as ex:
                            logger.debug(f"Rolling slice {c_idx} error: {ex}")

                    threading.Thread(target=_transcribe_slice, args=(curr_idx, chunk_wav), daemon=True).start()

        threading.Thread(target=_rolling_loop, daemon=True, name="RollingAudioMonitor").start()

    def on_stop_speech(self):
        """Triggered globally when user stops hotkey."""
        if not self.recorder.is_recording:
            return

        self._rolling_active = False
        self.hotkey_mgr.set_recording_state(False)

        # 1. Stop audio capture
        wav_bytes, duration = self.recorder.stop_recording()

        if self._is_cancelled:
            logger.info("Speech was cancelled, discarding audio.")
            return

        # 2. Audio feedback (subtle descending beep)
        if self.config.get("play_sounds", True):
            try:
                winsound.Beep(520, 60)
            except Exception:
                pass

        # Ignore if speech was under 0.2s or empty
        if duration < 0.2 or len(wav_bytes) < 2000:
            logger.info("Speech too brief, ignoring.")
            self.hud.hide_smooth()
            self.tray.update_status("🟢 Ready", state="ready")
            return

        # 3. Update UI to processing state
        self.is_busy_processing = True
        self.hotkey_mgr.set_processing_state(True)
        self.hud.show_state(FloatingHUD.STATE_PROCESSING, "Refining with Gemini...")
        self.tray.update_status("⚡ Processing with Gemini...", state="processing")

        # 4. Dispatch background AI worker thread
        threading.Thread(
            target=self._process_speech_worker,
            args=(wav_bytes, duration),
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
        """Triggered globally when user presses Ctrl + Shift + P to enhance highlighted text or clipboard into an AI Prompt."""
        if self.is_busy_processing:
            return

        time.sleep(0.06)
        self.text_injector.capture_active_window()

        # 1. First priority: Capture highlighted / selected text on screen
        raw_text = self.text_injector.get_selected_text()

        # 2. Fallback: Check active clipboard
        if not raw_text or len(raw_text.strip()) < 2:
            try:
                raw_text = pyperclip.paste()
            except Exception:
                raw_text = ""

        # 3. Fallback: If nothing selected or copied, show error and do NOT start voice dictation
        if not raw_text or len(raw_text.strip()) < 2:
            logger.info("No text selected or in clipboard for prompt transform.")
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

            # Safe paste with normal speech safeguard on clipboard
            if self.config.get("auto_paste", True):
                paste_ok = self.text_injector.paste_text(prompt_or_error, leave_in_clipboard=raw_text if raw_text else None)
                if paste_ok:
                    self.hud.show_state(FloatingHUD.STATE_PASTED, "AI Prompt Pasted! (Raw in Clipboard 📋)")
                else:
                    if raw_text:
                        pyperclip.copy(raw_text)
                    self.hud.show_state(FloatingHUD.STATE_COPIED, "Prompt & Text Saved!")
            else:
                if raw_text:
                    pyperclip.copy(raw_text)
                else:
                    pyperclip.copy(prompt_or_error)
                self.hud.show_state(FloatingHUD.STATE_COPIED, "Raw Text in Clipboard (Prompt Saved)!")

            disp_name = self.config.get("hotkey_display", "Ctrl + Win")
            self.tray.update_status(f"🟢 Ready ({disp_name})", state="ready")
        else:
            self.hud.show_state(FloatingHUD.STATE_ERROR, prompt_or_error[:35])
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

    def _process_speech_worker(self, wav_bytes: bytes, duration: float):
        """Runs in background thread with Application Context, Profile routing, Intent classification, and resilient Gemini execution."""
        try:
            if self._is_cancelled:
                return

            api_key = self.config.get_api_key()
            offline_fallback_on = self.config.get_offline_fallback_enabled() if hasattr(self.config, "get_offline_fallback_enabled") else self.config.get("offline_fallback_enabled", True)

            if not api_key and not offline_fallback_on:
                self.signals.finished.emit(False, "Missing Gemini API Key. Open Settings.", duration, "clean_dictation", "General", "", "")
                return

            self.gemini.set_api_key(api_key)

            # 1. Resolve Application Context & Dynamic Profile
            target_hwnd = getattr(self.text_injector, "last_target_hwnd", None)
            app_context = AppIntelligenceManager.get_active_app_context(target_hwnd)
            app_name = app_context.app_name if app_context else self.text_injector.get_target_app_name()
            category = getattr(app_context, "category", "general") if app_context else "general"

            # 2. Voice Dictation Mode: Strictly adhere to user's configured mode_preset (default: clean_dictation)
            # Never force-override voice dictation to prompt_enhancer or code_assistant based on foreground apps.
            active_profile = app_context.profile_id if (app_context and app_context.profile_id) else self.config.get("active_profile", "coding")
            active_mode = self.config.get("mode_preset", "clean_dictation")

            auto_cost_mode = self.config.get("auto_cost_mode", True)
            logger.info(f"Dynamic Context: App='{app_name}', Category='{category}', Profile='{active_profile}', Mode='{active_mode}'")

            # In-memory sync of active profile
            self.config.config["active_profile"] = active_profile

            # 3. Construct Active Speech Transcription System Prompt
            prompt = self.config.get_system_prompt(preset_override=active_mode, app_context=app_context, profile_id_override=active_profile)

            # 4. Transcribe with Gemini / Whisper
            # If rolling streaming chunks were accumulated during speech (> 16s recording)
            with self._rolling_lock:
                has_rolling = bool(self._rolling_chunks)

            if has_rolling:
                logger.info(f"Processing rolling streaming dictation ({len(self._rolling_chunks)} chunks accumulated during speech)...")
                tail_wav = self.recorder.get_tail_chunk()
                if tail_wav and len(tail_wav) > 2000:
                    with self._rolling_lock:
                        tail_idx = len(self._rolling_chunks)
                        self._rolling_chunks.append("")
                    try:
                        ok_tail, txt_tail = self.gemini.transcribe_audio(
                            wav_bytes=tail_wav,
                            system_instruction=prompt,
                            app_context=app_context,
                            profile_id=active_profile,
                            auto_cost_mode=auto_cost_mode,
                            offline_fallback_enabled=offline_fallback_on
                        )
                        if ok_tail and txt_tail:
                            with self._rolling_lock:
                                if tail_idx < len(self._rolling_chunks):
                                    self._rolling_chunks[tail_idx] = txt_tail.strip()
                    except Exception as tail_ex:
                        logger.debug(f"Tail chunk note: {tail_ex}")

                # Wait briefly for in-flight rolling chunks to complete (max 3.5s)
                t_wait_start = time.time()
                while time.time() - t_wait_start < 3.5:
                    with self._rolling_lock:
                        all_done = all(len(c) > 0 for c in self._rolling_chunks)
                    if all_done:
                        break
                    time.sleep(0.08)

                with self._rolling_lock:
                    valid_chunks = [c.strip() for c in self._rolling_chunks if c and c.strip()]

                if valid_chunks:
                    raw_result = " ".join(valid_chunks).strip()
                    success = True
                else:
                    success, raw_result = self.gemini.transcribe_audio(
                        wav_bytes=wav_bytes,
                        system_instruction=prompt,
                        app_context=app_context,
                        profile_id=active_profile,
                        auto_cost_mode=auto_cost_mode,
                        offline_fallback_enabled=offline_fallback_on
                    )
            else:
                # Standard path for short speech (< 16s)
                success, raw_result = self.gemini.transcribe_audio(
                    wav_bytes=wav_bytes,
                    system_instruction=prompt,
                    app_context=app_context,
                    profile_id=active_profile,
                    auto_cost_mode=auto_cost_mode,
                    offline_fallback_enabled=offline_fallback_on
                )

            if self._is_cancelled:
                return

            if not success:
                self.signals.finished.emit(False, raw_result or "Transcription failed.", duration, active_mode, app_name, self.gemini.last_model_used, "")
                return

            # Clean silence detection (no words spoken)
            if not raw_result or not raw_result.strip():
                self.signals.finished.emit(True, "", duration, active_mode, app_name, self.gemini.last_model_used, "")
                return

            # 5. Apply Custom Dictionary, Snippets & Vocabulary to transcribe speech accurately
            final_text = GeminiEngine.apply_dictionary(raw_result, self.config.get_dictionary())
            final_text = GeminiEngine.apply_snippets(final_text, self.config.get_snippets())
            raw_spoken_text = final_text

            model_used = self.gemini.last_model_used or "gemini-2.5-flash"
            self.signals.finished.emit(True, final_text, duration, active_mode, app_name, model_used, raw_spoken_text)

        except Exception as e:
            logger.error(f"Error in speech processing worker: {e}", exc_info=True)
            self.signals.finished.emit(False, f"Error: {str(e)}", duration, "clean_dictation", "General", "gemini-2.5-flash", "")

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
                prompt=text_or_error if mode == "prompt_generation" else ""
            )
            if self.settings_dialog and self.settings_dialog.isVisible():
                self.settings_dialog.notify_history_changed()
                active_prof = self.config.get("active_profile", "coding")
                self.settings_dialog.sync_active_profile(active_prof)

            # 3. AI Prompt Pasting & Safeguard Normal Speech Clipboard Management:
            is_prompt_mode = (mode == "prompt_generation" and raw_spoken_text and raw_spoken_text.strip() != text_or_error.strip())
            is_offline_mode = "offline" in (model_used or "").lower()

            if self.config.get("auto_paste", True):
                if is_prompt_mode:
                    paste_ok = self.text_injector.paste_text(text_or_error, leave_in_clipboard=raw_spoken_text)
                    if paste_ok:
                        self.hud.show_state(FloatingHUD.STATE_PASTED, "AI Prompt Pasted! (Speech in Clipboard 📋)")
                    else:
                        pyperclip.copy(raw_spoken_text)
                        self.hud.show_state(FloatingHUD.STATE_COPIED, "Normal Speech Copied (Backup) 📋")
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

            # 2. Maximum recording duration safety net (auto-stop after 1800s / 30 mins)
            if hasattr(self, 'recorder') and self.recorder and self.recorder.is_recording:
                elapsed = time.time() - self.recorder.start_time
                if elapsed > 1800.0:
                    logger.warning(f"Recording reached 30-minute safety limit ({elapsed:.1f}s). Auto-stopping.")
                    self.on_stop_speech()

            # 3. Detect codebase changes on disk while idle (e.g. after code edits/updates)
            if hasattr(self, '_startup_code_mtime') and self._startup_code_mtime > 0:
                latest_code_mtime = get_codebase_last_modified()
                if latest_code_mtime > self._startup_code_mtime + 2.0:
                    if not (hasattr(self, 'recorder') and self.recorder and self.recorder.is_recording) and not self.is_busy_processing:
                        logger.info("Codebase modified on disk while running! Auto-reloading Gemini Flow to apply updates...")
                        self.restart_app()
                        return
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
                        try:
                            client.write(b"OK\n")
                            client.flush()
                        except Exception:
                            pass
                        self.open_settings()
                        if hasattr(self, 'hud') and self.hud:
                            self.hud.show_state(FloatingHUD.STATE_READY, "Gemini Flow — Voice AI Ready 🎙️")
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
        self.gemini.set_model(self.config.get("model_mode", "auto"))
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
        self.settings_dialog = None
        # Reload hotkey settings in listener
        hotkey = self.config.get("hotkey", "<ctrl>+<space>")
        mode = self.config.get("hotkey_mode", "toggle")
        prompt_hk = self.config.get("prompt_hotkey", "<ctrl>+<shift>+p")
        trans_hk = self.config.get("transform_hotkey", "<ctrl>+<shift>+t")
        disp_name = self.config.get("hotkey_display", "Ctrl + Space")

        self.hotkey_mgr.update_config(hotkey, mode, prompt_hk, trans_hk)
        self.gemini.set_api_key(self.config.get_api_key())
        self.gemini.set_model(self.config.get("model_mode", "auto"))
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
    is_force_restart = any(f in args for f in ("--force-restart", "--restart", "-r", "-f"))

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

        # Check if codebase was updated on disk since the running instance started
        code_mtime = get_codebase_last_modified()
        pid_mtime = 0.0
        if PID_FILE.exists():
            try:
                with open(PID_FILE, "r", encoding="utf-8") as f:
                    c = f.read().strip()
                    if ":" in c:
                        pid_mtime = float(c.split(":")[1])
                    else:
                        pid_mtime = PID_FILE.stat().st_mtime
            except Exception:
                pid_mtime = PID_FILE.stat().st_mtime

        if code_mtime > pid_mtime + 1.0 and pid_mtime > 0:
            logger.info("Codebase has been updated on disk since the running instance started! Recycling old instance to load fresh code...")
            terminate_other_gemini_flow_instances()
            release_app_mutex()
            time.sleep(0.3)
            continue

        # Check if an existing primary instance is actually responsive
        notified = notify_running_instance("SHOW")
        if notified and show_window:
            # Verify that the dashboard window actually became visible on screen
            window_visible = False
            for _ in range(10):
                time.sleep(0.1)
                if is_dashboard_window_visible():
                    window_visible = True
                    break
            if window_visible:
                logger.info("Gemini Flow is already running and dashboard was brought to front.")
                sys.exit(0)
            else:
                logger.warning("Existing instance failed to display visible dashboard on screen. Recycling old instance to guarantee app opens...")
                terminate_other_gemini_flow_instances()
                release_app_mutex()
                time.sleep(0.3)
                continue
        elif notified and not show_window:
            logger.info("Gemini Flow is already running in background.")
            sys.exit(0)
        else:
            logger.warning(f"Named Mutex held by unresponsive instance (attempt {attempt+1}/4). Purging zombie processes...")
            terminate_other_gemini_flow_instances()
            release_app_mutex()
            try:
                QLocalServer.removeServer(IPC_PIPE_NAME)
            except Exception:
                pass
            time.sleep(0.4)

    app = GeminiFlowApp()
    sys.exit(app.run(show_window=show_window))


if __name__ == "__main__":
    start_app()

