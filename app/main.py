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


def write_pid_file():
    """Writes current process ID to PID file for zombie recovery."""
    try:
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        logger.debug(f"Could not write PID file: {e}")


def remove_pid_file():
    """Removes PID file on clean shutdown."""
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception:
        pass


def kill_zombie_process_if_any():
    """Kills any stuck or unresponsive background instance identified in PID file."""
    if not PID_FILE.exists():
        return
    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            old_pid = int(f.read().strip())
        if old_pid != os.getpid():
            import subprocess
            logger.warning(f"Cleaning up unresponsive zombie Gemini Flow process (PID {old_pid})...")
            subprocess.run(["taskkill", "/F", "/PID", str(old_pid)], capture_output=True)
            time.sleep(0.3)
    except Exception as e:
        logger.debug(f"Zombie process cleanup note: {e}")
    finally:
        remove_pid_file()


def notify_running_instance(command: str = "SHOW") -> bool:
    """Notifies the already running instance to perform an action (e.g. SHOW, RESTART)."""
    socket = QLocalSocket()
    socket.connectToServer(IPC_PIPE_NAME)
    if socket.waitForConnected(1200):
        socket.write(f"{command}\n".encode("utf-8"))
        socket.waitForBytesWritten(800)
        # Wait for acknowledgment
        if socket.waitForReadyRead(1000):
            socket.readAll()
        socket.disconnectFromServer()

        if command == "SHOW":
            # In addition, find the window directly and switch to it
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.FindWindowW(None, "Gemini Flow — Voice AI Settings & Dashboard")
                if hwnd:
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE = 9
                    user32.SwitchToThisWindow(hwnd, True)
                    user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
        return True
    return False


def force_window_to_foreground(window):
    """
    Guarantees a PyQt window is un-minimized, restored, and forced to the foreground
    over active apps (Edge, Chrome, Antigravity, etc.) using native Win32 APIs without recreating window flags.
    """
    if not window:
        return
    window.showNormal()
    window.show()
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = int(window.winId())
        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_RESTORE)

        fore_hwnd = user32.GetForegroundWindow()
        cur_thread = user32.GetCurrentThreadId()
        fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None)
        if fore_thread != cur_thread and fore_thread != 0:
            user32.AttachThreadInput(fore_thread, cur_thread, True)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            user32.AttachThreadInput(fore_thread, cur_thread, False)
        else:
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
    except Exception:
        pass
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
from .intent.intent_system import IntentClassifier, IntentCategory
from .transformation.transform_engine import TransformType, TransformEngine
from .profiles.profile_manager import ProfileManager
from .reliability.fallback_handler import FallbackHandler

