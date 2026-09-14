"""
Floating HUD Pill Widget for Gemini Flow (PyQt6)
Provides real-time feedback with live audio waveform, status indicator, and glassmorphic styling.
"""
import math
import logging
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QApplication, QMenu
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QPainterPath, QLinearGradient

logger = logging.getLogger("GeminiFlow.FloatingHUD")


class AudioWaveWidget(QWidget):
    """Animated sound wave bars with glowing gradient reacting dynamically to mic volume."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(58, 26)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.num_bars = 5
        self.bar_heights = [5.0] * self.num_bars
        self.target_amplitude = 0.0
        self.phase = 0.0

        # 60 FPS fluid animation timer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animate_bars)
        self.anim_timer.start(16)

    def set_amplitude(self, amp: float):
        self.target_amplitude = max(0.08, min(1.0, amp))

    def _animate_bars(self):
        self.phase += 0.16
        base_h = 5.0
        max_h = 22.0
        amp = self.target_amplitude

        for i in range(self.num_bars):
            offset = math.sin(self.phase + (i * 0.85)) * 0.5 + 0.5
            target = base_h + (max_h - base_h) * amp * (0.35 + 0.65 * offset)
            self.bar_heights[i] += (target - self.bar_heights[i]) * 0.28

        # Smooth volume decay
        self.target_amplitude = max(0.08, self.target_amplitude * 0.93)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bar_width = 3.6
        spacing = 5.2
        total_w = self.num_bars * bar_width + (self.num_bars - 1) * spacing
        start_x = (self.width() - total_w) / 2
        center_y = self.height() / 2

        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(self.num_bars):
            h = self.bar_heights[i]
            x = start_x + i * (bar_width + spacing)
            y = center_y - (h / 2)

            # Luminous gradient (Electric Indigo to Cyan)
            grad = QLinearGradient(x, y, x, y + h)
            grad.setColorAt(0.0, QColor(99, 102, 241, 255))  # Electric Indigo / Violet
            grad.setColorAt(1.0, QColor(6, 182, 212, 255))   # Luminous Cyan

            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(h), 1.8, 1.8)


class FloatingHUD(QWidget):
    """
    Frameless, 80% translucent 3D glass embossed status emblem.
    Center-aligned waveform, strictly zero text during listening, non-focus-stealing,
    draggable with right-click / left-click and remembers saved screen coordinates.
    """
    # Signals for thread-safe UI updates
    state_signal = pyqtSignal(str, str)       # (state_name, message)
    amplitude_signal = pyqtSignal(float)      # (volume_amplitude 0.0-1.0)

    STATE_LISTENING = "listening"
    STATE_PROCESSING = "processing"
    STATE_PASTED = "pasted"
    STATE_COPIED = "copied"
    STATE_ERROR = "error"
    STATE_CANCELLED = "cancelled"
    STATE_PROMPT = "prompt"
    STATE_OFFLINE = "offline"

    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.current_state = ""
        self.current_border_color = "rgba(129, 140, 248, 0.55)"

        # Drag state tracking
        self._drag_start_pos = None
        self._drag_offset = None
        self._is_dragging = False

        self._init_window_flags()
        self._init_ui()
        self._setup_signals()

    def _init_window_flags(self):
        # Frameless, Always on Top, Tool window (hidden from taskbar), DOES NOT STEAL FOCUS!
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)

    def _init_ui(self):
        self.setFixedHeight(40)
        self.setFixedWidth(115)

        # Strictly Center-Aligned Layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(12, 4, 12, 4)
        self.main_layout.setSpacing(8)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Centered Waveform Widget
        self.wave_widget = AudioWaveWidget(self)
        self.main_layout.addWidget(self.wave_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status Icon Label (for processing/success/error icons)
        self.status_icon = QLabel("⚡", self)
        self.status_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.status_icon.setStyleSheet("font-size: 15px; color: #818CF8; border: none; background: transparent;")
        self.status_icon.hide()
        self.main_layout.addWidget(self.status_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status Text Label (used strictly for brief confirmation/error messages, hidden in listening)
        self.status_label = QLabel("", self)
        self.status_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
        self.status_label.setFont(font)
        self.status_label.setStyleSheet("color: #F3F4F6; border: none; background: transparent;")
        self.status_label.hide()
        self.main_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Auto-hide timer for success/error/cancellation states
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_smooth)

    def _setup_signals(self):
        self.state_signal.connect(self._handle_state_change)
        self.amplitude_signal.connect(self.wave_widget.set_amplitude)

    def reposition(self, force_default: bool = False):
        """
        Positions the 3D glass pill at user's saved custom position or bottom-center.
        Guarantees coordinates are bounded within visible screen geometry.
        """
        custom_x = self.config.get("hud_custom_x")
        custom_y = self.config.get("hud_custom_y")

        if not force_default and custom_x is not None and custom_y is not None:
            try:
                cx = int(custom_x)
                cy = int(custom_y)
                # Verify coordinates intersect any connected monitor
                for screen in QApplication.screens():
                    geo = screen.availableGeometry()
                    if (geo.x() - self.width() + 30 <= cx <= geo.x() + geo.width() - 30 and
                        geo.y() - 10 <= cy <= geo.y() + geo.height() - 20):
                        self.move(cx, cy)
                        return
            except Exception as e:
                logger.debug(f"Reposition custom coordinates check: {e}")

        # Default: Bottom-center of primary monitor (55px above taskbar)
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + geo.height() - self.height() - 55
        self.move(x, y)

    def _resize_and_anchor(self, new_w: int, new_h: int = 40):
        """Resizes the HUD while anchoring its horizontal center point."""
        old_w = self.width()
        old_x = self.x()
        old_y = self.y()

        self.setFixedSize(new_w, new_h)

        # If already visible, keep centered around current anchor
        if self.isVisible():
            center_x = old_x + (old_w // 2)
            new_x = center_x - (new_w // 2)
            self.move(new_x, old_y)
        else:
            self.reposition()

    def show_state(self, state: str, message: str = ""):
        """Thread-safe state change trigger."""
        self.state_signal.emit(state, message)

    def update_volume(self, amp: float):
        """Thread-safe volume level update."""
        self.amplitude_signal.emit(amp)

    def _handle_state_change(self, state: str, message: str):
        self.current_state = state
        self.hide_timer.stop()

        if state == self.STATE_LISTENING:
            # ONLY center-aligned wave bars. Strictly NO text!
            self.status_label.hide()
            self.status_icon.hide()
            self.wave_widget.show()
            self._apply_glass_style(border_color="rgba(129, 140, 248, 0.65)")
            self._resize_and_anchor(115, 40)
            self.show()

        elif state == self.STATE_PROCESSING:
            self.wave_widget.hide()
            self.status_icon.setText("⚡")
            self.status_icon.setStyleSheet("font-size: 15px; color: #C084FC; border: none; background: transparent;")
            self.status_icon.show()
            self.status_label.setText(message or "Refining...")
            self.status_label.setStyleSheet("color: #F3E8FF; border: none; background: transparent;")
            self.status_label.show()
            self._apply_glass_style(border_color="rgba(192, 132, 252, 0.70)")
            self._resize_and_anchor(155, 40)
            self.show()

        elif state == self.STATE_PROMPT:
            self.wave_widget.hide()
            self.status_icon.setText("✨")
            self.status_icon.setStyleSheet("font-size: 15px; color: #F59E0B; border: none; background: transparent;")
            self.status_icon.show()
            self.status_label.setText(message or "Prompt Ready")
            self.status_label.setStyleSheet("color: #FEF3C7; border: none; background: transparent;")
            self.status_label.show()
            self._apply_glass_style(border_color="rgba(245, 158, 11, 0.70)")
            self._resize_and_anchor(165, 40)
            self.show()

        elif state == self.STATE_CANCELLED:
            self.wave_widget.hide()
            self.status_icon.setText("🚫")
            self.status_icon.setStyleSheet("font-size: 14px; color: #F87171; border: none; background: transparent;")
            self.status_icon.show()
            self.status_label.setText("Cancelled")
            self.status_label.setStyleSheet("color: #FECACA; border: none; background: transparent;")
            self.status_label.show()
            self._apply_glass_style(border_color="rgba(239, 68, 68, 0.70)")
            self._resize_and_anchor(130, 40)
            self.show()
            self.hide_timer.start(1100)

        elif state == self.STATE_OFFLINE:
            self.wave_widget.hide()
            self.status_icon.setText("🎙️")
            self.status_icon.setStyleSheet("font-size: 14px; color: #38BDF8; border: none; background: transparent;")
            self.status_icon.show()
            msg = message or "Offline Speech (Local)"
            self.status_label.setText(msg)
            self.status_label.setStyleSheet("color: #E0F2FE; border: none; background: transparent;")
            self.status_label.show()
            self._apply_glass_style(border_color="rgba(56, 189, 248, 0.75)")
            fm = self.status_label.fontMetrics()
            needed_w = fm.horizontalAdvance(msg) + 55
            self._resize_and_anchor(max(140, needed_w), 40)
            self.show()
            self.hide_timer.start(1800)

        elif state == self.STATE_PASTED:
            self.wave_widget.hide()
            self.status_icon.setText("✨")
            self.status_icon.setStyleSheet("font-size: 15px; color: #10B981; border: none; background: transparent;")
            self.status_icon.show()
            msg = message or "Pasted!"
            self.status_label.setText(msg)
            self.status_label.setStyleSheet("color: #D1FAE5; border: none; background: transparent;")
            self.status_label.show()
            self._apply_glass_style(border_color="rgba(16, 185, 129, 0.70)")
            fm = self.status_label.fontMetrics()
            needed_w = fm.horizontalAdvance(msg) + 55
            self._resize_and_anchor(max(125, needed_w), 40)
            self.show()
            self.hide_timer.start(1600 if len(msg) > 15 else 1300)

        elif state == self.STATE_COPIED:
            self.wave_widget.hide()
            self.status_icon.setText("📋")
            self.status_icon.setStyleSheet("font-size: 14px; color: #38BDF8; border: none; background: transparent;")
            self.status_icon.show()
            msg = message or "Copied!"
            self.status_label.setText(msg)
            self.status_label.setStyleSheet("color: #E0F2FE; border: none; background: transparent;")
            self.status_label.show()
            self._apply_glass_style(border_color="rgba(56, 189, 248, 0.70)")
            fm = self.status_label.fontMetrics()
            needed_w = fm.horizontalAdvance(msg) + 55
            self._resize_and_anchor(max(130, needed_w), 40)
            self.show()
            self.hide_timer.start(1600 if len(msg) > 15 else 1300)

        elif state == self.STATE_ERROR:
            self.wave_widget.hide()
            self.status_icon.setText("⚠️")
            self.status_icon.setStyleSheet("font-size: 14px; color: #EF4444; border: none; background: transparent;")
            self.status_icon.show()
            msg = message or "Error"
            self.status_label.setText(msg)
            self.status_label.setStyleSheet("color: #FEE2E2; border: none; background: transparent;")
            self.status_label.show()
            self._apply_glass_style(border_color="rgba(239, 68, 68, 0.70)")
            fm = self.status_label.fontMetrics()
            needed_w = fm.horizontalAdvance(msg) + 55
            self._resize_and_anchor(max(135, needed_w), 40)
            self.show()
            self.hide_timer.start(2400)

    def _apply_glass_style(self, border_color: str):
        self.current_border_color = border_color
        self.update()

    def hide_smooth(self):
        self.hide()

    # -------------------------------------------------------------------------
    # Drag & Drop Movement & Right-Click Context Menu
    # -------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_dragging = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos is not None:
            delta = (event.globalPosition().toPoint() - self._drag_start_pos).manhattanLength()
            if delta > 3:
                self._is_dragging = True
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                new_pos = event.globalPosition().toPoint() - self._drag_offset
                self.move(new_pos)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_dragging:
            self._is_dragging = False
            self.unsetCursor()
            # Save custom position permanently to config
            self.config.set("hud_custom_x", self.x())
            self.config.set("hud_custom_y", self.y())
            self.config.set("hud_position", "custom")
            logger.info(f"HUD positioned and saved to ({self.x()}, {self.y()})")
            self._drag_start_pos = None
            event.accept()
            return

        # If user right-clicked without dragging, open context menu
        if event.button() == Qt.MouseButton.RightButton:
            self._drag_start_pos = None
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()
            return

        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self._show_context_menu(event.globalPos())
        event.accept()

    def _show_context_menu(self, global_pos: QPoint):
        """Sleek dark-glass context menu for repositioning and options."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 18px 8px 12px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: #6366F1;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: #334155;
                margin: 4px 6px;
            }
        """)
        action_move = menu.addAction("✥ Move HUD (Drag to reposition)")
        action_reset = menu.addAction("🔄 Reset Position to Bottom-Center")

        chosen = menu.exec(global_pos)
        if chosen == action_move:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            # Brief visual hint
            self.show_state(self.STATE_PROCESSING, "Drag to Place...")
        elif chosen == action_reset:
            self.config.set("hud_custom_x", None)
            self.config.set("hud_custom_y", None)
            self.config.set("hud_position", "bottom_center")
            self.reposition(force_default=True)
            logger.info("HUD position reset to default bottom-center.")

    # -------------------------------------------------------------------------
    # 80% Translucent Glassmorphic Paint Engine
    # -------------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = float(rect.height()) / 2.0

        path = QPainterPath()
        path.addRoundedRect(float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height()), radius, radius)

        # 1. 80% Translucent Glass Fill (Frosted Obsidian Glass with ~20% opacity)
        # Background text and windows remain clearly legible through the glass
        bg_grad = QLinearGradient(0, float(rect.y()), 0, float(rect.y() + rect.height()))
        bg_grad.setColorAt(0.0, QColor(25, 32, 48, 48))    # ~19% opacity upper sheen
        bg_grad.setColorAt(0.5, QColor(14, 18, 28, 52))    # ~20% opacity body
        bg_grad.setColorAt(1.0, QColor(8, 10, 18, 58))     # ~22% opacity base
        painter.fillPath(path, QBrush(bg_grad))

        # 2. Glowing Outer Rim Border
        border_pen = QPen(QColor(getattr(self, "current_border_color", "rgba(129, 140, 248, 0.55)")))
        border_pen.setWidthF(1.2)
        painter.setPen(border_pen)
        painter.drawPath(path)

        # 3. 3D Embossed Specular Highlight Arc (Crisp Glass Reflection)
        inner_rect = rect.adjusted(1, 1, -1, -1)
        top_highlight_path = QPainterPath()
        top_highlight_path.addRoundedRect(
            float(inner_rect.x()), float(inner_rect.y()),
            float(inner_rect.width()), float(inner_rect.height()),
            radius - 1.0, radius - 1.0
        )
        specular_pen = QPen()
        spec_grad = QLinearGradient(0, float(inner_rect.y()), 0, float(inner_rect.y() + inner_rect.height() * 0.6))
        spec_grad.setColorAt(0.0, QColor(255, 255, 255, 65))  # Refined specular arc
        spec_grad.setColorAt(0.4, QColor(255, 255, 255, 15))
        spec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        specular_pen.setBrush(QBrush(spec_grad))
        specular_pen.setWidthF(1.0)
        painter.setPen(specular_pen)
        painter.drawPath(top_highlight_path)

        # 4. Subtle Bottom Shadow Bevel (Physical Emboss Depth)
        bottom_shadow_path = QPainterPath()
        bottom_shadow_path.addRoundedRect(
            float(inner_rect.x()), float(inner_rect.y() + 2),
            float(inner_rect.width()), float(inner_rect.height() - 2),
            radius - 1.0, radius - 1.0
        )
        shadow_pen = QPen(QColor(0, 0, 0, 35))
        shadow_pen.setWidthF(1.0)
        painter.setPen(shadow_pen)
        painter.drawPath(bottom_shadow_path)

