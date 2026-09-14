"""
System Tray Manager for Gemini Flow (PyQt6)
Provides background presence, quick status, settings access, and context menu.
"""
import logging
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QAction

logger = logging.getLogger("GeminiFlow.TrayIcon")


def create_mic_pixmap(color: QColor = QColor(99, 102, 241), size: int = 64) -> QPixmap:
    """Dynamically creates a high-res glowing microphone tray icon without external assets."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Base circle background
    painter.setBrush(QBrush(QColor(15, 23, 42)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, size - 8, size - 8, 14, 14)

    # Microphone capsule
    painter.setBrush(QBrush(color))
    painter.drawRoundedRect(size // 2 - 8, 14, 16, 26, 8, 8)

    # Mic stand cradle arc
    pen = painter.pen()
    pen.setColor(color)
    pen.setWidth(4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(size // 2 - 14, 22, 28, 24, 0, -180 * 16)

    # Mic stem & base
    painter.drawLine(size // 2, 46, size // 2, 54)
    painter.drawLine(size // 2 - 10, 54, size // 2 + 10, 54)

    painter.end()
    return pixmap


class SystemTrayManager(QSystemTrayIcon):
    def __init__(self, main_app, parent=None):
        self.main_app = main_app
        self.icon_ready = QIcon(create_mic_pixmap(QColor(99, 102, 241)))      # Indigo
        self.icon_recording = QIcon(create_mic_pixmap(QColor(239, 68, 68)))  # Red
        self.icon_processing = QIcon(create_mic_pixmap(QColor(168, 85, 247))) # Purple

        super().__init__(self.icon_ready, parent)
        self.setToolTip("Gemini Flow — AI Voice Dictation (Ready)")

        self._init_menu()
        self.activated.connect(self._on_tray_activated)

    def _init_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QMenu::item {
                padding: 8px 24px 8px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #334155;
                color: #38BDF8;
            }
            QMenu::separator {
                height: 1px;
                background: #334155;
                margin: 4px 8px;
            }
        """)

        # Status Header Action (Disabled)
        self.action_status = QAction("🟢 Gemini Flow: Ready", menu)
        self.action_status.setEnabled(False)
        menu.addAction(self.action_status)

        menu.addSeparator()

        # Settings
        action_settings = QAction("⚙️ Settings & Configuration", menu)
        action_settings.triggered.connect(self.main_app.open_settings)
        menu.addAction(action_settings)

        # History
        action_history = QAction("📜 Transcription History", menu)
        action_history.triggered.connect(self.main_app.open_history)
        menu.addAction(action_history)

        # Cost & Productivity
        action_cost = QAction("💰 Cost & Productivity", menu)
        action_cost.triggered.connect(self.main_app.open_cost_dashboard)
        menu.addAction(action_cost)

        menu.addSeparator()

        # Mode quick switch
        self.action_toggle_mode = QAction("Switch to Push-to-Talk", menu)
        self.action_toggle_mode.triggered.connect(self._toggle_mode_quick)
        menu.addAction(self.action_toggle_mode)

        # AI Prompt Auto-Conversion quick switch
        is_prompt_on = self.main_app.config.get("auto_prompt_conversion", False)
        self.action_toggle_prompt = QAction("✨ AI Prompt Mode (Active in IDEs)" if is_prompt_on else "🗣️ Pure Speech Mode (Active Everywhere)", menu)
        self.action_toggle_prompt.triggered.connect(self._toggle_prompt_mode_quick)
        menu.addAction(self.action_toggle_prompt)

        menu.addSeparator()

        # Restart
        action_restart = QAction("🔄 Restart Gemini Flow", menu)
        action_restart.triggered.connect(self.main_app.restart_app)
        menu.addAction(action_restart)

        # Exit
        action_exit = QAction("❌ Exit Gemini Flow", menu)
        action_exit.triggered.connect(self.main_app.quit_app)
        menu.addAction(action_exit)

        self.setContextMenu(menu)

    def update_status(self, text: str, state: str = "ready"):
        self.action_status.setText(f"● {text}")
        if state == "recording":
            self.setIcon(self.icon_recording)
            self.setToolTip(f"Gemini Flow — {text}")
        elif state == "processing":
            self.setIcon(self.icon_processing)
            self.setToolTip(f"Gemini Flow — {text}")
        else:
            self.setIcon(self.icon_ready)
            self.setToolTip(f"Gemini Flow — {text}")

    def _toggle_mode_quick(self):
        curr = self.main_app.config.get("hotkey_mode", "toggle")
        new_mode = "push_to_talk" if curr == "toggle" else "toggle"
        self.main_app.config.set("hotkey_mode", new_mode)
        self.action_toggle_mode.setText("Switch to Toggle Mode" if new_mode == "push_to_talk" else "Switch to Push-to-Talk")
        self.main_app.hotkey_mgr.update_config(
            self.main_app.config.get("hotkey", "<ctrl>+<cmd>"),
            new_mode,
            self.main_app.config.get("prompt_hotkey", "<ctrl>+<shift>+p")
        )

    def _toggle_prompt_mode_quick(self):
        curr = self.main_app.config.get("auto_prompt_conversion", False)
        new_val = not curr
        self.main_app.config.set("auto_prompt_conversion", new_val)
        self.action_toggle_prompt.setText("✨ AI Prompt Mode (Active in IDEs)" if new_val else "🗣️ Pure Speech Mode (Active Everywhere)")
        if hasattr(self.main_app, "hud") and self.main_app.hud:
            from .floating_hud import FloatingHUD
            msg = "Mode: AI Prompt Engineer ✨" if new_val else "Mode: Pure Speech Dictation 🗣️"
            self.main_app.hud.show_state(FloatingHUD.STATE_READY, msg)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.main_app.open_settings()