# Configure logging
import logging.handlers
log_file = Path(os.environ.get("APPDATA", Path.home())) / "GeminiFlow" / "gemini_flow.log"
log_file.parent.mkdir(parents=True, exist_ok=True)
handlers = [logging.handlers.RotatingFileHandler(str(log_file), maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8")]
if sys.stdout is not None:
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
            hotkey_str=self.config.get("hotkey", "<ctrl>+<cmd>"),
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
        self.server.listen(IPC_PIPE_NAME)

        # Standby / Sleep / Inactivity Watchdog Timer (fires every 5 seconds)
        from PyQt6.QtCore import QTimer
        self._last_watchdog_time = time.time()
        self.watchdog_timer = QTimer(self.app)
        self.watchdog_timer.timeout.connect(self._on_watchdog_tick)
        self.watchdog_timer.start(5000)

        self.is_busy_processing = False
        self._is_cancelled = False

    def _on_watchdog_tick(self):
        """Periodic background health-check watchdog (every 5 seconds)."""
        try:
            # 1. Check keyboard hook health after Windows Sleep / Screen Lock
            self.hotkey_mgr.check_health()

            # 2. Maximum recording duration safety net (auto-stop after 300s / 5 mins)
            if self.recorder.is_recording:
                elapsed = time.time() - self.recorder.start_time
                if elapsed > 300.0:
                    logger.warning(f"Recording reached 5-minute safety limit ({elapsed:.1f}s). Auto-stopping to prevent memory leak.")
                    self.on_stop_speech()
        except Exception as e:
            logger.debug(f"Watchdog tick note: {e}")

    def _on_audio_amplitude(self, amp: float):
        if self.recorder.is_recording:
            self.hud.update_volume(amp)

    def on_start_speech(self):
        """Triggered globally when user presses hotkey to speak."""
        if self.is_busy_processing:
            logger.warning("Still processing previous speech, ignoring new start.")
            return

        self._is_cancelled = False
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
        else:
            self.hud.show_state(FloatingHUD.STATE_ERROR, "Microphone Error")
            self.tray.update_status("⚠️ Mic Error", state="ready")

    def on_stop_speech(self):
        """Triggered globally when user stops hotkey."""
        if not self.recorder.is_recording:
            return

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
        self.is_busy_processing = False
        self.hotkey_mgr.set_recording_state(False)
        self.hotkey_mgr.set_processing_state(False)

        if self.recorder.is_recording:
            self.recorder.stop_recording()

        self.signals.cancelled.emit()

    def _on_speech_cancelled(self):
        """UI Thread handler for speech cancellation."""
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

        # 3. Fallback: If nothing selected or copied, start voice dictation
        if not raw_text or len(raw_text.strip()) < 2:
            logger.info("No text selected or in clipboard for prompt transform, starting prompt voice dictation...")
            self.on_start_speech()
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
            model = self.gemini.last_model_used or self.config.get("model_name", "gemini-3.5-flash-lite")
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
            model = self.gemini.last_model_used or self.config.get("model_name", "gemini-3.5-flash-lite")
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

            # 1. Resolve Application Context
            app_context = AppIntelligenceManager.get_active_app_context()
            app_name = app_context.app_name if app_context else self.text_injector.get_target_app_name()

            # 2. Resolve Active Productivity Profile & Cost Mode
            active_profile = self.config.get("active_profile", "coding")
            auto_cost_mode = self.config.get("auto_cost_mode", True)

            # 3. Construct Clean Speech Transcription System Prompt
            # When transcribing audio, we ALWAYS use clean dictation to guarantee that
            # raw_spoken_text captures the exact normal words spoken by the user.
            prompt = self.config.get_system_prompt(preset_override="clean_dictation", app_context=app_context)

            # 4. Transcribe with Gemini (Resilient execution + ModelRouter + Cost Optimization + Offline Fallback)
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

            if not success or not raw_result:
                self.signals.finished.emit(False, raw_result or "Transcription failed.", duration, "clean_dictation", app_name, self.gemini.last_model_used, "")
                return

            # Apply Custom Dictionary & Snippet Expansions to normal speech
            raw_spoken_text = GeminiEngine.apply_dictionary(raw_result, self.config.get_dictionary())
            raw_spoken_text = GeminiEngine.apply_snippets(raw_spoken_text, self.config.get_snippets())

            mode = "clean_dictation"
            final_text = raw_spoken_text

            # 5. Check if active window is a Prompt-Generation Interface (Antigravity, VS Code, Windsurf, Cursor, etc.)
            auto_prompt_enabled = self.config.get_auto_prompt_conversion() if hasattr(self.config, "get_auto_prompt_conversion") else self.config.get("auto_prompt_conversion", False)
            is_prompt_ui = getattr(app_context, "is_prompt_interface", False) and auto_prompt_enabled
            if is_prompt_ui:
                logger.info(f"Active window '{app_name}' is a Prompt-Generation Interface: Converting speech to structured prompt.")
                prompt_instruction = (
                    "You are an expert AI Prompt Engineer. The user dictated raw speech intended as an instruction/prompt for an AI system:\n"
                    f"<spoken_instruction>{raw_spoken_text}</spoken_instruction>\n\n"
                    "Transform this raw speech into an exceptionally clear, comprehensive, and high-impact AI prompt. "
                    "Structure the prompt logically with:\n"
                    "- Role & Objective: Define the specific persona and primary goal\n"
                    "- Context & Requirements: Clear constraints, guidelines, and specifications\n"
                    "- Step-by-Step Instructions: Logical numbered steps to follow\n"
                    "- Expected Output Format: Concrete structure\n"
                    "Output ONLY the finalized optimized prompt without any preamble, markdown code fence wrapping the whole response, or commentary."
                )
                try:
                    trans_res = self.gemini.transform_text(
                        raw_text=raw_spoken_text,
                        transform_type=TransformType.CONVERT_PROMPT,
                        app_context=app_context,
                        custom_instruction=prompt_instruction,
                        profile_id=active_profile,
                        auto_cost_mode=auto_cost_mode
                    )
                    if trans_res.success and trans_res.text:
                        final_text = trans_res.text.strip()
                        mode = "prompt_generation"
                    else:
                        final_text = raw_spoken_text
                except Exception as p_err:
                    logger.warning(f"Prompt generation fallback to raw speech: {p_err}")
                    final_text = raw_spoken_text
            else:
                # 6. General Code Editors / IDEs / Text Fields: Intent check or Raw Clean Transcription
                active_clip = ""
                try:
                    active_clip = pyperclip.paste()
                except Exception:
                    active_clip = ""

                intent_result = IntentClassifier.classify(raw_result, clipboard_fallback=active_clip)
                if intent_result.intent != IntentCategory.DICTATE and intent_result.payload:
                    logger.info(f"Voice Command Detected: {intent_result.intent.value} with payload length {len(intent_result.payload)}")
                    matched_transform = TransformType.IMPROVE
                    try:
                        matched_transform = TransformType[intent_result.intent.value]
                    except Exception:
                        pass

                    trans_res = self.gemini.transform_text(
                        raw_text=intent_result.payload,
                        transform_type=matched_transform,
                        app_context=app_context,
                        custom_instruction=intent_result.system_instruction,
                        profile_id=active_profile
                    )
                    if trans_res.success and trans_res.text:
                        final_text = trans_res.text
                        mode = intent_result.intent.value
                else:
                    # Apply Custom Dictionary & Snippet Expansions for normal code/text dictation
                    final_text = GeminiEngine.apply_dictionary(final_text, self.config.get_dictionary())
                    final_text = GeminiEngine.apply_snippets(final_text, self.config.get_snippets())

            model_used = self.gemini.last_model_used or self.config.get("model_name", "gemini-3.5-flash-lite")
            self.signals.finished.emit(True, final_text, duration, mode, app_name, model_used, raw_spoken_text)

        except Exception as e:
            logger.error(f"Error in speech processing worker: {e}", exc_info=True)
            self.signals.finished.emit(False, f"Error: {str(e)}", duration, "clean_dictation", "General", "", "")

    def _on_transcription_finished(
        self,
        success: bool,
        text_or_error: str,
        duration: float,
        mode: str = "clean_dictation",
        app_name: str = "General",
        model_used: str = "gemini-3.5-flash-lite",
        raw_spoken_text: str = ""
    ):
        """Back on main Qt UI thread."""
        self.is_busy_processing = False
        self.hotkey_mgr.set_processing_state(False)

        if self._is_cancelled:
            return

        if success and text_or_error:
            logger.info(f"Final Processed Text [{mode}]: {text_or_error[:100]}...")

            # 1. Persistent History Logging:
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

            # 2. AI Prompt Pasting & Safeguard Normal Speech Clipboard Management:
            # When prompt generation is active (e.g. in Antigravity, VS Code, Windsurf, Cursor),
            # paste the structured AI Prompt into the active chat/editor, then immediately set
            # the clipboard to the exact normal spoken text (as dictated) as a safeguard backup.
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

            disp_name = self.config.get("hotkey_display", "Ctrl + Win")
            self.tray.update_status(f"🟢 Ready ({disp_name})", state="ready")

        else:
            logger.warning(f"Transcription failed: {text_or_error}")
            self.hud.show_state(FloatingHUD.STATE_ERROR, text_or_error[:35])
            self.tray.update_status("⚠️ Transcription Failed", state="ready")

    def _on_watchdog_tick(self):
        """Monitors system sleep/resume and keyboard listener health."""
        now = time.time()
        # If interval exceeds 12s, laptop was suspended/asleep or clock jumped
        if now - self._last_watchdog_time > 12.0:
            logger.info("System resumed from sleep or standby. Reinitializing keyboard listener...")
            self.hotkey_mgr.restart()
            self.hotkey_mgr.reset_keys()
        else:
            self.hotkey_mgr.check_health()
        self._last_watchdog_time = now

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
        force_window_to_foreground(self.settings_dialog)

    def _on_settings_applied(self):
        """Called live when user clicks 'Save & Apply Changes' without closing dialog."""
        hotkey = self.config.get("hotkey", "<ctrl>+<cmd>")
        mode = self.config.get("hotkey_mode", "toggle")
        prompt_hk = self.config.get("prompt_hotkey", "<ctrl>+<shift>+p")
        trans_hk = self.config.get("transform_hotkey", "<ctrl>+<shift>+t")
        disp_name = self.config.get("hotkey_display", "Ctrl + Win")

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
        hotkey = self.config.get("hotkey", "<ctrl>+<cmd>")
        mode = self.config.get("hotkey_mode", "toggle")
        prompt_hk = self.config.get("prompt_hotkey", "<ctrl>+<shift>+p")
        trans_hk = self.config.get("transform_hotkey", "<ctrl>+<shift>+t")
        disp_name = self.config.get("hotkey_display", "Ctrl + Win")

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
            self.server.close()
            QLocalServer.removeServer(IPC_PIPE_NAME)
        except Exception:
            pass
        release_app_mutex()
        remove_pid_file()
        self.app.quit()

    def restart_app(self):
        """Cleanly releases all resources and launches a fresh Gemini Flow instance."""
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
        launcher = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main_standalone.py")
        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000
        flags = DETACHED_PROCESS | CREATE_NO_WINDOW
        try:
            subprocess.Popen([python_exe, launcher], creationflags=flags, close_fds=True)
        except Exception as e:
            logger.error(f"Failed to spawn detached process: {e}")
            subprocess.Popen([python_exe, launcher])

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

        # Show Dashboard window on launch
        if show_window:
            self.open_settings()

        try:
            return self.app.exec()
        finally:
            remove_pid_file()
            release_app_mutex()


def start_app(show_window: bool = True):
    from PyQt6.QtWidgets import QApplication
    # Check CLI flags
    args = sys.argv[1:]
    if "--restart" in args or "-r" in args:
        logger.info("Restart flag passed. Notifying running instance to restart...")
        if notify_running_instance(command="RESTART"):
            time.sleep(0.5)
            sys.exit(0)

    if "--startup" in args or "-s" in args or "--hidden" in args:
        show_window = False

    init_app = QApplication.instance() or QApplication(sys.argv)

    # 1. Enforce atomic single-instance via Named Mutex + live IPC check + Zombie Recovery
    is_primary = acquire_app_mutex()
    if not is_primary:
        # Check if the primary instance is actually alive and responsive
        notified = notify_running_instance("SHOW")
        if notified:
            logger.info("Gemini Flow is already running. Existing instance brought to front.")
            sys.exit(0)
        else:
            logger.warning("Named Mutex was held by an unresponsive or dead instance. Performing zombie recovery...")
            kill_zombie_process_if_any()
            release_app_mutex()
            try:
                QLocalServer.removeServer(IPC_PIPE_NAME)
            except Exception:
                pass
            time.sleep(0.2)
            acquire_app_mutex()

    # 2. Check and sync Windows Startup setting & Desktop Shortcuts
    try:
        cfg = ConfigManager()
        if cfg.get("start_with_windows", True):
            setup_windows_startup(True)
        ensure_desktop_shortcuts()
    except Exception as e:
        logger.warning(f"Could not verify Windows startup registry or shortcuts: {e}")

    app = GeminiFlowApp()
    sys.exit(app.run(show_window=show_window))


if __name__ == "__main__":
    start_app()

