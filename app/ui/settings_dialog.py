"""
Settings & History Dialog for Gemini Flow (PyQt6)
Features API configuration, interactive hotkey recorder, AI dictation presets, audio device selector,
custom phonetic dictionary, voice snippets manager, direct history copy, and AI prompt transformer.
"""
import time
import logging
import threading
from typing import Optional, List, Dict, Set, Any

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QDate, QSize, QEvent, QPoint
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel,
    QLineEdit, QPushButton, QComboBox, QRadioButton, QButtonGroup,
    QCheckBox, QTextEdit, QListWidget, QListWidgetItem, QProgressBar,
    QMessageBox, QFrame, QScrollArea, QApplication, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QListView,
    QInputDialog, QDialogButtonBox, QSizePolicy, QTreeWidget,
    QTreeWidgetItem, QMenu, QCalendarWidget, QStyledItemDelegate
)
from PyQt6.QtGui import QFont, QColor, QIcon, QAction, QTextDocument
from pynput import keyboard

from ..audio_recorder import AudioRecorder
from ..text_injector import TextInjector
from ..router.model_router import MODEL_REGISTRY, ModelRouter
from ..profiles.profile_manager import ProfileManager, BUILTIN_PROFILES
from ..vocabulary.vocab_engine import VocabularyEngine, VocabularyEntry
from ..benchmark.benchmark_engine import MetricsTracker, BenchmarkEngine, BENCHMARK_TEST_SUITE
from ..security.security_manager import SecurityManager
from ..transformation.transform_engine import TransformType, TransformEngine
from ..cost_awareness import (
    CostAwarenessTracker,
    MODEL_PRICING,
    MILESTONES_TABLE,
    MilestoneInfo,
    get_milestone_info,
    format_duration
)

from pathlib import Path

logger = logging.getLogger("GeminiFlow.SettingsDialog")

_RESOURCES_DIR = Path(__file__).parent.parent / "resources"
_CHECK_ICON = (_RESOURCES_DIR / "check.png").resolve().as_posix()
_RADIO_ICON = (_RESOURCES_DIR / "radio.png").resolve().as_posix()

DARK_STYLE = """
QDialog {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
}
QTabWidget::pane {
    border: 1px solid #334155;
    background: #1E293B;
    border-radius: 8px;
    top: -1px;
}
QTabBar::tab {
    background: #0F172A;
    color: #94A3B8;
    padding: 8px 10px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 500;
    font-size: 11px;
}
QTabBar::tab:selected {
    background: #1E293B;
    color: #38BDF8;
    border-bottom: 2px solid #38BDF8;
    font-weight: 600;
}
QLabel {
    color: #E2E8F0;
    font-size: 13px;
}
QLineEdit, QTextEdit {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 13px;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #6366F1;
}
QComboBox {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    min-height: 20px;
}
QComboBox:focus {
    border: 1px solid #6366F1;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #334155;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #94A3B8;
    margin: 4px;
}
QComboBox QAbstractItemView {
    background-color: #1E293B;
    color: #F8FAFC;
    selection-background-color: #6366F1;
    selection-color: #FFFFFF;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 4px;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 8px 10px;
    min-height: 24px;
    border-radius: 4px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #334155;
    color: #38BDF8;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #6366F1;
    color: #FFFFFF;
}
QPushButton {
    background-color: #6366F1;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 9px 18px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #4F46E5;
}
QPushButton:pressed {
    background-color: #4338CA;
}
QPushButton#secondaryBtn {
    background-color: #334155;
    color: #E2E8F0;
}
QPushButton#secondaryBtn:hover {
    background-color: #475569;
}
QPushButton#successBtn {
    background-color: #10B981;
    color: white;
}
QPushButton#dangerBtn {
    background-color: #DC2626;
    color: white;
}
QPushButton#dangerBtn:hover {
    background-color: #B91C1C;
}
QPushButton#recordKeyBtn {
    background-color: #1E293B;
    color: #38BDF8;
    border: 1px dashed #6366F1;
    padding: 10px 16px;
    font-weight: 600;
    text-align: center;
}
QPushButton#recordKeyBtn:hover {
    background-color: #334155;
    border: 1px solid #38BDF8;
}
QPushButton#recordKeyBtnActive {
    background-color: #4338CA;
    color: #FDE047;
    border: 2px solid #F59E0B;
    padding: 10px 16px;
    font-weight: bold;
    text-align: center;
}
QCheckBox {
    color: #F8FAFC;
    spacing: 10px;
    font-size: 13px;
    font-weight: 500;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 5px;
    border: 2px solid #64748B;
    background-color: #0B1120;
}
QCheckBox::indicator:hover {
    border: 2px solid #38BDF8;
    background-color: #1E293B;
}
QCheckBox::indicator:checked {
    border: 2px solid #38BDF8;
    background-color: #0284C7;
    image: url({CHECK_ICON});
}
QCheckBox::indicator:checked:hover {
    border: 2px solid #38BDF8;
    background-color: #0369A1;
    image: url({CHECK_ICON});
}
QRadioButton {
    color: #F8FAFC;
    spacing: 10px;
    font-size: 13px;
    font-weight: 500;
}
QRadioButton::indicator {
    width: 20px;
    height: 20px;
    border-radius: 10px;
    border: 2px solid #64748B;
    background-color: #0B1120;
}
QRadioButton::indicator:hover {
    border: 2px solid #38BDF8;
    background-color: #1E293B;
}
QRadioButton::indicator:checked {
    border: 2px solid #38BDF8;
    background-color: #0284C7;
    image: url({RADIO_ICON});
}
QRadioButton::indicator:checked:hover {
    border: 2px solid #38BDF8;
    background-color: #0369A1;
    image: url({RADIO_ICON});
}
QListWidget {
    background-color: #0B1120;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #F8FAFC;
    padding: 6px;
    outline: none;
}
QListWidget::item {
    padding: 12px 14px;
    border-bottom: 1px solid #1E293B;
    border-radius: 6px;
    margin-bottom: 4px;
    background-color: #0F172A;
}
QListWidget::item:hover {
    background-color: #1E293B;
    border: 1px solid #475569;
}
QListWidget::item:selected {
    background-color: #1E293B;
    border: 1px solid #38BDF8;
    color: #FFFFFF;
}
QTableWidget {
    background-color: #0B1120;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #FFFFFF;
    gridline-color: #1E293B;
    outline: none;
    font-size: 14px;
}
QTableWidget::item {
    padding: 6px 12px;
    border-bottom: 1px solid #1E293B;
    color: #FFFFFF;
    font-size: 14px;
}
QTableWidget::item:selected {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: bold;
}
QTableWidget::item:hover {
    background-color: #1E293B;
}
QHeaderView::section {
    background-color: #1E293B;
    color: #38BDF8;
    padding: 8px 12px;
    border: none;
    border-bottom: 2px solid #334155;
    font-weight: 700;
    font-size: 13px;
}
QPushButton#historyChip {
    background-color: #1E293B;
    color: #94A3B8;
    border: 1px solid #475569;
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 500;
    min-height: 20px;
}
QPushButton#historyChip:hover {
    background-color: #334155;
    color: #38BDF8;
    border: 1px solid #38BDF8;
}
QProgressBar {
    border: 1px solid #334155;
    border-radius: 4px;
    background: #0F172A;
    text-align: center;
    color: white;
}
QProgressBar::chunk {
    background-color: #10B981;
    border-radius: 3px;
}
QTreeWidget {
    background-color: #0B1120;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 4px;
    font-size: 13px;
    outline: none;
}
QTreeWidget::item {
    padding: 6px 4px;
    border-radius: 4px;
    margin-bottom: 2px;
}
QTreeWidget::item:hover {
    background-color: #1E293B;
}
QTreeWidget::item:selected {
    background-color: #0369A1;
    color: #FFFFFF;
}
QHeaderView::section {
    background-color: #1E293B;
    color: #38BDF8;
    padding: 8px 10px;
    border-top: 1px solid #334155;
    border-bottom: 2px solid #38BDF8;
    border-left: none;
    border-right: 1px solid #334155;
    font-weight: 700;
    font-size: 12px;
}
QHeaderView::section:hover {
    background-color: #334155;
    color: #FFFFFF;
}
QMenu {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px;
}
QMenu::item {
    padding: 8px 24px 8px 16px;
    border-radius: 4px;
    font-size: 13px;
}
QMenu::item:selected {
    background-color: #0284C7;
    color: white;
}
QMenu::separator {
    height: 1px;
    background: #334155;
    margin: 4px 8px;
}
QCalendarWidget QWidget {
    background-color: #0F172A;
    color: #F8FAFC;
}
"""
DARK_STYLE = DARK_STYLE.replace("{CHECK_ICON}", _CHECK_ICON).replace("{RADIO_ICON}", _RADIO_ICON)


class HotkeyCaptureSignals(QObject):
    key_combo_updated = pyqtSignal(str, str)  # display_str, internal_str


class HotkeyCaptureButton(QPushButton):
    """
    Interactive button that listens to physical keyboard presses in real-time
    (e.g., Shift, Control, Windows, Alt, Space, F-keys) and formats them cleanly.
    """
    def __init__(self, default_display: str = "Ctrl + Win", default_internal: str = "<ctrl>+<cmd>", parent=None):
        super().__init__(parent)
        self.display_str = default_display
        self.internal_str = default_internal
        self.is_recording = False
        self.signals = HotkeyCaptureSignals()
        self.signals.key_combo_updated.connect(self._on_combo_updated)

        self._listener: Optional[keyboard.Listener] = None
        self._pressed_keys: Set[Any] = set()

        self.setMinimumHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        font = QFont("Segoe UI", 11)
        font.setWeight(QFont.Weight.DemiBold)
        self.setFont(font)

        self._update_button_text()
        self.clicked.connect(self._toggle_recording)

    def set_hotkey(self, display_str: str, internal_str: str):
        self.display_str = display_str
        self.internal_str = internal_str
        self._update_button_text()

    def _update_button_text(self):
        if self.is_recording:
            self.setText("🔴 Recording Shortcut... Press Keys on Keyboard (e.g. Shift, Ctrl, Win)")
            self.setStyleSheet("""
                QPushButton {
                    background-color: #312E81;
                    color: #FDE047;
                    border: 2px solid #F59E0B;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                    text-align: center;
                }
            """)
        else:
            self.setText(f"⌨️  {self.display_str}   (Click to Record Shortcut)")
            self.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #38BDF8;
                    border: 2px dashed #6366F1;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: bold;
                    text-align: center;
                }
                QPushButton:hover {
                    background-color: #334155;
                    border-color: #38BDF8;
                    color: #FFFFFF;
                }
            """)

    def _toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.is_recording = True
        self._pressed_keys.clear()
        self._update_button_text()

        # Start pynput keyboard listener to reliably capture Windows/Cmd, Ctrl, Shift, Alt
        self._listener = keyboard.Listener(
            on_press=self._on_pynput_press,
            on_release=self._on_pynput_release
        )
        self._listener.daemon = True
        self._listener.start()

    def stop_recording(self):
        self.is_recording = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._update_button_text()

    def _on_pynput_press(self, key):
        if not self.is_recording:
            return
        self._pressed_keys.add(key)
        self._process_pressed_keys(is_release=False)

    def _on_pynput_release(self, key):
        if not self.is_recording:
            return
        self._process_pressed_keys(is_release=True)
        # When all keys are released, automatically finalize recording
        if key in self._pressed_keys:
            self._pressed_keys.discard(key)
        if not self._pressed_keys:
            QTimer.singleShot(150, self.stop_recording)

    def _process_pressed_keys(self, is_release: bool = False):
        display_parts = []
        internal_parts = []

        # Check standard modifiers in clean order: Ctrl -> Shift -> Alt -> Win -> Other Keys
        has_ctrl = any(k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r) for k in self._pressed_keys)
        has_shift = any(k in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r) for k in self._pressed_keys)
        has_alt = any(k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr) for k in self._pressed_keys)
        has_win = any(k in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r) for k in self._pressed_keys)

        if has_ctrl:
            display_parts.append("Ctrl")
            internal_parts.append("<ctrl>")
        if has_shift:
            display_parts.append("Shift")
            internal_parts.append("<shift>")
        if has_alt:
            display_parts.append("Alt")
            internal_parts.append("<alt>")
        if has_win:
            display_parts.append("Win")
            internal_parts.append("<cmd>")

        # Check other keys (Space, F-keys, Alphanumerics)
        for k in self._pressed_keys:
            if k == keyboard.Key.space:
                display_parts.append("Space")
                internal_parts.append("<space>")
            elif hasattr(k, "name") and k.name and k.name.startswith("f") and k.name[1:].isdigit():
                display_parts.append(k.name.upper())
                internal_parts.append(k.name.lower())
            elif isinstance(k, keyboard.KeyCode) and k.char:
                char_str = k.char.upper()
                if char_str not in display_parts:
                    display_parts.append(char_str)
                    internal_parts.append(char_str.lower())

        if display_parts:
            disp = " + ".join(display_parts)
            inter = "+".join(internal_parts)
            self.signals.key_combo_updated.emit(disp, inter)

    def _on_combo_updated(self, disp: str, inter: str):
        self.display_str = disp
        self.internal_str = inter
        self.setText(f"🔴 {disp} (Release keys to confirm)")


class DictEditDialog(QDialog):
    """Modal dialog for creating or editing a phonetic dictionary entry."""
    def __init__(self, spoken: str = "", replacement: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Dictionary Entry" if spoken else "Add Dictionary Entry")
        self.setMinimumSize(480, 240)
        self.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        desc = QLabel("Teach Gemini Flow how you want specific names, acronyms, or misheard words to be spelled.")
        desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(desc)

        layout.addWidget(QLabel("Spoken / Misheard Phrase (What speech-to-text might hear):"))
        self.spoken_input = QLineEdit(self)
        self.spoken_input.setPlaceholderText("e.g. Srinivas Avasthi, antiquee, Wisper...")
        self.spoken_input.setText(spoken)
        self.spoken_input.setStyleSheet("font-size: 14px; font-weight: 600; color: #FFFFFF; padding: 8px 10px;")
        layout.addWidget(self.spoken_input)

        layout.addWidget(QLabel("Target Replacement Spelling (What you actually want typed):"))
        self.replacement_input = QLineEdit(self)
        self.replacement_input.setPlaceholderText("e.g. Sri Srinivas Awasthi, antiqui, Wispr...")
        self.replacement_input.setText(replacement)
        self.replacement_input.setStyleSheet("font-size: 14px; font-weight: 600; color: #38BDF8; padding: 8px 10px;")
        layout.addWidget(self.replacement_input)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Word Pair", self)
        self.btn_save.clicked.connect(self._validate_and_accept)
        btn_box.addWidget(self.btn_save)
        layout.addLayout(btn_box)

    def _validate_and_accept(self):
        if not self.spoken_input.text().strip():
            QMessageBox.warning(self, "Missing Phrase", "Please enter the spoken or misheard phrase.")
            return
        if not self.replacement_input.text().strip():
            QMessageBox.warning(self, "Missing Replacement", "Please enter the replacement spelling.")
            return
        self.accept()

    def get_data(self) -> Dict[str, str]:
        return {
            "spoken": self.spoken_input.text().strip(),
            "replacement": self.replacement_input.text().strip()
        }


class SnippetEditDialog(QDialog):
    """Modal dialog for creating or editing a voice quick text expansion."""
    def __init__(self, trigger: str = "", content: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Quick Text" if trigger else "Add Quick Text")
        self.setMinimumSize(500, 340)
        self.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Voice Trigger Phrase (What you speak):"))
        self.trigger_input = QLineEdit(self)
        self.trigger_input.setPlaceholderText("e.g. Hey I am Srinivas LinkedIn GitHub Instagram")
        self.trigger_input.setText(trigger)
        layout.addWidget(self.trigger_input)

        layout.addWidget(QLabel("Expanded Text (What gets pasted):"))
        self.content_edit = QTextEdit(self)
        self.content_edit.setPlaceholderText("Enter the full text, profile, template, or links to expand...")
        self.content_edit.setPlainText(content)
        layout.addWidget(self.content_edit)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Quick Text", self)
        self.btn_save.clicked.connect(self._validate_and_accept)
        btn_box.addWidget(self.btn_save)
        layout.addLayout(btn_box)

    def _validate_and_accept(self):
        if not self.trigger_input.text().strip():
            QMessageBox.warning(self, "Missing Trigger", "Please enter a voice trigger phrase.")
            return
        if not self.content_edit.toPlainText().strip():
            QMessageBox.warning(self, "Missing Content", "Please enter the expanded text.")
            return
        self.accept()

    def get_data(self) -> Dict[str, str]:
        return {
            "trigger": self.trigger_input.text().strip(),
            "content": self.content_edit.toPlainText().strip()
        }


class VocabEditDialog(QDialog):
    """Modal dialog for creating or editing a Personal AI Vocabulary entry."""
    def __init__(self, canonical: str = "", aliases: str = "", category: str = "Technical", enabled: bool = True, notes: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Vocabulary Term" if canonical else "Add Vocabulary Term")
        self.setMinimumSize(500, 380)
        self.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        desc = QLabel("Define canonical terms, technical acronyms, or proper names with their spoken phonetic variants.")
        desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(desc)

        layout.addWidget(QLabel("Canonical Term (Exact spelling to output):"))
        self.canonical_input = QLineEdit(self)
        self.canonical_input.setPlaceholderText("e.g. TypeScript, PyTorch, LeetCode, Srinivas Awasthi...")
        self.canonical_input.setText(canonical)
        self.canonical_input.setStyleSheet("font-size: 14px; font-weight: 600; color: #38BDF8; padding: 8px 10px;")
        layout.addWidget(self.canonical_input)

        layout.addWidget(QLabel("Spoken Aliases / Phonetic Variants (comma separated):"))
        self.aliases_input = QLineEdit(self)
        self.aliases_input.setPlaceholderText("e.g. types script, type script, ts")
        self.aliases_input.setText(aliases)
        layout.addWidget(self.aliases_input)

        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox(self)
        self.category_combo.setView(QListView())
        self.category_combo.addItems(["Technical", "Programming", "Personal", "Project", "Academic", "Business", "Custom"])
        idx = self.category_combo.findText(category)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        layout.addWidget(self.category_combo)

        layout.addWidget(QLabel("Notes / Context (Optional):"))
        self.notes_input = QLineEdit(self)
        self.notes_input.setPlaceholderText("e.g. Senior dev tech stack, founder name...")
        self.notes_input.setText(notes)
        layout.addWidget(self.notes_input)

        self.cb_enabled = QCheckBox("Enabled (Active in prompt priming & auto-normalization)")
        self.cb_enabled.setChecked(enabled)
        layout.addWidget(self.cb_enabled)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Vocabulary Term", self)
        self.btn_save.clicked.connect(self._validate_and_accept)
        btn_box.addWidget(self.btn_save)
        layout.addLayout(btn_box)

    def _validate_and_accept(self):
        if not self.canonical_input.text().strip():
            QMessageBox.warning(self, "Missing Term", "Please enter the canonical term.")
            return
        self.accept()

    def get_data(self) -> Dict[str, Any]:
        raw_aliases = [a.strip() for a in self.aliases_input.text().split(",") if a.strip()]
        return {
            "canonical_term": self.canonical_input.text().strip(),
            "aliases": raw_aliases,
            "category": self.category_combo.currentText(),
            "enabled": self.cb_enabled.isChecked(),
            "notes": self.notes_input.text().strip()
        }


class PromptResultDialog(QDialog):
    """Spacious modal dialog that displays the generated AI prompt with easy copy."""
    def __init__(self, prompt_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✨ Generated AI Prompt")
        self.setMinimumSize(640, 480)
        self.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QLabel("✨ Your Optimized AI Prompt is Ready!", self)
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8;")
        layout.addWidget(header)

        sub = QLabel("Formatted for ChatGPT, Claude, Gemini, or IDEs. Automatically copied to clipboard.", self)
        sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(sub)

        self.prompt_view = QTextEdit(self)
        self.prompt_view.setReadOnly(True)
        self.prompt_view.setPlainText(prompt_text)
        self.prompt_view.setStyleSheet("""
            background-color: #0B1120;
            color: #F8FAFC;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px;
            font-size: 13px;
            font-family: 'Consolas', 'Segoe UI', monospace;
        """)
        layout.addWidget(self.prompt_view)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_copy = QPushButton("📋 Copy Prompt Again", self)
        self.btn_copy.setObjectName("secondaryBtn")
        self.btn_copy.clicked.connect(self._copy_prompt)
        btn_box.addWidget(self.btn_copy)

        self.btn_done = QPushButton("Done", self)
        self.btn_done.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_done)

        layout.addLayout(btn_box)

    def _copy_prompt(self):
        import pyperclip
        pyperclip.copy(self.prompt_view.toPlainText())
        self.btn_copy.setText("✓ Copied!")
        self.btn_copy.setStyleSheet("background-color: #10B981; color: white;")
        QTimer.singleShot(1400, lambda: [
            self.btn_copy.setText("📋 Copy Prompt Again"),
            self.btn_copy.setStyleSheet("")
        ])


class RenameTranscriptDialog(QDialog):
    """Clean popup modal to rename a past transcript with a custom memorable title."""
    def __init__(self, current_title: str = "", preview_text: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("✏️ Rename Transcript")
        self.setFixedWidth(460)
        self.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("✏️ Set Custom Transcript Title", self)
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #38BDF8;")
        layout.addWidget(title)

        sub = QLabel("Give this transcript a memorable name (e.g. 'Project Planning', 'Email to Team', 'Bug Report').", self)
        sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        if preview_text:
            preview_lbl = QLabel(f"Preview: \"{preview_text[:70]}...\"", self)
            preview_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-style: italic;")
            layout.addWidget(preview_lbl)

        self.title_input = QLineEdit(self)
        self.title_input.setText(current_title)
        self.title_input.setPlaceholderText("Enter custom title...")
        self.title_input.setStyleSheet("font-size: 14px; font-weight: 600; color: #FFFFFF; padding: 8px 10px;")
        layout.addWidget(self.title_input)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Title", self)
        self.btn_save.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_save)

        layout.addLayout(btn_box)

    def get_title(self) -> str:
        return self.title_input.text().strip()


class CalendarFilterDialog(QDialog):
    """Calendar date-picker modal for filtering transcripts by specific date."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📅 Filter Transcripts by Date")
        self.setFixedSize(400, 360)
        self.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QLabel("📅 Select Date to Filter", self)
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #38BDF8;")
        layout.addWidget(header)

        self.calendar = QCalendarWidget(self)
        self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton("Apply Date Filter", self)
        self.btn_apply.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_apply)

        layout.addLayout(btn_box)

    def get_selected_date_str(self) -> str:
        qdate = self.calendar.selectedDate()
        return qdate.toString("yyyy-MM-dd")


def format_history_preview(text: str, max_chars: int = 240, max_lines: int = 3) -> str:
    """
    Format a multi-line transcript preview showing up to 3 lines (around 240 characters)
    with clean word-boundary truncation and ellipsis if longer.
    """
    cleaned = text.strip()
    if not cleaned:
        return ""
    lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
    if len(lines) > max_lines:
        truncated_block = "\n".join(lines[:max_lines])
        if len(truncated_block) > max_chars:
            truncated_block = truncated_block[:max_chars].rsplit(" ", 1)[0]
        return truncated_block + "..."

    if len(lines) > 1:
        combined = "\n".join(lines)
    else:
        combined = " ".join(cleaned.split())
    if len(combined) > max_chars:
        return combined[:max_chars].rsplit(" ", 1)[0] + "..."
    return combined


class HistoryTranscriptDelegate(QStyledItemDelegate):
    """
    Delegate for multi-line transcript rendering in the History QTreeWidget.
    Dynamically computes height to show up to 3 lines with clean text wrapping.
    """
    def sizeHint(self, option, index):
        if index.column() == 0 and index.parent().isValid():
            text = index.data(Qt.ItemDataRole.DisplayRole) or ""
            col_w = option.widget.columnWidth(0) if option.widget else 500
            doc = QTextDocument()
            doc.setDefaultFont(option.font)
            doc.setTextWidth(max(150, col_w - 36))
            doc.setPlainText(text)

            line_height = option.fontMetrics.lineSpacing()
            needed_h = int(doc.size().height())
            return QSize(int(doc.idealWidth()), max(line_height + 14, needed_h + 14))
        return super().sizeHint(option, index)


class SettingsDialog(QDialog):
    settings_applied = pyqtSignal()

    def __init__(self, config_manager, gemini_engine, text_injector=None, main_app=None, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.gemini = gemini_engine
        self.text_injector = text_injector or TextInjector()
        self.main_app = main_app
        self.test_recorder = None
        self.mic_test_timer = None

        # Advanced History Filter & Selection State
        self._history_search_query = ""
        self._history_filter_favorites = False
        self._history_filter_category = None  # "date", "model", "app", "transformation"
        self._history_filter_value = None
        self._selected_entry_id = None

        # Live background sync state & timer (every 2.5 seconds)
        self._last_history_mtime = 0.0
        self._last_config_mtime = 0.0
        self._last_history_len = len(self.config.get_history())
        self._last_top_id = ""

        self.live_sync_timer = QTimer(self)
        self.live_sync_timer.setInterval(2500)
        self.live_sync_timer.timeout.connect(self._poll_live_updates)
        self.live_sync_timer.start()

        self.setWindowTitle("Gemini Flow — Voice AI Settings & Dashboard")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinMaxButtonsHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(720, 620)
        self.setStyleSheet(DARK_STYLE)

        # Debounce timer for geometry persistence (250ms)
        self._debounce_save_timer = QTimer(self)
        self._debounce_save_timer.setSingleShot(True)
        self._debounce_save_timer.setInterval(250)
        self._debounce_save_timer.timeout.connect(self._save_window_state)
        self._restore_window_state()

        self._init_ui()
        self._load_values()

    def _restore_window_state(self):
        try:
            ws = self.config.get("settings_window_state", {})
            w = ws.get("width", 820)
            h = ws.get("height", 720)
            x = ws.get("x")
            y = ws.get("y")
            self.resize(w, h)
            if x is not None and y is not None:
                self.move(x, y)
        except Exception as e:
            logger.warning(f"Could not restore window geometry: {e}")

    def _save_window_state(self):
        try:
            geom = self.geometry()
            ws = {
                "x": geom.x(),
                "y": geom.y(),
                "width": geom.width(),
                "height": geom.height(),
                "is_maximized": self.isMaximized()
            }
            self.config.set("settings_window_state", ws)
        except Exception as e:
            logger.warning(f"Could not save window geometry: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_debounce_save_timer') and self._debounce_save_timer:
            self._debounce_save_timer.start()

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, '_debounce_save_timer') and self._debounce_save_timer:
            self._debounce_save_timer.start()

    def _poll_live_updates(self):
        """Polls for background history/config changes and updates UI safely."""
        try:
            history = self.config.get_history()
            cur_len = len(history)
            top_id = history[0].get("id") if history else ""
            if cur_len != self._last_history_len or top_id != self._last_top_id:
                self._last_history_len = cur_len
                self._last_top_id = top_id
                self._refresh_history()
                self._refresh_cost_stats()
        except Exception as e:
            logger.debug(f"Live poll update skipped: {e}")

    def notify_history_changed(self):
        """Called immediately when a new dictation/transform completes."""
        try:
            self._refresh_history()
            self._refresh_cost_stats()
        except Exception as e:
            logger.debug(f"Notify history change error: {e}")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Title
        title_box = QHBoxLayout()
        title_label = QLabel("✨ Gemini Flow Settings", self)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #F8FAFC;")
        title_box.addWidget(title_label)
        title_box.addStretch()

        tip_label = QLabel("💡 Tip: Double-click the taskbar mic icon to open anytime. Press Esc while speaking to cancel.", self)
        tip_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        title_box.addWidget(tip_label)
        layout.addLayout(title_box)

        # Tabs (Organized strictly per user specification)
        self.tabs = QTabWidget(self)
        self.tabs.addTab(self._create_general_tab(), "🔑 API_General")
        self.tabs.addTab(self._create_hotkeys_tab(), "⌨️ Hotkeys_Mode")
        self.tabs.addTab(self._create_cost_tab(), "💰 Cost_Productivity")
        self.tabs.addTab(self._create_vocabulary_tab(), "📁 Vocabulary Engine")
        self.tabs.addTab(self._create_dictionary_tab(), "📖 Custom Dictionary")
        self.tabs.addTab(self._create_snippets_tab(), "⚡ Quick Text")
        self.tabs.addTab(self._create_history_tab(), "📜 History")
        self.tabs.addTab(self._create_profiles_tab(), "⚡ Profiles")
        self.tabs.addTab(self._create_ai_tab(), "🧠 AI Dictation")
        self.tabs.addTab(self._create_router_tab(), "🎯 AI Model Router")
        self.tabs.addTab(self._create_audio_tab(), "🎙️ Audio Device")
        layout.addWidget(self.tabs)

        # Bottom Action Buttons (Save/Apply stays open, Close button closes)
        btn_box = QHBoxLayout()
        self.save_status_label = QLabel("", self)
        self.save_status_label.setStyleSheet("color: #10B981; font-weight: 600; font-size: 13px;")
        btn_box.addWidget(self.save_status_label)
        btn_box.addStretch()

        self.btn_save = QPushButton("💾 Save & Apply Changes", self)
        self.btn_save.setMinimumHeight(38)
        self.btn_save.clicked.connect(self._save_settings)
        btn_box.addWidget(self.btn_save)

        self.btn_restart = QPushButton("🔄 Restart App", self)
        self.btn_restart.setObjectName("secondaryBtn")
        self.btn_restart.setMinimumHeight(38)
        self.btn_restart.setToolTip("Saves changes and cleanly reloads Gemini Flow without rebooting Windows")
        self.btn_restart.clicked.connect(self._restart_app)
        btn_box.addWidget(self.btn_restart)

        self.btn_close = QPushButton("✖ Close", self)
        self.btn_close.setObjectName("secondaryBtn")
        self.btn_close.setMinimumHeight(38)
        self.btn_close.clicked.connect(self.close)
        btn_box.addWidget(self.btn_close)

        layout.addLayout(btn_box)

    def _create_general_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QWidget#generalScrollChild { background: transparent; }")

        tab = QWidget()
        tab.setObjectName("generalScrollChild")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # API Key Section
        api_label = QLabel("Google Gemini API Key:")
        layout.addWidget(api_label)

        key_box = QHBoxLayout()
        self.api_key_input = QLineEdit(self)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter your Gemini API key (AQ.Ab8... or AIzaSy...)")
        key_box.addWidget(self.api_key_input)

        self.btn_toggle_key = QPushButton("👁️ Show", self)
        self.btn_toggle_key.setObjectName("secondaryBtn")
        self.btn_toggle_key.clicked.connect(self._toggle_key_echo)
        key_box.addWidget(self.btn_toggle_key)

        self.btn_test_api = QPushButton("Test API", self)
        self.btn_test_api.setObjectName("secondaryBtn")
        self.btn_test_api.clicked.connect(self._test_api)
        key_box.addWidget(self.btn_test_api)
        layout.addLayout(key_box)

        self.api_status_label = QLabel("")
        layout.addWidget(self.api_status_label)

        # Model Selection (Intelligent Router + Models)
        model_label = QLabel("Gemini AI Model / Routing Mode:")
        layout.addWidget(model_label)
        self.model_combo = QComboBox(self)
        self.model_combo.setView(QListView())
        self.model_combo.addItems([
            "auto (Intelligent AI Model Router — Dynamic Per-Task Selection)",
            "gemini-3.5-flash-lite (Lowest Latency < 1.5s — Recommended)",
            "gemini-3.5-flash (Balanced Dictation & Prompt Enhancer)",
            "gemini-3.6-flash (Fast Advanced Reasoning & Polish)",
            "gemini-flash-latest (Auto Latest Production Flash)",
            "gemini-3.7-flash (Advanced Reasoning & Technical Dictation)",
            "gemini-2.5-flash (Standard Flash)",
            "gemini-2.5-pro (Deep Thought & Document Generation)"
        ])
        self.model_combo.currentIndexChanged.connect(self._on_general_model_combo_changed)
        layout.addWidget(self.model_combo)

        # Auto-paste & Sound options
        self.cb_auto_paste = QCheckBox("Automatically paste transcribed text into active cursor position")
        layout.addWidget(self.cb_auto_paste)

        self.cb_sounds = QCheckBox("Play subtle sound cues on start, stop, and cancellation")
        layout.addWidget(self.cb_sounds)

        self.cb_auto_prompt = QCheckBox("✨ Automatically convert voice to structured AI Prompts in AI Coding Agents (Antigravity, VS Code, Windsurf, Cursor)")
        self.cb_auto_prompt.setToolTip("When checked: Converts voice to formatted AI Prompts in IDEs and keeps verbatim speech in clipboard.\nWhen unchecked: Outputs 100% pure, clean, natural speech dictation with perfect grammar & punctuation everywhere.")
        layout.addWidget(self.cb_auto_prompt)

        self.cb_start_with_windows = QCheckBox("Start Gemini Flow automatically when Windows starts (Recommended)")
        layout.addWidget(self.cb_start_with_windows)

        layout.addStretch()
        layout.addStretch()
        scroll.setWidget(tab)
        return scroll

    def _create_hotkeys_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QWidget#hotkeyScrollChild { background: transparent; }")

        tab = QWidget()
        tab.setObjectName("hotkeyScrollChild")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        mode_label = QLabel("Speech Dictation Mode:")
        mode_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #F8FAFC;")
        layout.addWidget(mode_label)

        self.radio_toggle = QRadioButton("Toggle Mode (Press hotkey once to start recording, press again to stop)")
        self.radio_ptt = QRadioButton("Push-to-Talk Mode (Hold hotkey to record, release to transcribe & paste)")
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_toggle)
        self.mode_group.addButton(self.radio_ptt)
        layout.addWidget(self.radio_toggle)
        layout.addWidget(self.radio_ptt)

        # Dictation Hotkey Section with Interactive Key-Capture
        hk_label = QLabel("🎙️ Voice Dictation Shortcut Key:")
        hk_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #38BDF8; margin-top: 6px;")
        layout.addWidget(hk_label)

        self.hotkey_btn = HotkeyCaptureButton("Ctrl + Win", "<ctrl>+<cmd>", self)
        layout.addWidget(self.hotkey_btn)

        # Quick preset buttons for main hotkey
        preset_box = QHBoxLayout()
        preset_box.setSpacing(8)
        presets = [
            ("Ctrl + Win", "Ctrl + Win", "<ctrl>+<cmd>"),
            ("Ctrl + Space", "Ctrl + Space", "<ctrl>+<space>"),
            ("F8", "F8", "f8"),
            ("Alt + Space", "Alt + Space", "<alt>+<space>"),
            ("Ctrl + Shift + V", "Ctrl + Shift + V", "<ctrl>+<shift>+v")
        ]
        for title, disp, inter in presets:
            btn = QPushButton(title, self)
            btn.setMinimumHeight(36)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #F8FAFC;
                    border: 1px solid #475569;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #38BDF8;
                    border-color: #38BDF8;
                }
            """)
            btn.clicked.connect(lambda _, d=disp, i=inter: self.hotkey_btn.set_hotkey(d, i))
            preset_box.addWidget(btn)
        preset_box.addStretch()
        layout.addLayout(preset_box)

        # Prompt Enhancer Shortcut Key
        prompt_hk_label = QLabel("✨ AI Prompt Transformation Shortcut (Turns thoughts into AI Prompts):")
        prompt_hk_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #FDE047; margin-top: 6px;")
        layout.addWidget(prompt_hk_label)

        self.prompt_hotkey_btn = HotkeyCaptureButton("Ctrl + Shift + P", "<ctrl>+<shift>+p", self)
        layout.addWidget(self.prompt_hotkey_btn)

        # Quick preset suggestions for prompt hotkey
        prompt_preset_box = QHBoxLayout()
        prompt_preset_box.setSpacing(8)
        prompt_presets = [
            ("Ctrl + Shift + P", "Ctrl + Shift + P", "<ctrl>+<shift>+p"),
            ("Ctrl + Shift + L", "Ctrl + Shift + L", "<ctrl>+<shift>+l"),
            ("Ctrl + Alt + P", "Ctrl + Alt + P", "<ctrl>+<alt>+p"),
            ("Alt + P", "Alt + P", "<alt>+p"),
            ("F9", "F9", "f9")
        ]
        for title, disp, inter in prompt_presets:
            btn = QPushButton(title, self)
            btn.setMinimumHeight(36)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #F8FAFC;
                    border: 1px solid #475569;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #FDE047;
                    border-color: #F59E0B;
                }
            """)
            btn.clicked.connect(lambda _, d=disp, i=inter: self.prompt_hotkey_btn.set_hotkey(d, i))
            prompt_preset_box.addWidget(btn)
        prompt_preset_box.addStretch()
        layout.addLayout(prompt_preset_box)

        # Universal Text Transformation Shortcut
        trans_hk_label = QLabel("⚡ Universal Text Transformation Shortcut (Transforms selected text anywhere):")
        trans_hk_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #A78BFA; margin-top: 6px;")
        layout.addWidget(trans_hk_label)

        self.transform_hotkey_btn = HotkeyCaptureButton("Ctrl + Shift + T", "<ctrl>+<shift>+t", self)
        layout.addWidget(self.transform_hotkey_btn)

        trans_preset_box = QHBoxLayout()
        trans_preset_box.setSpacing(8)
        trans_presets = [
            ("Ctrl + Shift + T", "Ctrl + Shift + T", "<ctrl>+<shift>+t"),
            ("Ctrl + Alt + T", "Ctrl + Alt + T", "<ctrl>+<alt>+t"),
            ("Alt + T", "Alt + T", "<alt>+t"),
            ("F10", "F10", "f10")
        ]
        for title, disp, inter in trans_presets:
            btn = QPushButton(title, self)
            btn.setMinimumHeight(36)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #F8FAFC;
                    border: 1px solid #475569;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #A78BFA;
                    border-color: #A78BFA;
                }
            """)
            btn.clicked.connect(lambda _, d=disp, i=inter: self.transform_hotkey_btn.set_hotkey(d, i))
            trans_preset_box.addWidget(btn)
        trans_preset_box.addStretch()
        layout.addLayout(trans_preset_box)

        # Escape info alert
        esc_info = QLabel("ℹ️ Note: Pressing Escape (Esc) during recording will instantly cancel and discard that speech.")
        esc_info.setWordWrap(True)
        esc_info.setStyleSheet("color: #38BDF8; font-size: 12px; background: #0F172A; border: 1px solid #334155; padding: 10px 14px; border-radius: 6px; margin-top: 4px;")
        layout.addWidget(esc_info)

        layout.addStretch()
        scroll.setWidget(tab)
        return scroll

    def _toggle_key_echo(self):
        if self.api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setText("🙈 Hide")
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setText("👁️ Show")

    def _purge_expired_history(self):
        days = self.retention_combo.currentData()
        if days == 0:
            QMessageBox.information(self, "Retention", "Retention is set to 'Keep Forever'. No entries purged.")
            return
        from ..security.security_manager import SecurityManager
        from ..config import APP_DIR, HISTORY_FILE
        sec = SecurityManager(APP_DIR)
        purged = sec.enforce_history_retention(str(HISTORY_FILE), days=days)
        self._refresh_history()
        QMessageBox.information(self, "Purge Complete", f"Successfully purged {purged} expired entries older than {days} days.")

    def _create_router_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QWidget#routerScrollChild { background: transparent; }")

        tab = QWidget()
        tab.setObjectName("routerScrollChild")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header = QLabel("🧭 Intelligent AI Model Router")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8;")
        layout.addWidget(header)

        desc = QLabel(
            "Gemini Flow dynamically analyzes the utterance, active foreground window, and developer profile "
            "to automatically pick the fastest and most capable model with zero configuration."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(desc)

        # Active status frame
        status_frame = QFrame(self)
        status_frame.setStyleSheet("QFrame { background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 12px; }")
        sf_layout = QVBoxLayout(status_frame)
        sf_layout.setSpacing(6)

        self.router_active_badge = QLabel("🟢 Router Status: Active (Intelligent Dynamic Selection Enabled)", self)
        self.router_active_badge.setStyleSheet("color: #10B981; font-weight: 700; font-size: 13px; border: none;")
        sf_layout.addWidget(self.router_active_badge)

        self.router_rule_info = QLabel(
            "• Short Speech / Chat apps ➔ Gemini 3.5 Flash-Lite (<1.5s latency)\n"
            "• VS Code / Terminal / Code ➔ Gemini 3.7 Flash (High Reasoning & Syntax)\n"
            "• Long Dictations / Summaries ➔ Gemini 2.5 Pro (Deep Thought & Outlines)\n"
            "• Formal Writing / Academic ➔ Gemini 2.5 Flash (Rich Textbook Clauses)",
            self
        )
        self.router_rule_info.setStyleSheet("color: #E2E8F0; font-size: 12px; line-height: 1.4; border: none;")
        sf_layout.addWidget(self.router_rule_info)
        layout.addWidget(status_frame)

        # Direct Model Selection Card on Router Tab
        sel_card = QFrame(self)
        sel_card.setStyleSheet("QFrame { background-color: #1E293B; border: 1px solid #0284C7; border-radius: 8px; padding: 12px; }")
        sel_layout = QVBoxLayout(sel_card)
        sel_layout.setSpacing(6)

        sel_title = QLabel("🎯 Select Active AI Model or Auto-Intelligence Router:", sel_card)
        sel_title.setStyleSheet("color: #38BDF8; font-weight: 700; font-size: 13px; border: none;")
        sel_layout.addWidget(sel_title)

        self.router_model_combo = QComboBox(sel_card)
        self.router_model_combo.setView(QListView())
        self.router_model_combo.addItems([
            "auto (Intelligent AI Model Router — Dynamic Per-Task Selection)",
            "gemini-3.5-flash-lite (Lowest Latency < 1.5s — Recommended)",
            "gemini-3.5-flash (Balanced Dictation & Prompt Enhancer)",
            "gemini-3.6-flash (Fast Advanced Reasoning & Polish)",
            "gemini-flash-latest (Auto Latest Production Flash)",
            "gemini-3.7-flash (Advanced Reasoning & Technical Dictation)",
            "gemini-2.5-flash (Standard Flash)",
            "gemini-2.5-pro (Deep Thought & Document Generation)"
        ])
        self.router_model_combo.currentIndexChanged.connect(self._on_router_model_combo_changed)
        sel_layout.addWidget(self.router_model_combo)
        layout.addWidget(sel_card)

        # Registry table
        mat_label = QLabel("Model Matrix & Capabilities:")
        mat_label.setStyleSheet("font-weight: 600; font-size: 13px; margin-top: 6px;")
        layout.addWidget(mat_label)

        self.router_table = QTableWidget(self)
        self.router_table.setColumnCount(5)
        self.router_table.setHorizontalHeaderLabels(["Model", "Speed", "Latency", "Reasoning", "Recommended Workflows"])
        self.router_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.router_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.router_table.setColumnWidth(0, 175)
        self.router_table.setColumnWidth(1, 90)
        self.router_table.setColumnWidth(2, 90)
        self.router_table.setColumnWidth(3, 100)
        self.router_table.verticalHeader().setVisible(False)
        self.router_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.router_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.router_table.setMinimumHeight(240)

        row = 0
        for m_id, m_meta in MODEL_REGISTRY.items():
            self.router_table.insertRow(row)
            self.router_table.setRowHeight(row, 40)
            self.router_table.setItem(row, 0, QTableWidgetItem(m_id))
            speed_stars = "⚡" * m_meta.speed_rating
            self.router_table.setItem(row, 1, QTableWidgetItem(speed_stars))
            self.router_table.setItem(row, 2, QTableWidgetItem(m_meta.typical_latency))
            self.router_table.setItem(row, 3, QTableWidgetItem(m_meta.reasoning_capability.capitalize()))
            self.router_table.setItem(row, 4, QTableWidgetItem(", ".join(m_meta.recommended_tasks)))
            row += 1

        layout.addWidget(self.router_table)

        # Universal Spoken Example Section
        example_header = QLabel("🎙️ Universal Spoken Example: How Each Model Responds", self)
        example_header.setStyleSheet("font-weight: 700; font-size: 15px; color: #38BDF8; margin-top: 16px;")
        layout.addWidget(example_header)

        example_intro = QLabel(
            "To demonstrate how each of the 6 models behaves, here is one single spoken audio test with filler words, contractions, a run-on sentence, and contrasting clauses:",
            self
        )
        example_intro.setWordWrap(True)
        example_intro.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(example_intro)

        # What you spoke card
        spoken_card = QFrame(self)
        spoken_card.setStyleSheet("QFrame { background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 12px; }")
        sc_layout = QVBoxLayout(spoken_card)
        sc_title = QLabel("🗣️ What You Spoke into the Microphone (Raw Spoken Audio with Fillers & Hesitations):", self)
        sc_title.setStyleSheet("font-weight: 600; font-size: 12px; color: #F59E0B; border: none;")
        sc_layout.addWidget(sc_title)

        sc_text = QLabel(
            "\"hey uh can you just say me how can i use this AI dictation because uh we havent finished the api backend yet but the frontend ui is almost done however uh i have given two datas can you just analyze and say me whether both datas are same or not and also remember to revert back to the team today thanks\"",
            self
        )
        sc_text.setWordWrap(True)
        sc_text.setStyleSheet("color: #F8FAFC; font-size: 12px; font-style: italic; border: none; padding-top: 4px;")
        sc_layout.addWidget(sc_text)
        layout.addWidget(spoken_card)

        # Model comparison items
        models_examples = [
            (
                "1. gemini-3.5-flash-lite (Lowest Latency < 1.0s — Currently Active Default)",
                "⚡ ~0.7s – 1.0s (Blazing Fast)",
                "100% filler removal ('uh', 'ah'), seamless Indian English upgrade ('say me' ➔ 'tell me', 'two datas' ➔ 'two datasets', 'revert back' ➔ 'reply'), crisp punctuation.",
                "Hey, can you tell me how to use this AI dictation tool? We haven't finished the API backend yet, but the frontend UI is almost done. However, I have provided two datasets; could you please analyze them and let me know if they are identical? Also, remember to reply to the team today. Thanks!",
                "Instant daily dictation across WhatsApp, ChatGPT, Antigravity, Slack, Discord, and search bars where speed (<1s) is essential."
            ),
            (
                "2. gemini-3.5-flash (Balanced Dictation & Prompt Enhancer)",
                "⚡ ~1.2s – 1.8s (Balanced & Fluid)",
                "Fluid grammatical flow. Uses semicolons (;) and em-dashes (—) for compound clauses, splits run-ons into natural sentences.",
                "Hey, could you explain how to use this AI dictation tool? We haven't finished the API backend yet; however, the frontend UI is nearly complete. I have provided two datasets—could you analyze them and verify whether they match? Also, please remember to follow up with the team today. Thanks!",
                "Daily emails, GitHub PR descriptions, ticket updates, and writing clear messages with natural cadence."
            ),
            (
                "3. gemini-3.6-flash (Fast Advanced Reasoning & Executive Polish)",
                "🚀 ~1.1s – 1.6s (Executive Grade)",
                "Native executive polish, superior vocabulary synthesis, elevated professional diction, rich semicolons, colons, and quotation formatting.",
                "Hey, could you please explain how to utilize this AI dictation tool? Although the frontend UI is nearly finished, the API backend remains in progress. I have provided two datasets for your review—could you examine both to determine if they are identical? Furthermore, please ensure you get back to the team today. Thank you!",
                "Executive emails, formal client proposals, pitch decks, high-impact AI prompt engineering, and professional publications."
            ),
            (
                "4. gemini-3.7-flash (Advanced Reasoning & Technical Dictation)",
                "⏱️ ~1.8s – 2.5s (Deep Technical Synthesis)",
                "Deep technical awareness. Formats variable names, API endpoints, code syntax, and logical conditional structures with precision.",
                "Hey, could you explain how to operate this AI dictation system? Our team has not yet completed the API backend, though the frontend UI is almost finalized. I have submitted two datasets: please analyze and verify if both data objects are identical. Additionally, remember to follow up with the engineering team today. Thanks!",
                "VS Code, terminal commands, writing technical documentation, software architecture notes, and developer prompts."
            ),
            (
                "5. gemini-2.5-flash (Standard Flash — Textbook Grammar)",
                "⏱️ ~2.0s – 3.0s (Academic Precision)",
                "Spends additional compute time refining formal syntax, formal clauses, and textbook grammatical rules.",
                "Hey, could you please explain how this AI dictation tool is used? We have not yet finished the API backend, but the frontend UI is almost done. However, I have provided two datasets; please analyze them and let me know if they are identical. Also, remember to get back to the team today. Thanks!",
                "Formal letters, academic papers, and official correspondence requiring strict textbook grammar."
            ),
            (
                "6. gemini-2.5-pro (Deep Thought & Document Generation)",
                "⏳ ~4.0s – 6.0s (Deepest Analysis)",
                "Synthesizes long stream-of-consciousness dictations into structured paragraphs, sections, and clear bulleted action items.",
                "Hey,\n\nCould you please explain how to use this AI dictation tool?\n\nKey Project Updates & Requests:\n• Backend: The API backend is still in progress.\n• Frontend: The UI is nearly complete.\n• Data Analysis: I have provided two datasets—please analyze them and confirm whether they are identical.\n• Follow-Up: Please remember to reply to the team with updates today.\n\nThank you!",
                "Long recordings (1–5 minutes of continuous talking), brainstorming sessions, meeting debriefs, and multi-step action plans."
            ),
        ]

        for m_name, speed, style, output, best_for in models_examples:
            m_card = QFrame(self)
            m_card.setStyleSheet("QFrame { background-color: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 12px; }")
            mc_layout = QVBoxLayout(m_card)
            mc_layout.setSpacing(6)

            m_title = QLabel(m_name, self)
            m_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #38BDF8; border: none;")
            mc_layout.addWidget(m_title)

            meta_lbl = QLabel(f"<b>Speed:</b> {speed} | <b>Grammar Style:</b> {style}", self)
            meta_lbl.setWordWrap(True)
            meta_lbl.setStyleSheet("color: #CBD5E1; font-size: 11px; border: none;")
            mc_layout.addWidget(meta_lbl)

            out_box = QLabel(f"<b>Output:</b>\n{output}", self)
            out_box.setWordWrap(True)
            out_box.setStyleSheet("background-color: #0F172A; border: 1px solid #1E293B; border-radius: 6px; padding: 8px; color: #10B981; font-size: 12px; font-family: Consolas, 'Segoe UI';")
            mc_layout.addWidget(out_box)

            best_lbl = QLabel(f"<b>Best Used For:</b> {best_for}", self)
            best_lbl.setWordWrap(True)
            best_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; border: none;")
            mc_layout.addWidget(best_lbl)

            layout.addWidget(m_card)

        # Quick Recommendation Guide Table
        guide_header = QLabel("📋 Quick Recommendation Guide", self)
        guide_header.setStyleSheet("font-weight: 700; font-size: 14px; color: #F59E0B; margin-top: 10px;")
        layout.addWidget(guide_header)

        guide_table = QTableWidget(self)
        guide_table.setColumnCount(3)
        guide_table.setHorizontalHeaderLabels(["If your priority is...", "Choose this Model in Settings", "Expected Latency"])
        guide_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        guide_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        guide_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        guide_table.setColumnWidth(1, 260)
        guide_table.setColumnWidth(2, 130)
        guide_table.verticalHeader().setVisible(False)
        guide_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        guide_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        guide_table.setMinimumHeight(240)

        guide_rows = [
            ("⚡ Ultra-Fast Speed (<1.0s) for WhatsApp, ChatGPT & Instant Dictation", "gemini-3.5-flash-lite (Active Default)", "~0.7s – 1.0s"),
            ("🚀 Executive Polish & Professional Business Proposal Quality", "gemini-3.6-flash", "~1.1s – 1.6s"),
            ("✨ Balanced Everyday Flow, Emails & Pull Request Notes", "gemini-3.5-flash", "~1.2s – 1.8s"),
            ("💻 Coding, Technical Architecture & Programming Prompts", "gemini-3.7-flash", "~1.8s – 2.5s"),
            ("📖 Formal Textbook Grammar & Academic Correspondence", "gemini-2.5-flash", "~2.0s – 3.0s"),
            ("📝 Long Recordings, Meeting Action Items & Structured Bullet Points", "gemini-2.5-pro", "~4.0s – 6.0s"),
        ]
        for r_idx, (prio, mdl, wait) in enumerate(guide_rows):
            guide_table.insertRow(r_idx)
            guide_table.setRowHeight(r_idx, 36)
            guide_table.setItem(r_idx, 0, QTableWidgetItem(prio))
            guide_table.setItem(r_idx, 1, QTableWidgetItem(mdl))
            guide_table.setItem(r_idx, 2, QTableWidgetItem(wait))

        layout.addWidget(guide_table)
        layout.addStretch()
        scroll.setWidget(tab)
        return scroll

    def _create_profiles_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QWidget#profileScrollChild { background: transparent; }")

        tab = QWidget()
        tab.setObjectName("profileScrollChild")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header = QLabel("⚡ Developer Productivity Profiles")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #F59E0B;")
        layout.addWidget(header)

        desc = QLabel("Select domain-specific tuning to align model parameters, system prompts, and vocabulary priorities.")
        desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(desc)

        # Profile combo
        sel_box = QHBoxLayout()
        sel_box.addWidget(QLabel("Active Profile:"))
        self.profile_combo = QComboBox(self)
        self.profile_combo.setView(QListView())
        for p in BUILTIN_PROFILES.values():
            self.profile_combo.addItem(f"{p.icon}  {p.name}", p.id)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_combo_changed)
        sel_box.addWidget(self.profile_combo, stretch=2)
        layout.addLayout(sel_box)

        # Profile Details Card
        detail_frame = QFrame(self)
        detail_frame.setStyleSheet("QFrame { background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 14px; }")
        df_layout = QVBoxLayout(detail_frame)
        df_layout.setSpacing(10)

        self.profile_desc_label = QLabel("", self)
        self.profile_desc_label.setWordWrap(True)
        self.profile_desc_label.setStyleSheet("color: #E2E8F0; font-size: 13px; font-weight: 500; border: none;")
        df_layout.addWidget(self.profile_desc_label)

        mod_box = QHBoxLayout()
        mod_box.addWidget(QLabel("Preferred AI Model:", self))
        self.profile_model_badge = QLabel("", self)
        self.profile_model_badge.setStyleSheet("color: #38BDF8; font-weight: 700; background: #1E293B; border: 1px solid #0284C7; border-radius: 6px; padding: 4px 10px;")
        mod_box.addWidget(self.profile_model_badge)
        mod_box.addStretch()
        df_layout.addLayout(mod_box)

        df_layout.addWidget(QLabel("Profile System Directives (Injected into Gemini system instructions):", self))
        self.profile_prompt_edit = QTextEdit(self)
        self.profile_prompt_edit.setMinimumHeight(100)
        self.profile_prompt_edit.setPlaceholderText("Profile directives...")
        df_layout.addWidget(self.profile_prompt_edit)

        vocab_p_box = QHBoxLayout()
        vocab_p_box.addWidget(QLabel("Priority Vocabulary Domains:", self))
        self.profile_vocab_tags = QLabel("", self)
        self.profile_vocab_tags.setStyleSheet("color: #A78BFA; font-weight: 600; border: none;")
        vocab_p_box.addWidget(self.profile_vocab_tags)
        vocab_p_box.addStretch()
        df_layout.addLayout(vocab_p_box)

        layout.addWidget(detail_frame)
        layout.addStretch()
        scroll.setWidget(tab)
        return scroll

    def _on_profile_combo_changed(self):
        prof_id = self.profile_combo.currentData()
        if prof_id in BUILTIN_PROFILES:
            p = BUILTIN_PROFILES[prof_id]
            self.profile_desc_label.setText(p.description)
            self.profile_model_badge.setText(f"💎 {p.preferred_model}")
            self.profile_prompt_edit.setPlainText(p.system_prompt_addition)
            self.profile_vocab_tags.setText(", ".join(p.vocabulary_categories) if p.vocabulary_categories else "General")

    def _create_vocabulary_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("🗂️ Personal AI Vocabulary Engine")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8;")
        layout.addWidget(header)

        desc = QLabel("Teaches Gemini your specific company terminology, project codenames, technical APIs, and phonetic name spellings.")
        desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(desc)

        # Search bar & actions
        top_box = QHBoxLayout()
        self.vocab_search = QLineEdit(self)
        self.vocab_search.setPlaceholderText("🔍 Search terms, spoken aliases, categories...")
        self.vocab_search.textChanged.connect(self._filter_vocab_table)
        top_box.addWidget(self.vocab_search, stretch=3)

        self.btn_add_vocab = QPushButton("➕ Add Term", self)
        self.btn_add_vocab.clicked.connect(self._on_add_vocab)
        top_box.addWidget(self.btn_add_vocab)

        self.btn_edit_vocab = QPushButton("✏️ Edit", self)
        self.btn_edit_vocab.setObjectName("secondaryBtn")
        self.btn_edit_vocab.clicked.connect(self._on_edit_vocab)
        top_box.addWidget(self.btn_edit_vocab)

        self.btn_delete_vocab = QPushButton("🗑️ Delete", self)
        self.btn_delete_vocab.setObjectName("dangerBtn")
        self.btn_delete_vocab.clicked.connect(self._on_delete_vocab)
        top_box.addWidget(self.btn_delete_vocab)

        layout.addLayout(top_box)

        # Vocab table
        self.vocab_table = QTableWidget(self)
        self.vocab_table.setColumnCount(4)
        self.vocab_table.setHorizontalHeaderLabels(["Canonical Term", "Spoken Aliases / Variants", "Category", "Status"])
        self.vocab_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.vocab_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.vocab_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.vocab_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.vocab_table.verticalHeader().setVisible(False)
        self.vocab_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.vocab_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.vocab_table.doubleClicked.connect(self._on_edit_vocab)
        layout.addWidget(self.vocab_table)

        # Normalization Sandbox
        sandbox_frame = QFrame(self)
        sandbox_frame.setStyleSheet("QFrame { background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 10px; }")
        sb_layout = QVBoxLayout(sandbox_frame)
        sb_layout.setSpacing(6)

        sb_title = QLabel("🧪 Live Normalization Sandbox (Test your vocabulary in real-time):", self)
        sb_title.setStyleSheet("font-weight: 600; font-size: 12px; color: #F59E0B; border: none;")
        sb_layout.addWidget(sb_title)

        self.vocab_test_input = QLineEdit("dr sriniwas awasti deployed type script and pytorch on git hub", self)
        self.vocab_test_input.setPlaceholderText("Type spoken text with aliases...")
        self.vocab_test_input.textChanged.connect(self._on_vocab_test_changed)
        sb_layout.addWidget(self.vocab_test_input)

        out_box = QHBoxLayout()
        out_box.addWidget(QLabel("Normalized Result:", self))
        self.vocab_test_output = QLabel("", self)
        self.vocab_test_output.setStyleSheet("color: #10B981; font-weight: 700; font-size: 13px; border: none;")
        out_box.addWidget(self.vocab_test_output, stretch=1)
        sb_layout.addLayout(out_box)

        layout.addWidget(sandbox_frame)
        return tab

    def _refresh_vocab_table(self):
        self.vocab_table.setRowCount(0)
        try:
            ve = VocabularyEngine()
            entries = ve.entries
            for row, e in enumerate(entries):
                self.vocab_table.insertRow(row)
                self.vocab_table.setRowHeight(row, 38)
                self.vocab_table.setItem(row, 0, QTableWidgetItem(e.canonical_term))
                self.vocab_table.setItem(row, 1, QTableWidgetItem(", ".join(e.aliases)))
                self.vocab_table.setItem(row, 2, QTableWidgetItem(e.category))
                self.vocab_table.setItem(row, 3, QTableWidgetItem("✅ Active" if e.enabled else "⏸️ Disabled"))
        except Exception as ex:
            logger.error(f"Error refreshing vocab table: {ex}")

    def _filter_vocab_table(self, query: str):
        q = (query or "").lower().strip()
        for r in range(self.vocab_table.rowCount()):
            c_term = self.vocab_table.item(r, 0).text().lower() if self.vocab_table.item(r, 0) else ""
            aliases = self.vocab_table.item(r, 1).text().lower() if self.vocab_table.item(r, 1) else ""
            cat = self.vocab_table.item(r, 2).text().lower() if self.vocab_table.item(r, 2) else ""
            match = (q in c_term) or (q in aliases) or (q in cat)
            self.vocab_table.setRowHidden(r, not match)

    def _on_add_vocab(self):
        dlg = VocabEditDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            ve = VocabularyEngine()
            ve.add_entry(VocabularyEntry(
                id=str(time.time()),
                canonical_term=data["canonical_term"],
                aliases=data["aliases"],
                category=data["category"],
                enabled=data["enabled"],
                notes=data["notes"]
            ))
            self._refresh_vocab_table()
            self._on_vocab_test_changed(self.vocab_test_input.text())

    def _on_edit_vocab(self):
        row = self.vocab_table.currentRow()
        if row < 0:
            return
        c_term = self.vocab_table.item(row, 0).text()
        ve = VocabularyEngine()
        entry = next((e for e in ve.entries if e.canonical_term == c_term), None)
        if not entry:
            return
        dlg = VocabEditDialog(
            canonical=entry.canonical_term,
            aliases=", ".join(entry.aliases),
            category=entry.category,
            enabled=entry.enabled,
            notes=entry.notes,
            parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            entry.canonical_term = data["canonical_term"]
            entry.aliases = data["aliases"]
            entry.category = data["category"]
            entry.enabled = data["enabled"]
            entry.notes = data["notes"]
            ve.save()
            self._refresh_vocab_table()
            self._on_vocab_test_changed(self.vocab_test_input.text())

    def _on_delete_vocab(self):
        row = self.vocab_table.currentRow()
        if row < 0:
            return
        c_term = self.vocab_table.item(row, 0).text()
        res = QMessageBox.question(self, "Delete Term", f"Delete '{c_term}' from your vocabulary engine?")
        if res == QMessageBox.StandardButton.Yes:
            ve = VocabularyEngine()
            ve.delete_entry(c_term)
            self._refresh_vocab_table()
            self._on_vocab_test_changed(self.vocab_test_input.text())

    def _on_vocab_test_changed(self, text: str):
        try:
            ve = VocabularyEngine()
            norm = ve.normalize(text)
            self.vocab_test_output.setText(norm)
        except Exception:
            self.vocab_test_output.setText(text)

    def _create_benchmark_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QWidget#benchScrollChild { background: transparent; }")

        tab = QWidget()
        tab.setObjectName("benchScrollChild")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header = QLabel("📊 AI Performance & Benchmark Dashboard")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8;")
        layout.addWidget(header)

        # Telemetry Stats Cards Grid
        metrics_frame = QFrame(self)
        metrics_frame.setStyleSheet("QFrame { background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 12px; }")
        mf_layout = QVBoxLayout(metrics_frame)
        mf_layout.setSpacing(8)

        mf_title = QLabel("📈 Live Operation Telemetry (P50, P95, Fallbacks & Utilization)", self)
        mf_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #10B981; border: none;")
        mf_layout.addWidget(mf_title)

        grid = QHBoxLayout()
        self.bench_stat_reqs = QLabel("Total Requests: 0\nWords Dictated: 0", self)
        self.bench_stat_reqs.setStyleSheet("background: #1E293B; padding: 8px 12px; border-radius: 6px; font-size: 12px; border: none;")
        grid.addWidget(self.bench_stat_reqs)

        self.bench_stat_lat = QLabel("Avg Latency: 0.0s\nP50: 0.0s | P95: 0.0s", self)
        self.bench_stat_lat.setStyleSheet("background: #1E293B; padding: 8px 12px; border-radius: 6px; font-size: 12px; border: none;")
        grid.addWidget(self.bench_stat_lat)

        self.bench_stat_rate = QLabel("Success Rate: 100.0%\nFallbacks Triggered: 0", self)
        self.bench_stat_rate.setStyleSheet("background: #1E293B; padding: 8px 12px; border-radius: 6px; font-size: 12px; border: none;")
        grid.addWidget(self.bench_stat_rate)
        mf_layout.addLayout(grid)
        layout.addWidget(metrics_frame)

        # 6-Model Benchmark Suite
        suite_frame = QFrame(self)
        suite_frame.setStyleSheet("QFrame { background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 12px; }")
        sf_layout = QVBoxLayout(suite_frame)
        sf_layout.setSpacing(10)

        sf_title = QLabel("🚀 6-Model Benchmark Suite (Per Gemini_Flow_AI_Models_Guide.md)", self)
        sf_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #F59E0B; border: none;")
        sf_layout.addWidget(sf_title)

        runner_box = QHBoxLayout()
        runner_box.addWidget(QLabel("Target Model:", self))
        self.bench_target_combo = QComboBox(self)
        self.bench_target_combo.setView(QListView())
        for m in MODEL_REGISTRY.keys():
            self.bench_target_combo.addItem(m, m)
        runner_box.addWidget(self.bench_target_combo, stretch=2)

        self.btn_run_suite = QPushButton("🚀 Run 6-Test Suite", self)
        self.btn_run_suite.clicked.connect(self._run_benchmark_suite)
        runner_box.addWidget(self.btn_run_suite)

        self.btn_reset_telemetry = QPushButton("Reset Stats", self)
        self.btn_reset_telemetry.setObjectName("secondaryBtn")
        self.btn_reset_telemetry.clicked.connect(self._reset_telemetry)
        runner_box.addWidget(self.btn_reset_telemetry)
        sf_layout.addLayout(runner_box)

        self.bench_progress_bar = QProgressBar(self)
        self.bench_progress_bar.setVisible(False)
        self.bench_progress_bar.setRange(0, len(BENCHMARK_TEST_SUITE))
        sf_layout.addWidget(self.bench_progress_bar)

        self.bench_status_label = QLabel("", self)
        self.bench_status_label.setStyleSheet("color: #38BDF8; font-size: 12px; border: none;")
        sf_layout.addWidget(self.bench_status_label)

        # Benchmark results table
        self.bench_table = QTableWidget(self)
        self.bench_table.setColumnCount(5)
        self.bench_table.setHorizontalHeaderLabels(["Test Category", "Model", "Latency (s)", "Quality Score", "Output Preview"])
        self.bench_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.bench_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.bench_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.bench_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.bench_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.bench_table.verticalHeader().setVisible(False)
        self.bench_table.setMinimumHeight(200)
        sf_layout.addWidget(self.bench_table)

        layout.addWidget(suite_frame)
        layout.addStretch()
        scroll.setWidget(tab)
        return scroll

    def _refresh_benchmark_stats(self):
        try:
            mt = MetricsTracker()
            sum_data = mt.get_summary()
            self.bench_stat_reqs.setText(f"Total Requests: {sum_data['total_requests']}\nWords Dictated: {sum_data['total_words']:,}")
            self.bench_stat_lat.setText(f"Avg Latency: {sum_data['avg_latency_sec']}s\nP50: {sum_data['p50_latency_sec']}s | P95: {sum_data['p95_latency_sec']}s")
            self.bench_stat_rate.setText(f"Success Rate: {sum_data['success_rate_pct']}%\nFallbacks: {sum_data['fallbacks_triggered']}")
        except Exception as ex:
            logger.debug(f"Error refreshing benchmark stats: {ex}")

    def _reset_telemetry(self):
        res = QMessageBox.question(self, "Reset Metrics", "Reset all latency, usage, and request counters?")
        if res == QMessageBox.StandardButton.Yes:
            mt = MetricsTracker()
            mt.clear_metrics()
            self._refresh_benchmark_stats()

    def _run_benchmark_suite(self):
        model = self.bench_target_combo.currentText()
        key = self.api_key_input.text().strip() or self.config.get_api_key()
        if not key:
            QMessageBox.warning(self, "Missing API Key", "Please configure your Gemini API Key in Settings first.")
            return

        self.btn_run_suite.setEnabled(False)
        self.bench_progress_bar.setVisible(True)
        self.bench_progress_bar.setValue(0)
        self.bench_status_label.setText(f"Running 6-category benchmark suite on {model}...")
        self.bench_table.setRowCount(0)

        def worker():
            from ..benchmark.benchmark_engine import BenchmarkEngine, BENCHMARK_TEST_SUITE
            results = []
            for i, tc in enumerate(BENCHMARK_TEST_SUITE):
                res = BenchmarkEngine.run_single_test(model, tc, key)
                results.append(res)
                # Update progress on UI thread
                QTimer.singleShot(0, lambda r=res, step=i+1: self._on_benchmark_step(r, step))
                time.sleep(0.2)

            QTimer.singleShot(0, lambda: self._on_benchmark_done(model))

        threading.Thread(target=worker, daemon=True).start()

    def _on_benchmark_step(self, result, step: int):
        self.bench_progress_bar.setValue(step)
        row = self.bench_table.rowCount()
        self.bench_table.insertRow(row)
        self.bench_table.setItem(row, 0, QTableWidgetItem(result.category))
        self.bench_table.setItem(row, 1, QTableWidgetItem(result.model_name))
        self.bench_table.setItem(row, 2, QTableWidgetItem(f"{result.latency_seconds:.2f}s"))
        score_text = f"{result.accuracy_score}/100" if result.success else "Failed"
        self.bench_table.setItem(row, 3, QTableWidgetItem(score_text))
        preview = result.output_text if result.success else result.error
        self.bench_table.setItem(row, 4, QTableWidgetItem(preview[:100]))

    def _on_benchmark_done(self, model: str):
        self.btn_run_suite.setEnabled(True)
        self.bench_progress_bar.setVisible(False)
        self.bench_status_label.setText(f"✅ Benchmark suite completed for {model}!")
        self._refresh_benchmark_stats()

    def _create_ai_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QWidget#aiScrollChild { background: transparent; }")

        tab = QWidget()
        tab.setObjectName("aiScrollChild")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Header & Intro
        ai_header = QLabel("🧠 AI Dictation & Custom Prompts Library", self)
        ai_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8;")
        layout.addWidget(ai_header)

        ai_desc = QLabel(
            "Configure your default dictation style, customize technical vocabulary, "
            "or manage your personal library of custom AI system prompts with instant live updating.",
            self
        )
        ai_desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        ai_desc.setWordWrap(True)
        layout.addWidget(ai_desc)

        # 1. Unified Dictation Styles & Prompts Card
        prompt_card = QFrame(self)
        prompt_card.setStyleSheet("QFrame { background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 14px; }")
        pc_layout = QVBoxLayout(prompt_card)
        pc_layout.setSpacing(10)

        # Header with active badge
        pc_header = QHBoxLayout()
        pc_title = QLabel("📚 Active Dictation Style & System Prompt", prompt_card)
        pc_title.setStyleSheet("font-weight: 700; font-size: 14px; color: #F59E0B; border: none;")
        pc_header.addWidget(pc_title)
        pc_header.addStretch()

        self.active_prompt_badge = QLabel("Active: Clean Speech & Grammar Enhancement", prompt_card)
        self.active_prompt_badge.setStyleSheet("color: #10B981; font-weight: bold; font-size: 11px; background: #064E3B; border-radius: 4px; padding: 3px 8px; border: none;")
        pc_header.addWidget(self.active_prompt_badge)
        pc_layout.addLayout(pc_header)

        # Selector Row
        sel_row = QHBoxLayout()
        sel_lbl = QLabel("Choose Dictation Style / Prompt:", prompt_card)
        sel_lbl.setStyleSheet("font-weight: 600; color: #E2E8F0;")
        sel_row.addWidget(sel_lbl)
        self.saved_prompts_combo = QComboBox(prompt_card)
        self.saved_prompts_combo.setView(QListView())
        self.saved_prompts_combo.currentIndexChanged.connect(self._on_saved_prompt_selected)
        sel_row.addWidget(self.saved_prompts_combo, stretch=2)
        pc_layout.addLayout(sel_row)
        sel_row.addWidget(self.saved_prompts_combo, stretch=2)
        pc_layout.addLayout(sel_row)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_new_prompt = QPushButton("➕ New Prompt", prompt_card)
        self.btn_new_prompt.setObjectName("secondaryBtn")
        self.btn_new_prompt.clicked.connect(self._on_new_saved_prompt)
        btn_row.addWidget(self.btn_new_prompt)

        self.btn_save_prompt = QPushButton("💾 Save / Update Prompt", prompt_card)
        self.btn_save_prompt.clicked.connect(self._on_save_custom_prompt)
        btn_row.addWidget(self.btn_save_prompt)

        self.btn_apply_prompt = QPushButton("⚡ Set as Active Prompt", prompt_card)
        self.btn_apply_prompt.setObjectName("secondaryBtn")
        self.btn_apply_prompt.clicked.connect(self._on_activate_saved_prompt)
        btn_row.addWidget(self.btn_apply_prompt)

        self.btn_delete_prompt = QPushButton("🗑️ Delete", prompt_card)
        self.btn_delete_prompt.setObjectName("dangerBtn")
        self.btn_delete_prompt.clicked.connect(self._on_delete_saved_prompt)
        btn_row.addWidget(self.btn_delete_prompt)

        btn_row.addStretch()
        pc_layout.addLayout(btn_row)

        # Prompt Title Input
        pc_layout.addWidget(QLabel("Prompt Title / Name:", prompt_card))
        self.prompt_title_input = QLineEdit(prompt_card)
        self.prompt_title_input.setPlaceholderText("e.g. Executive Email Polish, Technical Architecture, Python Docstrings...")
        self.prompt_title_input.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF; padding: 6px 10px;")
        pc_layout.addWidget(self.prompt_title_input)

        # Prompt Text Instructions
        pc_layout.addWidget(QLabel("Prompt System Instructions (Passed to Gemini AI):", prompt_card))
        self.custom_prompt_edit = QTextEdit(prompt_card)
        self.custom_prompt_edit.setPlaceholderText("Enter detailed system instructions for Gemini Flow...")
        self.custom_prompt_edit.setMinimumHeight(100)
        self.custom_prompt_edit.setMaximumHeight(140)
        pc_layout.addWidget(self.custom_prompt_edit)

        # Status feedback label
        self.prompt_status_label = QLabel("", prompt_card)
        self.prompt_status_label.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600; border: none;")
        pc_layout.addWidget(self.prompt_status_label)

        layout.addWidget(prompt_card)

        # 2. Custom Vocabulary Input
        vocab_card = QFrame(self)
        vocab_card.setStyleSheet("QFrame { background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 12px; }")
        vc_layout = QVBoxLayout(vocab_card)
        vc_layout.setSpacing(6)
        
        vocab_label = QLabel("🔤 Custom Vocabulary & Jargon (Comma Separated):", vocab_card)
        vocab_label.setStyleSheet("font-weight: 700; font-size: 13px; color: #38BDF8; border: none;")
        vc_layout.addWidget(vocab_label)
        
        self.vocab_input = QLineEdit(vocab_card)
        self.vocab_input.setPlaceholderText("e.g. Srinivas, Awasthi, Gemini, Wispr, PyTorch, LeetCode, TypeScript...")
        self.vocab_input.setStyleSheet("font-size: 13px; padding: 6px 10px;")
        vc_layout.addWidget(self.vocab_input)
        layout.addWidget(vocab_card)

        layout.addStretch()

        scroll.setWidget(tab)
        return scroll

    def _create_dictionary_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        desc = QLabel("📖 Custom Phonetic Dictionary: Teach Gemini Flow how you want specific names, jargon, or misheard words to be spelled.")
        desc.setStyleSheet("color: #94A3B8; font-size: 13px;")
        layout.addWidget(desc)

        top_box = QHBoxLayout()
        self.dict_search = QLineEdit(self)
        self.dict_search.setPlaceholderText("🔍 Filter dictionary words...")
        self.dict_search.textChanged.connect(self._filter_dictionary)
        top_box.addWidget(self.dict_search)

        self.btn_add_dict = QPushButton("➕ Add Word Pair", self)
        self.btn_add_dict.clicked.connect(self._add_dict_entry)
        top_box.addWidget(self.btn_add_dict)
        layout.addLayout(top_box)

        # Dictionary Table with natural width and high letter readability
        self.dict_table = QTableWidget(self)
        self.dict_table.setColumnCount(2)
        self.dict_table.setHorizontalHeaderLabels(["🗣️ Spoken / Heard Phrase", "✍️ Target Replacement Spelling"])
        self.dict_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dict_table.horizontalHeader().setFixedHeight(36)
        self.dict_table.verticalHeader().setDefaultSectionSize(46)
        self.dict_table.verticalHeader().setVisible(False)
        self.dict_table.setShowGrid(True)
        self.dict_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.dict_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.dict_table.itemClicked.connect(self._on_dict_row_selected)
        self.dict_table.itemDoubleClicked.connect(self._edit_dict_entry)
        layout.addWidget(self.dict_table)

        # Bottom action buttons (Previous layout: Edit Selected, Delete Selected, and status)
        action_box = QHBoxLayout()
        self.btn_edit_dict = QPushButton("✏️ Edit Selected", self)
        self.btn_edit_dict.setObjectName("secondaryBtn")
        self.btn_edit_dict.clicked.connect(self._edit_dict_entry)
        action_box.addWidget(self.btn_edit_dict)

        self.btn_delete_dict = QPushButton("🗑️ Delete Selected", self)
        self.btn_delete_dict.setObjectName("dangerBtn")
        self.btn_delete_dict.clicked.connect(self._delete_dict_entry)
        action_box.addWidget(self.btn_delete_dict)

        self.dict_selection_info = QLabel("", self)
        self.dict_selection_info.setStyleSheet("color: #38BDF8; font-weight: 600; font-size: 13px; padding-left: 8px;")
        action_box.addWidget(self.dict_selection_info)

        action_box.addStretch()
        layout.addLayout(action_box)

        return tab

    def _create_snippets_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        desc = QLabel("⚡ Quick Text: Speak a trigger phrase (e.g. 'Hey I am Srinivas LinkedIn GitHub Instagram') to paste multi-line templates or links.")
        desc.setStyleSheet("color: #94A3B8; font-size: 13px;")
        layout.addWidget(desc)

        top_box = QHBoxLayout()
        self.snippet_search = QLineEdit(self)
        self.snippet_search.setPlaceholderText("🔍 Filter quick text...")
        self.snippet_search.textChanged.connect(self._filter_snippets)
        top_box.addWidget(self.snippet_search)

        self.btn_add_snippet = QPushButton("➕ Add Quick Text", self)
        self.btn_add_snippet.clicked.connect(self._add_snippet_entry)
        top_box.addWidget(self.btn_add_snippet)
        layout.addLayout(top_box)

        # Quick Text Table
        self.snippet_table = QTableWidget(self)
        self.snippet_table.setColumnCount(2)
        self.snippet_table.setHorizontalHeaderLabels(["🗣️ Voice Trigger Phrase", "📄 Expanded Text Content"])
        self.snippet_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.snippet_table.horizontalHeader().setFixedHeight(36)
        self.snippet_table.verticalHeader().setDefaultSectionSize(46)
        self.snippet_table.verticalHeader().setVisible(False)
        self.snippet_table.setShowGrid(True)
        self.snippet_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.snippet_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.snippet_table.doubleClicked.connect(self._edit_snippet_entry)
        layout.addWidget(self.snippet_table)

        # Bottom table buttons
        action_box = QHBoxLayout()
        self.btn_edit_snippet = QPushButton("✏️ Edit Selected", self)
        self.btn_edit_snippet.setObjectName("secondaryBtn")
        self.btn_edit_snippet.clicked.connect(self._edit_snippet_entry)
        action_box.addWidget(self.btn_edit_snippet)

        self.btn_delete_snippet = QPushButton("🗑️ Delete Selected", self)
        self.btn_delete_snippet.setObjectName("dangerBtn")
        self.btn_delete_snippet.clicked.connect(self._delete_snippet_entry)
        action_box.addWidget(self.btn_delete_snippet)

        action_box.addStretch()
        layout.addLayout(action_box)

        return tab

    def _create_audio_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        mic_label = QLabel("Input Microphone:")
        layout.addWidget(mic_label)

        self.mic_combo = QComboBox(self)
        self.mic_combo.setView(QListView())
        self._populate_mics()
        layout.addWidget(self.mic_combo)

        # Live Test Level
        test_box = QHBoxLayout()
        self.btn_test_mic = QPushButton("Test Microphone", self)
        self.btn_test_mic.setObjectName("secondaryBtn")
        self.btn_test_mic.clicked.connect(self._toggle_mic_test)
        test_box.addWidget(self.btn_test_mic)

        self.mic_level_bar = QProgressBar(self)
        self.mic_level_bar.setRange(0, 100)
        self.mic_level_bar.setValue(0)
        self.mic_level_bar.setTextVisible(False)
        test_box.addWidget(self.mic_level_bar)
        layout.addLayout(test_box)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("background-color: #334155; max-height: 1px; margin: 6px 0;")
        layout.addWidget(sep)

        # DSP Audio Noise Filter Section
        dsp_header = QLabel("🌀 Real-Time DSP Audio Noise Suppression & Fan Filters:")
        dsp_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #38BDF8; margin-top: 4px;")
        layout.addWidget(dsp_header)

        self.cb_dsp_fan_filter = QCheckBox("🌀 Real-Time Ceiling Fan & AC Motor Rumble Filter (85 Hz Butterworth High-Pass)")
        self.cb_dsp_fan_filter.setStyleSheet("font-weight: 600; color: #F8FAFC;")
        layout.addWidget(self.cb_dsp_fan_filter)

        fan_desc = QLabel("   Attenuates 50/60 Hz electrical hums and 20-75 Hz ceiling fan blade motor rumble without voice distortion.")
        fan_desc.setStyleSheet("color: #94A3B8; font-size: 11px; margin-bottom: 4px;")
        layout.addWidget(fan_desc)

        self.cb_dsp_noise_gate = QCheckBox("🔇 Dynamic RMS Audio Noise Gate (Mutes background hiss, breath & room noise)")
        self.cb_dsp_noise_gate.setStyleSheet("font-weight: 600; color: #F8FAFC;")
        layout.addWidget(self.cb_dsp_noise_gate)

        gate_desc = QLabel("   Automatically suppresses background hiss, room echo, and quiet breaths during speech pauses.")
        gate_desc.setStyleSheet("color: #94A3B8; font-size: 11px; margin-bottom: 6px;")
        layout.addWidget(gate_desc)

        # Offline Fallback Engine Section
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        sep2.setStyleSheet("background-color: #334155; max-height: 1px; margin: 6px 0;")
        layout.addWidget(sep2)

        offline_header = QLabel("📡 Local Offline Speech Recognition Fallback:")
        offline_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #38BDF8; margin-top: 4px;")
        layout.addWidget(offline_header)

        self.cb_offline_fallback = QCheckBox("🎙️ Embedded Local Offline Speech Fallback (Windows SAPI / Local Dictation)")
        self.cb_offline_fallback.setStyleSheet("font-weight: 600; color: #F8FAFC;")
        layout.addWidget(self.cb_offline_fallback)

        offline_desc = QLabel("   Seamlessly switches to on-device speech recognition when internet drops or Wi-Fi disconnects.")
        offline_desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(offline_desc)

        layout.addStretch()
        return tab

    def _create_history_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # 1. Top Toolbar (Search, Favorites Toggle, Filter By Menu, Clear History)
        top_box = QHBoxLayout()
        top_box.setSpacing(8)

        self.history_search = QLineEdit(self)
        self.history_search.setPlaceholderText("🔍 Search transcripts, custom titles, apps, models...")
        self.history_search.textChanged.connect(self._on_search_text_changed)
        top_box.addWidget(self.history_search, stretch=3)

        self.btn_filter_favorites = QPushButton("⭐ Favorites", self)
        self.btn_filter_favorites.setCheckable(True)
        self.btn_filter_favorites.setObjectName("secondaryBtn")
        self.btn_filter_favorites.setMinimumHeight(36)
        self.btn_filter_favorites.setToolTip("Show only favorited transcripts")
        self.btn_filter_favorites.clicked.connect(self._toggle_favorite_filter)
        top_box.addWidget(self.btn_filter_favorites)

        self.btn_filter_by = QPushButton("🔽 Filter By", self)
        self.btn_filter_by.setObjectName("secondaryBtn")
        self.btn_filter_by.setMinimumHeight(36)
        self.btn_filter_by.clicked.connect(self._show_filter_menu)
        top_box.addWidget(self.btn_filter_by)

        self.btn_clear_history = QPushButton("🗑️ Clear History", self)
        self.btn_clear_history.setObjectName("dangerBtn")
        self.btn_clear_history.setMinimumHeight(36)
        self.btn_clear_history.setToolTip("Clear unpinned history (📌 pinned items are strictly preserved)")
        self.btn_clear_history.clicked.connect(self._clear_all_history)
        top_box.addWidget(self.btn_clear_history)

        layout.addLayout(top_box)

        # 2. Active Filter Tag Bar
        self.filter_tag_bar = QFrame(self)
        self.filter_tag_bar.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #0284C7;
                border-radius: 6px;
                padding: 4px 10px;
            }
        """)
        tag_layout = QHBoxLayout(self.filter_tag_bar)
        tag_layout.setContentsMargins(8, 4, 8, 4)
        tag_layout.setSpacing(8)

        self.filter_tag_label = QLabel("Active Filter:", self.filter_tag_bar)
        self.filter_tag_label.setStyleSheet("color: #38BDF8; font-weight: 600; font-size: 12px;")
        tag_layout.addWidget(self.filter_tag_label)
        tag_layout.addStretch()

        self.btn_clear_filter = QPushButton("✖ Reset Filter", self.filter_tag_bar)
        self.btn_clear_filter.setObjectName("secondaryBtn")
        self.btn_clear_filter.setStyleSheet("padding: 2px 10px; font-size: 11px; height: 24px;")
        self.btn_clear_filter.clicked.connect(self._reset_all_filters)
        tag_layout.addWidget(self.btn_clear_filter)

        self.filter_tag_bar.setVisible(False)
        layout.addWidget(self.filter_tag_bar)

        # 3. Main Hierarchical Tree Widget (QTreeWidget)
        self.history_tree = QTreeWidget(self)
        self.history_tree.setHeaderLabels(["Transcript / Title", "Application", "Model", "Time"])
        self.history_tree.setWordWrap(True)
        self.history_tree.setItemDelegateForColumn(0, HistoryTranscriptDelegate(self.history_tree))

        # Excel-like interactive column resizing
        header = self.history_tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.sectionHandleDoubleClicked.connect(self.history_tree.resizeColumnToContents)
        header.sectionResized.connect(lambda idx, o, n: self.history_tree.scheduleDelayedItemsLayout())

        self.history_tree.setColumnWidth(0, 460)
        self.history_tree.setColumnWidth(1, 130)
        self.history_tree.setColumnWidth(2, 140)
        self.history_tree.setColumnWidth(3, 110)
        self.history_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_tree.customContextMenuRequested.connect(self._show_history_context_menu)
        self.history_tree.itemSelectionChanged.connect(self._on_history_tree_selection_changed)
        self.history_tree.itemDoubleClicked.connect(lambda item, col: self._copy_selected_history())
        layout.addWidget(self.history_tree, stretch=3)

        # 4. Dedicated Selected Transcription Detail Card (Dual AI Prompt & Spoken Safeguard Inspector)
        self.history_card = QFrame(self)
        self.history_card.setStyleSheet("""
            QFrame {
                background-color: #0B1120;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        card_layout = QVBoxLayout(self.history_card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(8)

        # Detail Header & Badges
        card_header = QHBoxLayout()
        self.history_detail_title = QLabel("📄 Full Transcription Details:", self.history_card)
        self.history_detail_title.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 13px;")
        card_header.addWidget(self.history_detail_title)
        card_header.addStretch()

        self.history_badge_app = QLabel("", self.history_card)
        self.history_badge_app.setStyleSheet("color: #94A3B8; background-color: #1E293B; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
        card_header.addWidget(self.history_badge_app)

        self.history_badge_model = QLabel("", self.history_card)
        self.history_badge_model.setStyleSheet("color: #94A3B8; background-color: #1E293B; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
        card_header.addWidget(self.history_badge_model)

        self.history_badge_safeguard = QLabel("", self.history_card)
        self.history_badge_safeguard.setStyleSheet("color: #38BDF8; background-color: #0C4A6E; border: 1px solid #0284C7; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600;")
        self.history_badge_safeguard.setVisible(False)
        card_header.addWidget(self.history_badge_safeguard)

        card_layout.addLayout(card_header)

        # Multi-tab wrapped text preview for dual inspection (AI Prompt vs Normal Speech Safeguard)
        self.history_detail_tabs = QTabWidget(self.history_card)
        self.history_detail_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #1E293B;
                background-color: #0F172A;
                border-radius: 6px;
            }
            QTabBar::tab {
                background: #0B1120;
                color: #94A3B8;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #1E293B;
                color: #38BDF8;
                border-bottom: 2px solid #38BDF8;
            }
        """)

        # Tab 1: AI Prompt / Primary Text
        tab_prompt = QWidget()
        p_lay = QVBoxLayout(tab_prompt)
        p_lay.setContentsMargins(4, 4, 4, 4)
        self.history_detail_text = QTextEdit(tab_prompt)
        self.history_detail_text.setReadOnly(True)
        self.history_detail_text.setPlaceholderText("Select any transcript in the tree above to inspect and manage...")
        self.history_detail_text.setStyleSheet("""
            background-color: #0F172A;
            color: #FFFFFF;
            border: none;
            font-size: 13px;
            line-height: 1.5;
        """)
        p_lay.addWidget(self.history_detail_text)
        self.history_detail_tabs.addTab(tab_prompt, "✨ Converted AI Prompt")

        # Tab 2: Normal Spoken Dictation (Safeguard Backup)
        tab_raw = QWidget()
        r_lay = QVBoxLayout(tab_raw)
        r_lay.setContentsMargins(4, 4, 4, 4)
        self.history_raw_detail_text = QTextEdit(tab_raw)
        self.history_raw_detail_text.setReadOnly(True)
        self.history_raw_detail_text.setPlaceholderText("Exact normal spoken speech (safeguard recovery)...")
        self.history_raw_detail_text.setStyleSheet("""
            background-color: #0F172A;
            color: #38BDF8;
            border: none;
            font-size: 13px;
            line-height: 1.5;
        """)
        r_lay.addWidget(self.history_raw_detail_text)
        self.history_detail_tabs.addTab(tab_raw, "🗣️ Normal Spoken Speech (Safeguard Backup)")

        self.history_detail_tabs.setMaximumHeight(130)
        card_layout.addWidget(self.history_detail_tabs)

        # Action Buttons Row (Pin, Favorite, Rename, Copy Prompt, Copy Speech, Reinsert Prompt, Reinsert Speech, Delete)
        action_row = QHBoxLayout()
        action_row.setSpacing(6)

        self.btn_pin_selected = QPushButton("📌 Pin", self.history_card)
        self.btn_pin_selected.setObjectName("secondaryBtn")
        self.btn_pin_selected.clicked.connect(self._toggle_pin_selected)
        self.btn_pin_selected.setEnabled(False)
        action_row.addWidget(self.btn_pin_selected)

        self.btn_fav_selected = QPushButton("⭐ Favorite", self.history_card)
        self.btn_fav_selected.setObjectName("secondaryBtn")
        self.btn_fav_selected.clicked.connect(self._toggle_fav_selected)
        self.btn_fav_selected.setEnabled(False)
        action_row.addWidget(self.btn_fav_selected)

        self.btn_rename_selected = QPushButton("✏️ Rename", self.history_card)
        self.btn_rename_selected.setObjectName("secondaryBtn")
        self.btn_rename_selected.clicked.connect(self._rename_selected_history)
        self.btn_rename_selected.setEnabled(False)
        action_row.addWidget(self.btn_rename_selected)

        self.btn_copy_selected = QPushButton("✨ Copy AI Prompt", self.history_card)
        self.btn_copy_selected.setObjectName("secondaryBtn")
        self.btn_copy_selected.clicked.connect(self._copy_selected_history)
        self.btn_copy_selected.setEnabled(False)
        action_row.addWidget(self.btn_copy_selected)

        self.btn_copy_raw_selected = QPushButton("🗣️ Copy Normal Speech", self.history_card)
        self.btn_copy_raw_selected.setObjectName("secondaryBtn")
        self.btn_copy_raw_selected.setStyleSheet("background-color: #1E293B; color: #38BDF8; border: 1px solid #0284C7;")
        self.btn_copy_raw_selected.clicked.connect(self._copy_raw_selected_history)
        self.btn_copy_raw_selected.setVisible(False)
        self.btn_copy_raw_selected.setEnabled(False)
        action_row.addWidget(self.btn_copy_raw_selected)

        self.btn_reinsert_selected = QPushButton("🚀 Paste AI Prompt", self.history_card)
        self.btn_reinsert_selected.setStyleSheet("background-color: #0284C7; color: white; font-weight: 600; padding: 6px 14px;")
        self.btn_reinsert_selected.clicked.connect(self._reinsert_selected_history)
        self.btn_reinsert_selected.setEnabled(False)
        action_row.addWidget(self.btn_reinsert_selected)

        self.btn_reinsert_raw_selected = QPushButton("🗣️ Paste Normal Speech", self.history_card)
        self.btn_reinsert_raw_selected.setStyleSheet("background-color: #1E293B; color: #38BDF8; font-weight: 600; padding: 6px 14px; border: 1px solid #0284C7;")
        self.btn_reinsert_raw_selected.clicked.connect(self._reinsert_raw_selected_history)
        self.btn_reinsert_raw_selected.setVisible(False)
        self.btn_reinsert_raw_selected.setEnabled(False)
        action_row.addWidget(self.btn_reinsert_raw_selected)

        action_row.addStretch()

        self.btn_delete_selected = QPushButton("🗑️ Delete", self.history_card)
        self.btn_delete_selected.setObjectName("dangerBtn")
        self.btn_delete_selected.clicked.connect(self._delete_selected_history)
        self.btn_delete_selected.setEnabled(False)
        action_row.addWidget(self.btn_delete_selected)

        card_layout.addLayout(action_row)

        layout.addWidget(self.history_card, stretch=2)
        return tab

    def _create_cost_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QWidget#costScrollChild { background: transparent; }")

        tab = QWidget()
        tab.setObjectName("costScrollChild")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. Top Hero Card: 🏆 Writing Publication Milestones & Total Words (Clean & Clutter-Free)
        milestone_card = QFrame(self)
        milestone_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0B132B, stop:1 #1C2541);
                border: 2px solid #38BDF8;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        m_layout = QVBoxLayout(milestone_card)
        m_layout.setContentsMargins(16, 14, 16, 14)
        m_layout.setSpacing(10)

        m_top = QHBoxLayout()
        m_title = QLabel("🏆 Total Spoken Words & Writing Publication Milestone", milestone_card)
        m_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #38BDF8; border: none;")
        m_top.addWidget(m_title)
        m_top.addStretch()

        self.lbl_milestone_badge = QLabel("🎙️ Voice Novice", milestone_card)
        self.lbl_milestone_badge.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 12px; background: #0284C7; border-radius: 6px; padding: 4px 12px; border: none;")
        m_top.addWidget(self.lbl_milestone_badge)
        m_layout.addLayout(m_top)

        self.lbl_milestone_desc = QLabel("Start dictating to unlock voice writing milestones!", milestone_card)
        self.lbl_milestone_desc.setWordWrap(True)
        self.lbl_milestone_desc.setStyleSheet("color: #F8FAFC; font-size: 13px; font-weight: 500; border: none;")
        m_layout.addWidget(self.lbl_milestone_desc)

        # Progress bar to next milestone
        self.milestone_progress_bar = QProgressBar(milestone_card)
        self.milestone_progress_bar.setRange(0, 100)
        self.milestone_progress_bar.setValue(0)
        self.milestone_progress_bar.setTextVisible(True)
        self.milestone_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 6px;
                background: #0B1120;
                text-align: center;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
                min-height: 26px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:0.5 #38BDF8, stop:1 #818CF8);
                border-radius: 5px;
            }
        """)
        m_layout.addWidget(self.milestone_progress_bar)

        layout.addWidget(milestone_card)

        # 2. Temporal Usage & Productivity Cards (Today, This Week, All-Time)
        temporal_title = QLabel("📊 Temporal Usage & Time Saved Summary")
        temporal_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #F8FAFC; margin-top: 4px;")
        layout.addWidget(temporal_title)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        def create_stat_card(card_title: str, title_color: str, border_color: str = "#334155"):
            card = QFrame(self)
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: #0F172A;
                    border: 1px solid {border_color};
                    border-radius: 10px;
                }}
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(14, 12, 14, 12)
            c_layout.setSpacing(10)

            labels: Dict[str, QLabel] = {}

            # Header row
            header_row = QHBoxLayout()
            t_lbl = QLabel(card_title, card)
            t_lbl.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {title_color}; border: none;")
            header_row.addWidget(t_lbl)
            header_row.addStretch()

            # Scope Badge
            m_badge = QLabel("🎙️ Voice Initiate", card)
            m_badge.setStyleSheet(f"color: {title_color}; background-color: #1E293B; border: 1px solid {border_color}; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600; border: none;")
            header_row.addWidget(m_badge)
            labels["milestone_scope"] = m_badge
            c_layout.addLayout(header_row)

            # Hero Stat Highlight Box (Net Time Saved)
            hero_box = QFrame(card)
            hero_box.setStyleSheet(f"""
                QFrame {{
                    background-color: #070D19;
                    border: 1px solid {border_color};
                    border-radius: 8px;
                    padding: 8px;
                }}
            """)
            hb_layout = QVBoxLayout(hero_box)
            hb_layout.setContentsMargins(10, 8, 10, 8)
            hb_layout.setSpacing(4)

            hb_top = QHBoxLayout()
            time_saved_lbl = QLabel("⚡ +0s Saved", hero_box)
            time_saved_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {title_color}; border: none;")
            hb_top.addWidget(time_saved_lbl)
            hb_top.addStretch()

            speedup_lbl = QLabel("🚀 0.0x Faster", hero_box)
            speedup_lbl.setStyleSheet("color: #10B981; font-weight: bold; font-size: 11px; background: #064E3B; border-radius: 4px; padding: 2px 6px; border: none;")
            hb_top.addWidget(speedup_lbl)
            hb_layout.addLayout(hb_top)

            comparison_lbl = QLabel("⏱️ 0s speaking vs 0s typing", hero_box)
            comparison_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; border: none;")
            hb_layout.addWidget(comparison_lbl)

            c_layout.addWidget(hero_box)

            labels["time_saved_hero"] = time_saved_lbl
            labels["speedup_badge"] = speedup_lbl
            labels["time_comparison"] = comparison_lbl
            labels["time_saved"] = time_saved_lbl
            labels["speaking_time"] = comparison_lbl

            # Metric Details Grid
            grid_frame = QFrame(card)
            grid_frame.setStyleSheet("background: transparent; border: none;")
            grid_layout = QVBoxLayout(grid_frame)
            grid_layout.setContentsMargins(0, 0, 0, 0)
            grid_layout.setSpacing(6)

            metric_rows = [
                ("words", "📝 Spoken Words:", "0 words", "#F8FAFC", True),
                ("dictations", "🎙️ Dictations:", "0 dictations", "#CBD5E1", False),
                ("transforms", "✨ AI Prompts:", "0 transforms", "#CBD5E1", False),
                ("tokens_used", "📊 Tokens Used:", "0 tokens", "#38BDF8", False),
                ("tokens_left", "🟢 Tokens Remaining:", "1,000,000 (100% Left)", "#10B981", True),
                ("cost", "💲 Est. API Cost:", "$0.0000 USD", "#F59E0B", True),
            ]

            for key, prompt_txt, def_val, val_color, is_bold in metric_rows:
                r_box = QHBoxLayout()
                p_lbl = QLabel(prompt_txt, grid_frame)
                p_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; border: none;")
                r_box.addWidget(p_lbl)
                r_box.addStretch()

                v_lbl = QLabel(def_val, grid_frame)
                weight_str = "font-weight: bold;" if is_bold else ""
                v_lbl.setStyleSheet(f"color: {val_color}; font-size: 12px; {weight_str} border: none;")
                r_box.addWidget(v_lbl)
                grid_layout.addLayout(r_box)
                labels[key] = v_lbl

            c_layout.addWidget(grid_frame)
            return card, labels

        self.today_card, self.today_labels = create_stat_card("📅 Today", "#38BDF8", "#0284C7")
        self.week_card, self.week_labels = create_stat_card("🗓️ This Week", "#A78BFA", "#6366F1")
        self.all_card, self.all_labels = create_stat_card("🏆 All-Time", "#F59E0B", "#D97706")

        cards_layout.addWidget(self.today_card)
        cards_layout.addWidget(self.week_card)
        cards_layout.addWidget(self.all_card)
        layout.addLayout(cards_layout)

        # 3. Auto Cost Mode Economizer Card
        auto_cost_card = QFrame(self)
        auto_cost_card.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        ac_layout = QVBoxLayout(auto_cost_card)
        ac_layout.setContentsMargins(12, 12, 12, 12)
        ac_layout.setSpacing(8)

        ac_header = QHBoxLayout()
        ac_title = QLabel("⚡ Auto Cost Mode (Smart Economizer)", auto_cost_card)
        ac_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F59E0B; border: none;")
        ac_header.addWidget(ac_title)
        ac_header.addStretch()

        self.auto_cost_badge = QLabel("🟢 Auto Cost Optimization: ACTIVE", auto_cost_card)
        self.auto_cost_badge.setStyleSheet("color: #10B981; font-weight: bold; font-size: 11px; background: #064E3B; border-radius: 4px; padding: 3px 8px; border: none;")
        ac_header.addWidget(self.auto_cost_badge)
        ac_layout.addLayout(ac_header)

        ac_desc = QLabel(
            "Dynamically routes everyday speech to ultra-low-cost gemini-3.5-flash-lite (<1.5s latency, ~85% cheaper) "
            "while automatically reserving heavier models (gemini-3.7-flash and gemini-2.5-pro) for long transformations and code.",
            auto_cost_card
        )
        ac_desc.setWordWrap(True)
        ac_desc.setStyleSheet("color: #94A3B8; font-size: 12px; border: none;")
        ac_layout.addWidget(ac_desc)

        self.cb_auto_cost_mode = QCheckBox("Enable Auto Cost Mode (Recommended for maximum speed and lowest API costs)", auto_cost_card)
        self.cb_auto_cost_mode.setStyleSheet("color: #F8FAFC; font-weight: 600; font-size: 12px; border: none;")
        self.cb_auto_cost_mode.setChecked(True)
        self.cb_auto_cost_mode.toggled.connect(self._on_auto_cost_toggled)
        ac_layout.addWidget(self.cb_auto_cost_mode)

        layout.addWidget(auto_cost_card)

        # 4. Interactive Voice AI Cost & ROI Predictor
        predictor_card = QFrame(self)
        predictor_card.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        pred_layout = QVBoxLayout(predictor_card)
        pred_layout.setContentsMargins(12, 12, 12, 12)
        pred_layout.setSpacing(10)

        pred_title = QLabel("🧮 Interactive Voice AI Cost & Productivity Predictor", predictor_card)
        pred_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #38BDF8; border: none;")
        pred_layout.addWidget(pred_title)

        pred_desc = QLabel(
            "Adjust your estimated daily voice usage below to see projected monthly word output, time saved, and API cost comparison:",
            predictor_card
        )
        pred_desc.setStyleSheet("color: #94A3B8; font-size: 12px; border: none;")
        pred_layout.addWidget(pred_desc)

        pred_control_row = QHBoxLayout()
        pred_control_row.addWidget(QLabel("Select Daily Dictation Volume:", predictor_card))
        self.pred_volume_combo = QComboBox(predictor_card)
        self.pred_volume_combo.addItem("15 Mins / day — Casual Notes & Quick Searches (~2,250 words/day)", 15)
        self.pred_volume_combo.addItem("30 Mins / day — Active Developer & Emails (~4,500 words/day)", 30)
        self.pred_volume_combo.addItem("1 Hour / day — Heavy Dictation & Coding (~9,000 words/day)", 60)
        self.pred_volume_combo.addItem("2 Hours / day — Full Workflow / Articles (~18,000 words/day)", 120)
        self.pred_volume_combo.addItem("4 Hours / day — Professional Author / Transcriber (~36,000 words/day)", 240)
        self.pred_volume_combo.setCurrentIndex(1)  # Default 30 mins
        self.pred_volume_combo.currentIndexChanged.connect(self._update_cost_prediction)
        self.pred_volume_combo.activated.connect(self._update_cost_prediction)
        pred_control_row.addWidget(self.pred_volume_combo, stretch=2)
        pred_layout.addLayout(pred_control_row)

        # 4 Projection Output Tiles in a row
        pred_tiles_row = QHBoxLayout()
        pred_tiles_row.setSpacing(8)

        def create_pred_tile(title: str, accent_color: str):
            tile = QFrame(predictor_card)
            tile.setStyleSheet(f"""
                QFrame {{
                    background-color: #070D19;
                    border: 1px solid #1E293B;
                    border-radius: 6px;
                    padding: 8px;
                }}
            """)
            tl = QVBoxLayout(tile)
            tl.setContentsMargins(8, 8, 8, 8)
            tl.setSpacing(4)
            t_lbl = QLabel(title, tile)
            t_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; border: none;")
            tl.addWidget(t_lbl)
            v_lbl = QLabel("...", tile)
            v_lbl.setStyleSheet(f"color: {accent_color}; font-size: 13px; font-weight: bold; border: none;")
            v_lbl.setWordWrap(True)
            tl.addWidget(v_lbl)
            return tile, v_lbl

        t1, self.pred_lbl_words = create_pred_tile("📝 Monthly Words Output", "#38BDF8")
        t2, self.pred_lbl_time = create_pred_tile("⚡ Monthly Time Saved", "#10B981")
        t3, self.pred_lbl_cost = create_pred_tile("💲 Est. Gemini API Cost / Mo", "#F59E0B")
        t4, self.pred_lbl_savings = create_pred_tile("💰 Annual Savings vs Paid Tools", "#EC4899")

        pred_tiles_row.addWidget(t1)
        pred_tiles_row.addWidget(t2)
        pred_tiles_row.addWidget(t3)
        pred_tiles_row.addWidget(t4)
        pred_layout.addLayout(pred_tiles_row)

        layout.addWidget(predictor_card)

        # 5. Official Google Gemini Pricing Matrix (Crystal Clear Table)
        pricing_card = QFrame(self)
        pricing_card.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        p_layout = QVBoxLayout(pricing_card)
        p_layout.setContentsMargins(12, 12, 12, 12)
        p_layout.setSpacing(8)

        p_title = QLabel("🏷️ Google Gemini Official API Pricing Matrix", pricing_card)
        p_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #38BDF8; border: none;")
        p_layout.addWidget(p_title)

        p_subtitle = QLabel("Official pay-as-you-go developer rates directly from Google Cloud AI. No monthly subscriptions required.", pricing_card)
        p_subtitle.setStyleSheet("color: #94A3B8; font-size: 12px; border: none;")
        p_layout.addWidget(p_subtitle)

        self.pricing_table = QTableWidget(self)
        self.pricing_table.setColumnCount(5)
        self.pricing_table.setHorizontalHeaderLabels([
            "AI Model",
            "Audio Dictation Rate",
            "Input / 1M Tokens",
            "Output / 1M Tokens",
            "Latency & Cost Tier"
        ])
        self.pricing_table.setStyleSheet("""
            QTableWidget {
                background-color: #0B1120;
                color: #F8FAFC;
                gridline-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                font-size: 12px;
                outline: none;
            }
            QHeaderView::section {
                background-color: #1E293B;
                color: #38BDF8;
                font-weight: bold;
                font-size: 12px;
                padding: 8px 10px;
                border: none;
                border-bottom: 2px solid #38BDF8;
                border-right: 1px solid #334155;
            }
            QTableWidget::item {
                padding: 6px 10px;
                border-bottom: 1px solid #1E293B;
            }
            QTableWidget::item:selected {
                background-color: #1E293B;
                color: #38BDF8;
            }
        """)
        self.pricing_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.pricing_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.pricing_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.pricing_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.pricing_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.pricing_table.setColumnWidth(0, 180)
        self.pricing_table.setColumnWidth(1, 150)
        self.pricing_table.setColumnWidth(2, 130)
        self.pricing_table.setColumnWidth(3, 130)
        self.pricing_table.verticalHeader().setVisible(False)
        self.pricing_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.pricing_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.pricing_table.setMinimumHeight(240)

        p_row = 0
        for m_id, p_info in MODEL_PRICING.items():
            self.pricing_table.insertRow(p_row)
            self.pricing_table.setRowHeight(p_row, 34)

            # Model item
            item_model = QTableWidgetItem(f"⚡ {p_info['display_name']}")
            item_model.setForeground(QColor("#38BDF8"))
            item_model.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.pricing_table.setItem(p_row, 0, item_model)

            # Audio Rate
            audio_rate_str = f"${p_info['audio_per_sec'] * 60:.4f} / min"
            item_audio = QTableWidgetItem(audio_rate_str)
            item_audio.setForeground(QColor("#10B981"))
            item_audio.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            item_audio.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.pricing_table.setItem(p_row, 1, item_audio)

            # Input Tokens
            item_input = QTableWidgetItem(f"${p_info['input_per_m']:.3f}")
            item_input.setForeground(QColor("#CBD5E1"))
            item_input.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.pricing_table.setItem(p_row, 2, item_input)

            # Output Tokens
            item_output = QTableWidgetItem(f"${p_info['output_per_m']:.2f}")
            item_output.setForeground(QColor("#CBD5E1"))
            item_output.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.pricing_table.setItem(p_row, 3, item_output)

            # Tier & Latency
            item_tier = QTableWidgetItem(p_info["tier"])
            item_tier.setForeground(QColor("#94A3B8"))
            self.pricing_table.setItem(p_row, 4, item_tier)

            p_row += 1

        p_layout.addWidget(self.pricing_table)
        layout.addWidget(pricing_card)

        # Trigger initial prediction calculation
        self._update_cost_prediction()

        layout.addStretch()
        scroll.setWidget(tab)
        return scroll

    def _update_cost_prediction(self, *args):
        """Calculates interactive monthly voice output, time savings, and API cost projections."""
        if not hasattr(self, 'pred_volume_combo') or not hasattr(self, 'pred_lbl_words'):
            return
        daily_mins = self.pred_volume_combo.currentData() or 30
        days_per_month = 30
        monthly_mins = daily_mins * days_per_month

        # Average speaking speed: ~150 words/min
        monthly_words = monthly_mins * 150

        # Typing duration at 40 WPM:
        typing_mins = monthly_words / 40.0
        time_saved_hours = max(0.0, (typing_mins - monthly_mins) / 60.0)

        # Gemini Flash-Lite pricing: $0.0012/min audio
        flash_lite_cost = monthly_mins * (0.000020 * 60)
        # Commercial voice AI tool baseline: ~$20.00 / month ($240 / year)
        annual_saved = (20.0 - flash_lite_cost) * 12.0

        # Books equivalent
        books_eq = monthly_words / 50000.0

        self.pred_lbl_words.setText(f"{monthly_words:,} words\n(~{books_eq:.1f} Full Books)")
        self.pred_lbl_time.setText(f"~{time_saved_hours:.1f} Hours Saved\n({time_saved_hours/8.0:.1f} full work days)")
        self.pred_lbl_cost.setText(f"~${flash_lite_cost:.2f} / mo\n(Virtually Free!)")
        self.pred_lbl_savings.setText(f"Save ~${annual_saved:.2f}/yr\n(99.5% Savings vs $20/mo)")

    def _on_auto_cost_toggled(self, checked: bool):
        if hasattr(self, 'auto_cost_badge') and self.auto_cost_badge:
            if checked:
                self.auto_cost_badge.setText("🟢 Auto Cost Optimization: ACTIVE")
                self.auto_cost_badge.setStyleSheet("color: #10B981; font-weight: bold; font-size: 11px; background: #064E3B; border-radius: 4px; padding: 3px 8px; border: none;")
            else:
                self.auto_cost_badge.setText("⚪ Auto Cost Optimization: OFF")
                self.auto_cost_badge.setStyleSheet("color: #94A3B8; font-weight: 500; font-size: 11px; background: #1E293B; border-radius: 4px; padding: 3px 8px; border: none;")
        self.config.set("auto_cost_mode", checked)

    def _refresh_cost_stats(self):
        """Calculates and refreshes the live Cost & Productivity metrics across Today, This Week, and All-Time."""
        if not hasattr(self, 'today_labels') or not self.today_labels:
            return
        try:
            history = self.config.get_history()
            stats = CostAwarenessTracker.get_aggregated_stats(history, current_api_key=self.config.get_api_key())

            def _update_card_labels(labels: Dict[str, QLabel], data: Dict[str, Any]):
                if "milestone_scope" in labels:
                    m_title = data.get("milestone_title", "Voice Initiate")
                    short_title = m_title.split("(")[0].strip()
                    labels["milestone_scope"].setText(short_title)
                if "time_saved_hero" in labels:
                    labels["time_saved_hero"].setText(f"⚡ +{data['time_saved_str']} Saved")
                if "speedup_badge" in labels:
                    labels["speedup_badge"].setText(f"🚀 {data['speedup_multiplier']} Faster")
                if "time_comparison" in labels:
                    labels["time_comparison"].setText(f"⏱️ {data['speaking_time_str']} speaking vs ~{data['typing_time_str']} typing")
                if "words" in labels:
                    labels["words"].setText(f"{data['total_words']:,} words")
                if "dictations" in labels:
                    labels["dictations"].setText(f"{data['dictations']} dictation{'s' if data['dictations'] != 1 else ''}")
                if "transforms" in labels:
                    labels["transforms"].setText(f"{data['transformations']} transform{'s' if data['transformations'] != 1 else ''}")
                if "tokens_used" in labels:
                    labels["tokens_used"].setText(data.get("tokens_used_str", "0 tokens"))
                if "tokens_left" in labels:
                    labels["tokens_left"].setText(data.get("tokens_left_str", "1,000,000 (100% Left)"))
                if "cost" in labels:
                    labels["cost"].setText(data["cost_formatted"])

            _update_card_labels(self.today_labels, stats["today"])
            _update_card_labels(self.week_labels, stats["this_week"])
            _update_card_labels(self.all_labels, stats["all_time"])

            # Update Gamified Milestones Hero Card (Clean & Clutter-Free)
            milestone: MilestoneInfo = stats["milestone"]
            self.lbl_milestone_badge.setText(milestone.rank_title)
            self.lbl_milestone_desc.setText(
                f"🎉 You have dictated {milestone.current_words:,} total words so far! {milestone.description}"
            )
            self.milestone_progress_bar.setValue(int(milestone.progress_pct))
            next_short = milestone.next_milestone_title.split('(')[0].strip()
            self.milestone_progress_bar.setFormat(
                f"{milestone.current_words:,} / {milestone.next_milestone_words:,} words ({milestone.progress_pct:.1f}% to {next_short})"
            )
        except Exception as e:
            logger.error(f"Error refreshing cost statistics: {e}", exc_info=True)

    def _populate_mics(self):
        self.mic_combo.clear()
        self.mic_combo.addItem("Default System Microphone", None)
        devices = AudioRecorder.get_input_devices()
        for dev in devices:
            self.mic_combo.addItem(f"{dev['name']} (ID: {dev['index']})", dev['index'])

    def _load_values(self):
        # API Key
        self.api_key_input.setText(self.config.get_api_key())

        # Model / Routing Mode
        model_mode = self.config.get("model_mode", "auto")
        if model_mode == "auto":
            self.model_combo.setCurrentIndex(0)
        else:
            model_name = self.config.get("model_name", "gemini-3.5-flash-lite")
            found = False
            for i in range(1, self.model_combo.count()):
                if self.model_combo.itemText(i).startswith(model_name):
                    self.model_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self.model_combo.setCurrentIndex(0)

        if hasattr(self, 'router_model_combo'):
            self.router_model_combo.blockSignals(True)
            self.router_model_combo.setCurrentIndex(self.model_combo.currentIndex())
            self.router_model_combo.blockSignals(False)

        # Modes
        mode = self.config.get("hotkey_mode", "toggle")
        if mode == "push_to_talk":
            self.radio_ptt.setChecked(True)
        else:
            self.radio_toggle.setChecked(True)

        hotkey_disp = self.config.get("hotkey_display", "Ctrl + Win")
        hotkey_inter = self.config.get("hotkey", "<ctrl>+<cmd>")
        self.hotkey_btn.set_hotkey(hotkey_disp, hotkey_inter)

        prompt_disp = self.config.get("prompt_hotkey_display", "Ctrl + Shift + P")
        prompt_inter = self.config.get("prompt_hotkey", "<ctrl>+<shift>+p")
        self.prompt_hotkey_btn.set_hotkey(prompt_disp, prompt_inter)

        trans_disp = self.config.get("transform_hotkey_display", "Ctrl + Shift + T")
        trans_inter = self.config.get("transform_hotkey", "<ctrl>+<shift>+t")
        self.transform_hotkey_btn.set_hotkey(trans_disp, trans_inter)

        # Profiles
        active_prof = self.config.get("active_profile", "coding")
        idx = self.profile_combo.findData(active_prof)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)
        self._on_profile_combo_changed()

        # Security & Retention (enforced automatically in background)
        sec_cfg = self.config.get("security", {})
        if hasattr(self, 'cb_log_redaction') and self.cb_log_redaction:
            self.cb_log_redaction.setChecked(sec_cfg.get("log_redaction", True))
        if hasattr(self, 'retention_combo') and self.retention_combo:
            ret_days = sec_cfg.get("history_retention_days", 30)
            ret_idx = self.retention_combo.findData(ret_days)
            if ret_idx >= 0:
                self.retention_combo.setCurrentIndex(ret_idx)

        self.cb_auto_paste.setChecked(self.config.get("auto_paste", True))
        self.cb_sounds.setChecked(self.config.get("play_sounds", True))
        self.cb_auto_prompt.setChecked(self.config.get("auto_prompt_conversion", False))
        self.cb_start_with_windows.setChecked(self.config.get("start_with_windows", True))

        # Preset Mode
        preset = self.config.get("mode_preset", "clean_dictation")

        vocab = self.config.get("custom_vocabulary", [])
        self.vocab_input.setText(", ".join(vocab))

        # Audio Device & DSP / Offline Options
        dev_idx = self.config.get("input_device_index")
        if dev_idx is not None:
            for i in range(self.mic_combo.count()):
                if self.mic_combo.itemData(i) == dev_idx:
                    self.mic_combo.setCurrentIndex(i)
                    break

        if hasattr(self, 'cb_dsp_fan_filter') and self.cb_dsp_fan_filter:
            self.cb_dsp_fan_filter.setChecked(self.config.get("dsp_fan_filter_enabled", True))
        if hasattr(self, 'cb_dsp_noise_gate') and self.cb_dsp_noise_gate:
            self.cb_dsp_noise_gate.setChecked(self.config.get("dsp_noise_gate_enabled", True))
        if hasattr(self, 'cb_offline_fallback') and self.cb_offline_fallback:
            self.cb_offline_fallback.setChecked(self.config.get("offline_fallback_enabled", True))

        # Auto Cost Mode
        if hasattr(self, 'cb_auto_cost_mode') and self.cb_auto_cost_mode:
            auto_cost = self.config.get("auto_cost_mode", True)
            self.cb_auto_cost_mode.setChecked(auto_cost)
            self._on_auto_cost_toggled(auto_cost)

        self._refresh_saved_prompts()
        self._refresh_dictionary()
        self._refresh_snippets()
        self._refresh_vocab_table()
        self._on_vocab_test_changed(self.vocab_test_input.text())
        self._refresh_history()
        self._refresh_cost_stats()

    # --- Custom Prompts Library Management ---
    def _refresh_saved_prompts(self, select_id: Optional[str] = None):
        if not hasattr(self, 'saved_prompts_combo'):
            return
        self.saved_prompts_combo.blockSignals(True)
        self.saved_prompts_combo.clear()
        prompts = self.config.get_saved_prompts()
        target_idx = 0
        for idx, p in enumerate(prompts):
            p_id = p.get("id", "")
            title = p.get("title", "Custom Prompt")
            is_act = p.get("is_active", False)
            disp = f"{'📌 ' if is_act else ''}{title}{' (Active)' if is_act else ''}"
            self.saved_prompts_combo.addItem(disp, p_id)
            if select_id and p_id == select_id:
                target_idx = idx
            elif not select_id and is_act:
                target_idx = idx

        if self.saved_prompts_combo.count() > 0:
            self.saved_prompts_combo.setCurrentIndex(target_idx)
        self.saved_prompts_combo.blockSignals(False)
        self._on_saved_prompt_selected()

    def _on_saved_prompt_selected(self, index: int = -1):
        if not hasattr(self, 'saved_prompts_combo'):
            return
        p_id = self.saved_prompts_combo.currentData()
        if not p_id:
            return
        self._editing_prompt_id = p_id
        prompts = self.config.get_saved_prompts()
        matched = next((p for p in prompts if p.get("id") == p_id), None)
        if matched:
            self.prompt_title_input.setText(matched.get("title", ""))
            self.custom_prompt_edit.setPlainText(matched.get("prompt", ""))
            self._original_editing_title = matched.get("title", "")

            # Map prompt id to preset mode
            id_to_preset = {
                "clean_dictation_custom": "clean_dictation",
                "smart_polish_custom": "smart_polish",
                "code_dev_custom": "code_assistant"
            }
            matched_preset = id_to_preset.get(p_id, "clean_dictation")
            
            # Activate immediately on selection
            self.config.set_active_saved_prompt(p_id)
            self.config.set("mode_preset", matched_preset)
            self.config.save_config()

            self.active_prompt_badge.setText(f"Active: {matched.get('title')}")
            self.active_prompt_badge.setStyleSheet("color: #10B981; font-weight: bold; font-size: 11px; background: #064E3B; border-radius: 4px; padding: 3px 8px; border: none;")
            self.btn_apply_prompt.setEnabled(False)
            self.btn_apply_prompt.setText("✓ Currently Active")
            self.btn_delete_prompt.setEnabled(len(prompts) > 1)
            self.settings_applied.emit()

    def _on_new_saved_prompt(self):
        self._editing_prompt_id = None
        self._original_editing_title = ""
        self.saved_prompts_combo.blockSignals(True)
        self.saved_prompts_combo.setCurrentIndex(-1)
        self.saved_prompts_combo.blockSignals(False)
        self.prompt_title_input.clear()
        self.prompt_title_input.setPlaceholderText("Enter a memorable prompt title...")
        self.custom_prompt_edit.clear()
        self.prompt_title_input.setFocus()
        self.active_prompt_badge.setText("Status: Drafting New Prompt")
        self.active_prompt_badge.setStyleSheet("color: #F59E0B; font-weight: bold; font-size: 11px; background: #78350F; border-radius: 4px; padding: 3px 8px; border: none;")
        self.btn_apply_prompt.setEnabled(False)
        self.btn_apply_prompt.setText("⚡ Set as Active Prompt")
        self.prompt_status_label.setText("💡 Enter a title and system prompt instructions, then click 'Save / Update Prompt'.")
        self.prompt_status_label.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600; border: none;")

    def _on_save_custom_prompt(self):
        title = self.prompt_title_input.text().strip()
        prompt_text = self.custom_prompt_edit.toPlainText().strip()
        if not title:
            QMessageBox.warning(self, "Missing Title", "Please give your custom prompt a title.")
            return
        if not prompt_text:
            QMessageBox.warning(self, "Missing Instructions", "Please enter the system prompt instructions.")
            return

        target_id = getattr(self, '_editing_prompt_id', None)
        saved_id = self.config.save_custom_prompt(title, prompt_text, prompt_id=target_id, set_active=True)
        self._editing_prompt_id = saved_id
        self._original_editing_title = title
        self._refresh_saved_prompts(select_id=saved_id)
        self.prompt_status_label.setText(f"✓ Saved '{title}' successfully and set as active!")
        self.prompt_status_label.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px; border: none;")
        self.settings_applied.emit()
        QTimer.singleShot(3000, lambda: self.prompt_status_label.setText(""))

    def _on_delete_saved_prompt(self):
        curr_id = self.saved_prompts_combo.currentData()
        if not curr_id:
            return
        title = self.prompt_title_input.text().strip()
        res = QMessageBox.question(
            self,
            "Delete Prompt",
            f"Are you sure you want to delete '{title}' from your saved prompts library?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self.config.delete_saved_prompt(curr_id)
            self._refresh_saved_prompts()
            self.prompt_status_label.setText(f"🗑️ Deleted '{title}'.")
            self.prompt_status_label.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600; border: none;")
            self.settings_applied.emit()
            QTimer.singleShot(3000, lambda: self.prompt_status_label.setText(""))

    def _on_activate_saved_prompt(self):
        curr_id = self.saved_prompts_combo.currentData()
        if not curr_id:
            return
        title = self.prompt_title_input.text().strip()
        self.config.set_active_saved_prompt(curr_id)
        self._refresh_saved_prompts(select_id=curr_id)
        self.prompt_status_label.setText(f"✓ '{title}' is now your active dictation system prompt!")
        self.prompt_status_label.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px; border: none;")
        self.settings_applied.emit()
    def _on_general_model_combo_changed(self, index: int):
        if hasattr(self, 'router_model_combo') and self.router_model_combo.currentIndex() != index:
            self.router_model_combo.blockSignals(True)
            self.router_model_combo.setCurrentIndex(index)
            self.router_model_combo.blockSignals(False)

    def _on_router_model_combo_changed(self, index: int):
        if hasattr(self, 'model_combo') and self.model_combo.currentIndex() != index:
            self.model_combo.blockSignals(True)
            self.model_combo.setCurrentIndex(index)
            self.model_combo.blockSignals(False)

    def notify_history_changed(self):
        """Called live by main coordinator when new transcription or prompt finishes."""
        self._refresh_history()
        self._refresh_cost_stats()

    def _poll_live_updates(self):
        """Polls for background file changes every 2.5s to update UI automatically without restart."""
        from ..config import HISTORY_FILE, CONFIG_FILE
        try:
            # Check history file
            if HISTORY_FILE.exists():
                mtime = HISTORY_FILE.stat().st_mtime
                if mtime != self._last_history_mtime:
                    self._last_history_mtime = mtime
                    curr_history = self.config.get_history()
                    top_id = curr_history[0].get('id') if curr_history else ""
                    if len(curr_history) != self._last_history_len or top_id != self._last_top_id:
                        self._last_history_len = len(curr_history)
                        self._last_top_id = top_id
                        self._refresh_history()
                        self._refresh_cost_stats()

            # Check config file (only sync if user is not actively typing in inputs)
            if CONFIG_FILE.exists():
                c_mtime = CONFIG_FILE.stat().st_mtime
                if self._last_config_mtime == 0.0:
                    self._last_config_mtime = c_mtime
                elif c_mtime > self._last_config_mtime + 1.0:
                    self._last_config_mtime = c_mtime
                    focused = QApplication.focusWidget()
                    if focused not in (self.custom_prompt_edit, self.prompt_title_input, self.vocab_input, self.api_key_input):
                        self.config.load_config()
                        self._refresh_saved_prompts()
                        self._refresh_dictionary()
                        self._refresh_snippets()
                        self._refresh_vocab_table()
        except Exception as e:
            logger.debug(f"Live poll note: {e}")

    # --- Dictionary Management ---
    def _on_dict_row_selected(self, item=None):
        row = self.dict_table.currentRow()
        if row >= 0:
            spoken_item = self.dict_table.item(row, 0)
            rep_item = self.dict_table.item(row, 1)
            spoken = spoken_item.text() if spoken_item else ""
            rep = rep_item.text() if rep_item else ""
            self.dict_selection_info.setText(f"Selected: \"{spoken}\"  ➔  \"{rep}\"")
            self.btn_edit_dict.setEnabled(True)
            self.btn_delete_dict.setEnabled(True)
        else:
            self.dict_selection_info.setText("")
            self.btn_edit_dict.setEnabled(False)
            self.btn_delete_dict.setEnabled(False)

    def _refresh_dictionary(self):
        self.dict_table.setRowCount(0)
        dictionary = self.config.get_dictionary()
        item_font = QFont("Segoe UI", 11)
        item_font.setWeight(QFont.Weight.DemiBold)

        for row, entry in enumerate(dictionary):
            self.dict_table.insertRow(row)
            self.dict_table.setRowHeight(row, 46)
            item_spoken = QTableWidgetItem(entry.get("spoken", ""))
            item_spoken.setFont(item_font)
            item_spoken.setForeground(QColor("#FFFFFF"))
            item_spoken.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            item_rep = QTableWidgetItem(entry.get("replacement", ""))
            item_rep.setFont(item_font)
            item_rep.setForeground(QColor("#FFFFFF"))
            item_rep.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.dict_table.setItem(row, 0, item_spoken)
            self.dict_table.setItem(row, 1, item_rep)

        if self.dict_table.rowCount() > 0:
            self.dict_table.setCurrentCell(0, 0)
            self._on_dict_row_selected()
        else:
            self._on_dict_row_selected()

    def _filter_dictionary(self, query: str):
        query = query.lower()
        for row in range(self.dict_table.rowCount()):
            spoken = (self.dict_table.item(row, 0).text() if self.dict_table.item(row, 0) else "").lower()
            rep = (self.dict_table.item(row, 1).text() if self.dict_table.item(row, 1) else "").lower()
            self.dict_table.setRowHidden(row, query not in spoken and query not in rep)

    def _add_dict_entry(self):
        dlg = DictEditDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            dictionary = self.config.get_dictionary()
            dictionary.append(data)
            self.config.set_dictionary(dictionary)
            self._refresh_dictionary()

    def _edit_dict_entry(self):
        row = self.dict_table.currentRow()
        if row < 0:
            return
        dictionary = self.config.get_dictionary()
        if row >= len(dictionary):
            return
        entry = dictionary[row]
        dlg = DictEditDialog(spoken=entry.get("spoken", ""), replacement=entry.get("replacement", ""), parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dictionary[row] = dlg.get_data()
            self.config.set_dictionary(dictionary)
            self._refresh_dictionary()

    def _delete_dict_entry(self):
        row = self.dict_table.currentRow()
        if row < 0:
            return
        dictionary = self.config.get_dictionary()
        if row < len(dictionary):
            dictionary.pop(row)
            self.config.set_dictionary(dictionary)
            self._refresh_dictionary()

    # --- Quick Text (Snippets) Management ---
    def _refresh_snippets(self):
        self.snippet_table.setRowCount(0)
        snippets = self.config.get_snippets()
        item_font = QFont("Segoe UI", 10)
        item_font.setWeight(QFont.Weight.DemiBold)
        for row, snip in enumerate(snippets):
            self.snippet_table.insertRow(row)
            self.snippet_table.setRowHeight(row, 46)
            item_trig = QTableWidgetItem(snip.get("trigger", ""))
            item_trig.setFont(item_font)
            item_trig.setForeground(QColor("#FFFFFF"))
            item_trig.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            content_preview = snip.get("content", "").replace("\n", "  ↵  ")
            item_content = QTableWidgetItem(content_preview)
            item_content.setFont(item_font)
            item_content.setForeground(QColor("#FFFFFF"))
            item_content.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.snippet_table.setItem(row, 0, item_trig)
            self.snippet_table.setItem(row, 1, item_content)

    def _filter_snippets(self, query: str):
        query = query.lower()
        for row in range(self.snippet_table.rowCount()):
            trigger = (self.snippet_table.item(row, 0).text() if self.snippet_table.item(row, 0) else "").lower()
            content = (self.snippet_table.item(row, 1).text() if self.snippet_table.item(row, 1) else "").lower()
            self.snippet_table.setRowHidden(row, query not in trigger and query not in content)

    def _add_snippet_entry(self):
        dlg = SnippetEditDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            snippets = self.config.get_snippets()
            snippets.append(data)
            self.config.set_snippets(snippets)
            self._refresh_snippets()

    def _edit_snippet_entry(self):
        row = self.snippet_table.currentRow()
        if row < 0:
            return
        snippets = self.config.get_snippets()
        if row >= len(snippets):
            return
        entry = snippets[row]
        dlg = SnippetEditDialog(trigger=entry.get("trigger", ""), content=entry.get("content", ""), parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            snippets[row] = dlg.get_data()
            self.config.set_snippets(snippets)
            self._refresh_snippets()

    def _delete_snippet_entry(self):
        row = self.snippet_table.currentRow()
        if row < 0:
            return
        snippets = self.config.get_snippets()
        if row < len(snippets):
            snippets.pop(row)
            self.config.set_snippets(snippets)
            self._refresh_snippets()

    # --- History Management & Hierarchical Filtering ---
    def _on_search_text_changed(self, text: str):
        self._history_search_query = text.strip().lower()
        self._refresh_history()

    def _toggle_favorite_filter(self):
        self._history_filter_favorites = self.btn_filter_favorites.isChecked()
        if self._history_filter_favorites:
            self.btn_filter_favorites.setText("⭐ Favorites (Active)")
            self.btn_filter_favorites.setStyleSheet("background-color: #D97706; color: white; font-weight: bold; border: 1px solid #F59E0B;")
        else:
            self.btn_filter_favorites.setText("⭐ Favorites")
            self.btn_filter_favorites.setStyleSheet("")
        self._update_filter_tag_bar()
        self._refresh_history()

    def _show_filter_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(DARK_STYLE)

        act_all = menu.addAction("🔄 All Transcripts (Reset Filters)")
        act_all.triggered.connect(self._reset_all_filters)
        menu.addSeparator()

        # 1. Filter by Date Submenu
        date_menu = menu.addMenu("📅 Filter by Date")
        date_menu.addAction("Today", lambda: self._set_filter("date", "today", "Date: Today"))
        date_menu.addAction("Yesterday", lambda: self._set_filter("date", "yesterday", "Date: Yesterday"))
        date_menu.addAction("Past 7 Days (Within Week)", lambda: self._set_filter("date", "week", "Date: Past 7 Days"))
        date_menu.addAction("Past 30 Days (Within Month)", lambda: self._set_filter("date", "month", "Date: Past 30 Days"))
        date_menu.addSeparator()
        date_menu.addAction("Pick Calendar Date...", self._pick_custom_date_filter)

        # 2. Filter by Model Submenu
        model_menu = menu.addMenu("🤖 Filter by Model")
        for m in [
            "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest",
            "gemini-3.7-flash", "gemini-2.5-flash", "gemini-2.5-pro"
        ]:
            model_menu.addAction(m, lambda checked=False, val=m: self._set_filter("model", val, f"Model: {val}"))

        # 3. Filter by Application Submenu
        app_menu = menu.addMenu("💻 Filter by Application")
        apps_found = set(["Antigravity", "VS Code", "Windsurf", "Cursor", "Cline AI", "ChatGPT", "Claude AI", "WhatsApp", "Google Chrome", "Microsoft Edge", "Terminal", "Notepad", "General"])
        for h in self.config.get_history():
            app = h.get("app_name")
            if app:
                apps_found.add(app)
        for app_name in sorted(apps_found):
            app_menu.addAction(app_name, lambda checked=False, val=app_name: self._set_filter("app", val, f"App: {val}"))

        # 4. Filter by Transformation Submenu
        trans_menu = menu.addMenu("⚡ Filter by Mode / Transformation")
        trans_map = [
            ("✨ AI Prompt (with Speech Safeguard)", "prompt_generation"),
            ("🗣️ Clean Voice Dictation", "clean_dictation"),
            ("✨ AI Prompt Enhancer (Ctrl+Shift+P)", "prompt_enhancer"),
            ("Smart Polish", "smart_polish"),
            ("Code Assistant", "code_assistant"),
            ("Verbatim", "verbatim"),
        ]
        for label, val in trans_map:
            trans_menu.addAction(label, lambda checked=False, v=val, lbl=label: self._set_filter("transformation", v, f"Mode: {lbl}"))

        menu.exec(self.btn_filter_by.mapToGlobal(self.btn_filter_by.rect().bottomLeft()))

    def _set_filter(self, category: str, value: Any, label: str):
        self._history_filter_category = category
        self._history_filter_value = value
        self._update_filter_tag_bar(label)
        self._refresh_history()

    def _pick_custom_date_filter(self):
        dlg = CalendarFilterDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            date_str = dlg.get_selected_date_str()
            self._set_filter("date", f"date:{date_str}", f"Date: {date_str}")

    def _reset_all_filters(self):
        self._history_search_query = ""
        self.history_search.clear()
        self._history_filter_favorites = False
        self.btn_filter_favorites.setChecked(False)
        self.btn_filter_favorites.setText("⭐ Favorites")
        self.btn_filter_favorites.setStyleSheet("")
        self._history_filter_category = None
        self._history_filter_value = None
        self.filter_tag_bar.setVisible(False)
        self._refresh_history()

    def _update_filter_tag_bar(self, extra_label: str = ""):
        parts = []
        if self._history_filter_favorites:
            parts.append("⭐ Favorites Only")
        if self._history_filter_category and self._history_filter_value:
            parts.append(extra_label or f"{self._history_filter_category}: {self._history_filter_value}")
        if self._history_search_query:
            parts.append(f"Query: \"{self._history_search_query}\"")

        if parts:
            self.filter_tag_label.setText("Active Filter: " + " | ".join(parts))
            self.filter_tag_bar.setVisible(True)
        else:
            self.filter_tag_bar.setVisible(False)

    def _filter_matches_entry(self, entry: Dict[str, Any]) -> bool:
        # Search query matching both prompt text and raw spoken text
        if self._history_search_query:
            q = self._history_search_query.lower()
            text = entry.get("text", "").lower()
            raw_text = entry.get("raw_text", "").lower()
            prompt = entry.get("prompt", "").lower()
            title = entry.get("title", "").lower()
            app = entry.get("app_name", "").lower()
            model = entry.get("model", "").lower()
            if q not in text and q not in raw_text and q not in prompt and q not in title and q not in app and q not in model:
                return False

        # Favorites
        if self._history_filter_favorites and not entry.get("is_favorite", False):
            return False

        # Category filters
        cat = self._history_filter_category
        val = self._history_filter_value
        if cat and val:
            if cat == "model":
                if entry.get("model") != val:
                    return False
            elif cat == "app":
                if entry.get("app_name") != val:
                    return False
            elif cat == "transformation":
                mode = entry.get("mode", "")
                raw_t = entry.get("raw_text", "")
                txt_t = entry.get("text", "")
                is_prompt = (mode in ("prompt_generation", "prompt_enhancer") or bool(entry.get("prompt")) or (bool(raw_t) and raw_t.strip() != txt_t.strip()))
                if val == "prompt_generation":
                    if not is_prompt:
                        return False
                elif val == "clean_dictation":
                    if is_prompt and mode != "clean_dictation":
                        return False
                elif mode != val:
                    return False
            elif cat == "date":
                import datetime
                try:
                    ts = entry.get("timestamp", "")
                    entry_dt = datetime.datetime.fromisoformat(ts).date()
                    today = datetime.date.today()
                    delta = (today - entry_dt).days
                    if val == "today" and delta != 0:
                        return False
                    elif val == "yesterday" and delta != 1:
                        return False
                    elif val == "week" and delta > 7:
                        return False
                    elif val == "month" and delta > 30:
                        return False
                    elif str(val).startswith("date:"):
                        target_d = str(val).split("date:")[1]
                        if entry_dt.strftime("%Y-%m-%d") != target_d:
                            return False
                except Exception:
                    pass

        return True

    def _refresh_history(self):
        self.history_tree.clear()
        history = self.config.get_history()

        filtered_entries = [e for e in history if self._filter_matches_entry(e)]

        import datetime
        today = datetime.date.today()

        pinned_entries = []
        buckets = {
            "Today": [],
            "Yesterday": [],
            "Earlier this Week": [],
            "Earlier this Month": [],
            "Older": []
        }

        for entry in filtered_entries:
            if entry.get("is_pinned", False):
                pinned_entries.append(entry)

            try:
                ts = entry.get("timestamp", "")
                entry_dt = datetime.datetime.fromisoformat(ts).date()
                delta = (today - entry_dt).days
                if delta == 0:
                    buckets["Today"].append(entry)
                elif delta == 1:
                    buckets["Yesterday"].append(entry)
                elif delta < 7:
                    buckets["Earlier this Week"].append(entry)
                elif delta < 30:
                    buckets["Earlier this Month"].append(entry)
                else:
                    buckets["Older"].append(entry)
            except Exception:
                buckets["Older"].append(entry)

        # 1. Pinned Group (at top if any pinned entries match filter)
        if pinned_entries:
            pinned_root = QTreeWidgetItem(self.history_tree)
            pinned_root.setText(0, f"📌 Pinned Transcripts ({len(pinned_entries)})")
            pinned_root.setForeground(0, QColor("#F59E0B"))
            pinned_font = pinned_root.font(0)
            pinned_font.setBold(True)
            pinned_root.setFont(0, pinned_font)
            pinned_root.setExpanded(True)
            for entry in pinned_entries:
                self._add_tree_item(pinned_root, entry)

        # 2. Date Groups
        icons = {
            "Today": "📅 Today",
            "Yesterday": "📅 Yesterday",
            "Earlier this Week": "🗓️ Earlier this Week",
            "Earlier this Month": "🗓️ Earlier this Month",
            "Older": "📁 Older Transcripts"
        }
        for b_name, b_list in buckets.items():
            if not b_list:
                continue
            b_root = QTreeWidgetItem(self.history_tree)
            b_root.setText(0, f"{icons.get(b_name, b_name)} ({len(b_list)})")
            b_root.setForeground(0, QColor("#38BDF8"))
            b_font = b_root.font(0)
            b_font.setBold(True)
            b_root.setFont(0, b_font)
            if b_name in ("Today", "Yesterday", "Earlier this Week"):
                b_root.setExpanded(True)
            else:
                b_root.setExpanded(False)

            for entry in b_list:
                self._add_tree_item(b_root, entry)

        self._restore_tree_selection()

    def _add_tree_item(self, parent_node: QTreeWidgetItem, entry: Dict[str, Any]):
        item = QTreeWidgetItem(parent_node)
        pin_mark = "📌 " if entry.get("is_pinned") else ""
        fav_mark = "⭐ " if entry.get("is_favorite") else ""
        custom_title = entry.get("title", "").strip()
        text = entry.get("text", "").strip()
        raw_text = entry.get("raw_text", "").strip()
        mode = entry.get("mode", "")

        is_prompt = (mode in ("prompt_generation", "prompt_enhancer") or (raw_text and raw_text != text) or bool(entry.get("prompt")))

        if is_prompt and raw_text and raw_text != text:
            # Multi-line preview showing both AI Prompt and Spoken Dictation
            prompt_preview = format_history_preview(text, max_chars=140, max_lines=2)
            raw_preview = format_history_preview(raw_text, max_chars=100, max_lines=1)
            if custom_title:
                col0_text = f"{pin_mark}{fav_mark}✨ {custom_title} — [Prompt: \"{prompt_preview}\" | 🗣️ Spoken: \"{raw_preview}\"]"
            else:
                col0_text = f"{pin_mark}{fav_mark}✨ Prompt: \"{prompt_preview}\"\n   🗣️ Spoken: \"{raw_preview}\""
        else:
            max_chars = max(120, 240 - len(custom_title)) if custom_title else 240
            text_preview = format_history_preview(text or raw_text, max_chars=max_chars, max_lines=3)
            if custom_title and text_preview:
                col0_text = f"{pin_mark}{fav_mark}{custom_title} — \"{text_preview}\""
            elif custom_title:
                col0_text = f"{pin_mark}{fav_mark}{custom_title}"
            elif text_preview:
                col0_text = f"{pin_mark}{fav_mark}\"{text_preview}\""
            else:
                col0_text = f"{pin_mark}{fav_mark}(Empty transcription)"

        item.setText(0, col0_text)

        # Column 1: Application
        app_name = entry.get("app_name", "General")
        app_icons = {
            "Antigravity": "🚀",
            "VS Code": "💻",
            "Cursor": "⚡",
            "Windsurf": "🏄",
            "Cline AI": "🤖",
            "Continue AI": "⏩",
            "Zed": "⚡",
            "ChatGPT": "🤖",
            "Claude AI": "🧠",
            "Perplexity": "🔍",
            "Google Chrome": "🌐",
            "Microsoft Edge": "🌐",
            "Firefox": "🌐",
            "WhatsApp": "💬",
            "Telegram": "💬",
            "Slack": "💬",
            "Discord": "💬",
            "Notepad": "📝",
            "Microsoft Word": "📄",
            "Terminal": "⚡",
            "General": "🖥️"
        }
        app_icon = app_icons.get(app_name, "💻" if "code" in app_name.lower() else "📱")
        item.setText(1, f"{app_icon} {app_name}")
        item.setForeground(1, QColor("#94A3B8"))

        # Column 2: Model
        model_name = entry.get("model", "gemini-3.5-flash-lite")
        short_model = model_name.replace("gemini-", "")
        item.setText(2, f"🤖 {short_model}")
        item.setForeground(2, QColor("#64748B"))

        # Column 3: Time
        time_str = entry.get("time_str", "")
        if " " in time_str:
            time_only = time_str.split(" ", 1)[1]
        else:
            time_only = time_str
        item.setText(3, f"🕒 {time_only}")
        item.setForeground(3, QColor("#64748B"))

        item.setData(0, Qt.ItemDataRole.UserRole, entry)

    def _restore_tree_selection(self):
        if self._selected_entry_id:
            root = self.history_tree.invisibleRootItem()
            for i in range(root.childCount()):
                cat_node = root.child(i)
                for j in range(cat_node.childCount()):
                    leaf = cat_node.child(j)
                    entry = leaf.data(0, Qt.ItemDataRole.UserRole)
                    if entry and entry.get("id") == self._selected_entry_id:
                        self.history_tree.setCurrentItem(leaf)
                        return

        root = self.history_tree.invisibleRootItem()
        if root.childCount() > 0:
            first_cat = root.child(0)
            if first_cat.childCount() > 0:
                self.history_tree.setCurrentItem(first_cat.child(0))
            else:
                self._set_detail_empty()
        else:
            self._set_detail_empty()

    def _on_history_tree_selection_changed(self):
        items = self.history_tree.selectedItems()
        if not items:
            self._set_detail_empty()
            return
        item = items[0]
        entry = item.data(0, Qt.ItemDataRole.UserRole)
        if not entry:
            self._set_detail_empty()
            return

        self._selected_entry_id = entry.get("id")
        text = entry.get("text", "")
        raw_text = entry.get("raw_text", "")
        prompt = entry.get("prompt", "")
        words = len(text.split())
        chars = len(text)
        title = entry.get("title", "")
        duration = entry.get("duration", 0)
        app_name = entry.get("app_name", "General")
        model = entry.get("model", "gemini-3.5-flash-lite")
        mode = entry.get("mode", "")
        is_pinned = entry.get("is_pinned", False)
        is_fav = entry.get("is_favorite", False)

        is_prompt_entry = (mode in ("prompt_generation", "prompt_enhancer") or bool(prompt) or (raw_text and raw_text.strip() != text.strip()))

        if is_prompt_entry:
            header_str = f"✨ AI Prompt ({words} words, {chars} chars, ⏱️ {duration}s)"
            if title:
                header_str = f"✨ {title} — AI Prompt ({words} words, {chars} chars, ⏱️ {duration}s)"
            self.history_detail_title.setText(header_str)
            self.history_detail_tabs.setTabText(0, "✨ Converted AI Prompt")
            self.history_detail_tabs.setTabText(1, "🗣️ Normal Spoken Speech (Safeguard Backup)")
            self.history_detail_tabs.setTabVisible(1, True)

            self.btn_copy_selected.setText("✨ Copy AI Prompt")
            self.btn_copy_raw_selected.setVisible(True)
            self.btn_copy_raw_selected.setEnabled(bool(raw_text))
            self.btn_copy_raw_selected.setText("🗣️ Copy Normal Speech")

            self.btn_reinsert_selected.setText("🚀 Paste AI Prompt")
            self.btn_reinsert_raw_selected.setVisible(True)
            self.btn_reinsert_raw_selected.setEnabled(bool(raw_text))

            self.history_badge_safeguard.setText("🛡️ Speech Safeguard on Clipboard")
            self.history_badge_safeguard.setVisible(True)
        else:
            header_str = f"📄 {title if title else 'Full Transcription'} ({words} words, {chars} chars, ⏱️ {duration}s)"
            self.history_detail_title.setText(header_str)
            self.history_detail_tabs.setTabText(0, "📄 Full Transcription")
            self.history_detail_tabs.setTabVisible(1, False)

            self.btn_copy_selected.setText("📋 Copy Text")
            self.btn_copy_raw_selected.setVisible(False)
            self.btn_copy_raw_selected.setEnabled(False)

            self.btn_reinsert_selected.setText("🚀 Reinsert (Paste)")
            self.btn_reinsert_raw_selected.setVisible(False)
            self.btn_reinsert_raw_selected.setEnabled(False)

            self.history_badge_safeguard.setVisible(False)

        self.history_badge_app.setText(f"App: {app_name}")
        self.history_badge_model.setText(f"Model: {model}")
        self.history_detail_text.setPlainText(text)
        self.history_raw_detail_text.setPlainText(raw_text or text)

        self.btn_pin_selected.setEnabled(True)
        self.btn_pin_selected.setText("📍 Unpin" if is_pinned else "📌 Pin")
        self.btn_fav_selected.setEnabled(True)
        self.btn_fav_selected.setText("★ Favorited" if is_fav else "⭐ Favorite")
        self.btn_rename_selected.setEnabled(True)
        self.btn_copy_selected.setEnabled(bool(text))
        self.btn_reinsert_selected.setEnabled(bool(text))
        self.btn_delete_selected.setEnabled(True)

    def _set_detail_empty(self):
        self._selected_entry_id = None
        self.history_detail_title.setText("📄 Full Transcription Details (No selection)")
        self.history_badge_app.setText("")
        self.history_badge_model.setText("")
        self.history_badge_safeguard.setVisible(False)
        self.history_detail_text.clear()
        self.history_raw_detail_text.clear()
        self.history_detail_tabs.setTabText(0, "✨ Converted AI Prompt")
        self.history_detail_tabs.setTabVisible(1, True)
        self.btn_pin_selected.setEnabled(False)
        self.btn_pin_selected.setText("📌 Pin")
        self.btn_fav_selected.setEnabled(False)
        self.btn_fav_selected.setText("⭐ Favorite")
        self.btn_rename_selected.setEnabled(False)
        self.btn_copy_selected.setText("📋 Copy Text")
        self.btn_copy_selected.setEnabled(False)
        self.btn_copy_raw_selected.setVisible(False)
        self.btn_copy_raw_selected.setEnabled(False)
        self.btn_reinsert_selected.setEnabled(False)
        self.btn_reinsert_raw_selected.setVisible(False)
        self.btn_reinsert_raw_selected.setEnabled(False)
        self.btn_delete_selected.setEnabled(False)

    def _get_selected_history_entry(self) -> Optional[Dict[str, Any]]:
        items = self.history_tree.selectedItems()
        if items:
            return items[0].data(0, Qt.ItemDataRole.UserRole)
        return None

    def _show_history_context_menu(self, pos):
        item = self.history_tree.itemAt(pos)
        if not item:
            return
        entry = item.data(0, Qt.ItemDataRole.UserRole)
        if not entry:
            return

        self.history_tree.setCurrentItem(item)
        is_pinned = entry.get("is_pinned", False)
        is_fav = entry.get("is_favorite", False)

        menu = QMenu(self)
        menu.setStyleSheet(DARK_STYLE)

        act_pin = menu.addAction("📍 Unpin Transcript" if is_pinned else "📌 Pin Transcript")
        act_pin.triggered.connect(self._toggle_pin_selected)

        act_fav = menu.addAction("★ Remove from Favorites" if is_fav else "⭐ Mark as Favorite")
        act_fav.triggered.connect(self._toggle_fav_selected)

        act_rename = menu.addAction("✏️ Rename Title...")
        act_rename.triggered.connect(self._rename_selected_history)

        menu.addSeparator()

        is_prompt = (entry.get("mode") in ("prompt_generation", "prompt_enhancer") or (entry.get("raw_text") and entry.get("raw_text").strip() != entry.get("text", "").strip()))
        act_copy = menu.addAction("✨ Copy AI Prompt" if is_prompt else "📋 Copy Text")
        act_copy.triggered.connect(self._copy_selected_history)

        if entry.get("raw_text") and entry.get("raw_text").strip() != entry.get("text", "").strip():
            act_copy_raw = menu.addAction("🗣️ Copy Normal Spoken Text (Safeguard Backup)")
            act_copy_raw.triggered.connect(self._copy_raw_selected_history)

        act_reinsert = menu.addAction("🚀 Paste AI Prompt to Cursor" if is_prompt else "🚀 Reinsert (Paste to Cursor)")
        act_reinsert.triggered.connect(self._reinsert_selected_history)

        if entry.get("raw_text") and entry.get("raw_text").strip() != entry.get("text", "").strip():
            act_reinsert_raw = menu.addAction("🗣️ Paste Normal Spoken Speech to Cursor")
            act_reinsert_raw.triggered.connect(self._reinsert_raw_selected_history)

        menu.addSeparator()

        act_delete = menu.addAction("🗑️ Delete This Transcript")
        act_delete.triggered.connect(self._delete_selected_history)

        menu.exec(self.history_tree.mapToGlobal(pos))

    def _toggle_pin_selected(self):
        entry = self._get_selected_history_entry()
        if not entry:
            return
        entry_id = entry.get("id")
        new_pinned = not entry.get("is_pinned", False)
        self.config.update_history_entry(entry_id, {"is_pinned": new_pinned})
        self._refresh_history()

    def _toggle_fav_selected(self):
        entry = self._get_selected_history_entry()
        if not entry:
            return
        entry_id = entry.get("id")
        new_fav = not entry.get("is_favorite", False)
        self.config.update_history_entry(entry_id, {"is_favorite": new_fav})
        self._refresh_history()

    def _rename_selected_history(self):
        entry = self._get_selected_history_entry()
        if not entry:
            return
        entry_id = entry.get("id")
        current_title = entry.get("title", "")
        text = entry.get("text", "")
        dlg = RenameTranscriptDialog(current_title, text, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_title = dlg.get_title()
            self.config.update_history_entry(entry_id, {"title": new_title})
            self._refresh_history()

    def _copy_selected_history(self):
        entry = self._get_selected_history_entry()
        if not entry:
            return
        text = entry.get("text", "")
        if text:
            import pyperclip
            pyperclip.copy(text)
            is_prompt = (entry.get("mode") in ("prompt_generation", "prompt_enhancer") or (entry.get("raw_text") and entry.get("raw_text").strip() != text.strip()))
            default_text = "✨ Copy AI Prompt" if is_prompt else "📋 Copy Text"
            self.btn_copy_selected.setText("✓ Copied!")
            self.btn_copy_selected.setStyleSheet("background-color: #10B981; color: white;")
            QTimer.singleShot(1400, lambda: [
                self.btn_copy_selected.setText(default_text),
                self.btn_copy_selected.setStyleSheet("")
            ])

    def _copy_raw_selected_history(self):
        entry = self._get_selected_history_entry()
        if not entry:
            return
        raw_text = entry.get("raw_text", "") or entry.get("text", "")
        if raw_text:
            import pyperclip
            pyperclip.copy(raw_text)
            self.btn_copy_raw_selected.setText("✓ Normal Speech Copied!")
            self.btn_copy_raw_selected.setStyleSheet("background-color: #10B981; color: white;")
            QTimer.singleShot(1400, lambda: [
                self.btn_copy_raw_selected.setText("🗣️ Copy Normal Speech"),
                self.btn_copy_raw_selected.setStyleSheet("background-color: #1E293B; color: #38BDF8; border: 1px solid #0284C7;")
            ])

    def _reinsert_selected_history(self):
        entry = self._get_selected_history_entry()
        if not entry:
            return
        text = entry.get("text", "")
        if not text:
            return

        self.btn_reinsert_selected.setText("🚀 Pasting...")
        QApplication.processEvents()

        self.showMinimized()
        time.sleep(0.2)

        paste_ok = self.text_injector.paste_text(text)
        if not paste_ok:
            import pyperclip
            pyperclip.copy(text)

        is_prompt = (entry.get("mode") in ("prompt_generation", "prompt_enhancer") or (entry.get("raw_text") and entry.get("raw_text").strip() != text.strip()))
        default_lbl = "🚀 Paste AI Prompt" if is_prompt else "🚀 Reinsert (Paste)"
        QTimer.singleShot(1500, lambda: self.btn_reinsert_selected.setText(default_lbl))

    def _reinsert_raw_selected_history(self):
        entry = self._get_selected_history_entry()
        if not entry:
            return
        raw_text = entry.get("raw_text", "") or entry.get("text", "")
        if not raw_text:
            return

        self.btn_reinsert_raw_selected.setText("🚀 Pasting Speech...")
        QApplication.processEvents()

        self.showMinimized()
        time.sleep(0.2)

        paste_ok = self.text_injector.paste_text(raw_text)
        if not paste_ok:
            import pyperclip
            pyperclip.copy(raw_text)

        QTimer.singleShot(1500, lambda: self.btn_reinsert_raw_selected.setText("🗣️ Paste Normal Speech"))

    def _delete_selected_history(self):
        entry = self._get_selected_history_entry()
        if not entry:
            return
        entry_id = entry.get("id")
        preview = entry.get("text", "")[:50]
        reply = QMessageBox.question(
            self,
            "Delete Transcript",
            f"Are you sure you want to delete this specific transcript?\n\n\"{preview}...\"\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config.delete_history_entry(entry_id)
            self._refresh_history()

    def _clear_all_history(self):
        history = self.config.get_history()
        if not history:
            QMessageBox.information(self, "History Empty", "Your dictation history is already empty.")
            return

        pinned_count = sum(1 for e in history if e.get("is_pinned", False))
        unpinned_count = len(history) - pinned_count

        if unpinned_count == 0 and pinned_count > 0:
            QMessageBox.information(
                self,
                "All Items Pinned",
                f"All {pinned_count} transcript(s) in your history are currently 📌 Pinned.\n\n"
                "Pinned items are protected and will never be deleted by Clear History.\n"
                "To remove an item, unpin it first or use the individual 🗑️ Delete button."
            )
            return

        msg = (
            f"Are you sure you want to clear your dictation history?\n\n"
            f"📌 {pinned_count} pinned item(s) will be strictly PRESERVED.\n"
            f"🗑️ {unpinned_count} unpinned item(s) will be deleted."
        )
        reply = QMessageBox.question(
            self,
            "Clear History (Pin Protected)",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            cleared, preserved = self.config.clear_history(clear_pinned=False)
            self._refresh_history()
            QMessageBox.information(
                self,
                "History Cleared",
                f"✓ Successfully cleared {cleared} unpinned transcript(s).\n📌 {preserved} pinned item(s) were preserved."
            )

    def _test_api(self):
        key = self.api_key_input.text().strip()
        if not key:
            self.api_status_label.setText("❌ Please enter an API key first.")
            self.api_status_label.setStyleSheet("color: #EF4444;")
            return

        self.api_status_label.setText("⏳ Testing connection to Gemini...")
        self.api_status_label.setStyleSheet("color: #38BDF8;")
        QApplication.processEvents()

        model_code = self.model_combo.currentText().split()[0]
        self.gemini.set_model(model_code)
        ok, msg = self.gemini.test_connection(key)
        if ok:
            self.api_status_label.setText("✅ " + msg)
            self.api_status_label.setStyleSheet("color: #10B981;")
        else:
            self.api_status_label.setText("❌ " + msg)
            self.api_status_label.setStyleSheet("color: #EF4444;")

    def _toggle_mic_test(self):
        if self.test_recorder and self.test_recorder.is_recording:
            self._stop_mic_test()
        else:
            self._start_mic_test()

    def _start_mic_test(self):
        dev_idx = self.mic_combo.currentData()
        self.test_recorder = AudioRecorder(on_amplitude=self._on_test_amplitude)
        self.test_recorder.set_device(dev_idx)
        if self.test_recorder.start_recording():
            self.btn_test_mic.setText("Stop Test")
        else:
            QMessageBox.warning(self, "Mic Error", "Could not start microphone stream.")

    def _on_test_amplitude(self, amp: float):
        val = int(amp * 100)
        self.mic_level_bar.setValue(val)

    def _stop_mic_test(self):
        if self.test_recorder:
            self.test_recorder.stop_recording()
            self.test_recorder = None
        self.btn_test_mic.setText("Test Microphone")
        self.mic_level_bar.setValue(0)

    def _save_settings(self):
        self._stop_mic_test()

        # Save to config
        key = self.api_key_input.text().strip()
        model_code = self.model_combo.currentText().split()[0]
        mode = "push_to_talk" if self.radio_ptt.isChecked() else "toggle"
        hotkey_disp = self.hotkey_btn.display_str
        hotkey_inter = self.hotkey_btn.internal_str
        prompt_disp = self.prompt_hotkey_btn.display_str
        prompt_inter = self.prompt_hotkey_btn.internal_str
        trans_disp = self.transform_hotkey_btn.display_str
        trans_inter = self.transform_hotkey_btn.internal_str

        preset = self.config.get("mode_preset", "clean_dictation")
        custom_prompt = self.custom_prompt_edit.toPlainText().strip()

        vocab_raw = self.vocab_input.text()
        vocab = [v.strip() for v in vocab_raw.split(",") if v.strip()]

        dev_idx = self.mic_combo.currentData()
        dev_name = self.mic_combo.currentText()

        # Secure key persistence (Windows DPAPI)
        self.config.set_api_key(key)

        # Model / Router
        if model_code == "auto":
            self.config.set("model_mode", "auto")
            self.config.set("model_name", "gemini-3.5-flash-lite")
        else:
            self.config.set("model_mode", model_code)
            self.config.set("model_name", model_code)

        # Hotkeys
        self.config.set("hotkey_mode", mode)
        self.config.set("hotkey_display", hotkey_disp)
        self.config.set("hotkey", hotkey_inter)
        self.config.set("prompt_hotkey_display", prompt_disp)
        self.config.set("prompt_hotkey", prompt_inter)
        self.config.set("transform_hotkey_display", trans_disp)
        self.config.set("transform_hotkey", trans_inter)

        # Add to persistent shortcut history
        self.config.add_voice_hotkey_history(hotkey_disp, hotkey_inter)
        self.config.add_prompt_hotkey_history(prompt_disp, prompt_inter)
        self.config.add_transform_hotkey_history(trans_disp, trans_inter)

        # Active Profile
        active_prof = self.profile_combo.currentData()
        self.config.set("active_profile", active_prof)

        # Security & Privacy Settings (runs seamlessly in background)
        sec_cfg = self.config.get("security", {})
        ret_days = self.retention_combo.currentData() if (hasattr(self, 'retention_combo') and self.retention_combo) else sec_cfg.get("history_retention_days", 30)
        log_red = self.cb_log_redaction.isChecked() if (hasattr(self, 'cb_log_redaction') and self.cb_log_redaction) else sec_cfg.get("log_redaction", True)
        self.config.set("security", {
            "encrypt_keys": True,
            "history_retention_days": ret_days,
            "telemetry_enabled": True,
            "log_redaction": log_red
        })
        self.config.enforce_retention()

        # Custom Prompt & Saved Prompts
        target_p_id = getattr(self, '_editing_prompt_id', None)
        p_title = self.prompt_title_input.text().strip()
        custom_prompt = self.custom_prompt_edit.toPlainText().strip()
        if p_title and custom_prompt:
            saved_id = self.config.save_custom_prompt(p_title, custom_prompt, prompt_id=target_p_id, set_active=True)
            self._editing_prompt_id = saved_id

        self.config.set("mode_preset", preset)
        self.config.set("custom_prompt", custom_prompt)
        self.config.set("custom_vocabulary", vocab)
        self.config.set("auto_paste", self.cb_auto_paste.isChecked())
        self.config.set("play_sounds", self.cb_sounds.isChecked())
        self.config.set("auto_prompt_conversion", self.cb_auto_prompt.isChecked())
        start_win = self.cb_start_with_windows.isChecked()
        self.config.set("start_with_windows", start_win)
        try:
            from ..config import setup_windows_startup
            setup_windows_startup(start_win)
        except Exception as e:
            logger.warning(f"Could not update Windows startup: {e}")
        self.config.set("input_device_index", dev_idx)
        self.config.set("input_device_name", dev_name)

        if hasattr(self, 'cb_dsp_fan_filter') and self.cb_dsp_fan_filter:
            self.config.set("dsp_fan_filter_enabled", self.cb_dsp_fan_filter.isChecked())
        if hasattr(self, 'cb_dsp_noise_gate') and self.cb_dsp_noise_gate:
            self.config.set("dsp_noise_gate_enabled", self.cb_dsp_noise_gate.isChecked())
        if hasattr(self, 'cb_offline_fallback') and self.cb_offline_fallback:
            self.config.set("offline_fallback_enabled", self.cb_offline_fallback.isChecked())

        if hasattr(self, 'cb_auto_cost_mode') and self.cb_auto_cost_mode:
            self.config.set("auto_cost_mode", self.cb_auto_cost_mode.isChecked())

        self.gemini.set_api_key(key)
        self.gemini.set_model(model_code)

        # Refresh all views immediately so changes appear instantly without closing or restart
        self._refresh_saved_prompts()
        self._refresh_history()
        self._refresh_cost_stats()
        self._refresh_dictionary()
        self._refresh_snippets()
        self._refresh_vocab_table()
        self._on_profile_combo_changed()
        self._on_vocab_test_changed(self.vocab_test_input.text())

        # Emit live settings applied signal to main coordinator
        self.settings_applied.emit()

        # Provide immediate visual confirmation without closing window
        self.btn_save.setText("✓ Settings Saved & Applied!")
        self.btn_save.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
        self.save_status_label.setText(f"✅ Active: {hotkey_disp} ({mode})")

        QTimer.singleShot(2500, lambda: [
            self.btn_save.setText("💾 Save & Apply Changes"),
            self.btn_save.setStyleSheet("")
        ])

    def _restart_app(self):
        """Saves current settings and immediately restarts Gemini Flow cleanly without rebooting."""
        self._save_settings()
        self.save_status_label.setText("🔄 Restarting Gemini Flow...")
        self.save_status_label.setStyleSheet("color: #38BDF8; font-weight: 600; font-size: 13px;")
        QApplication.processEvents()

        if hasattr(self, 'main_app') and self.main_app and hasattr(self.main_app, 'restart_app'):
            self.main_app.restart_app()
        else:
            # Standalone launcher fallback
            try:
                import subprocess, sys
                launcher = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "main_standalone.py")
                DETACHED_PROCESS = 0x00000008
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen([sys.executable, launcher], creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW, close_fds=True)
            except Exception as e:
                logger.error(f"Fallback restart spawn failed: {e}")
            self.close()

    def showEvent(self, event):
        if hasattr(self, 'live_sync_timer') and self.live_sync_timer and not self.live_sync_timer.isActive():
            self.live_sync_timer.start(2500)
        self._load_values()
        super().showEvent(event)

    def _restore_window_state(self):
        """Restores window geometry, dimensions, and maximized state with display bounds validation."""
        try:
            state = self.config.get("settings_window_state", {})
            if not state:
                self.resize(780, 720)
                return

            x = state.get("x")
            y = state.get("y")
            w = state.get("width", 780)
            h = state.get("height", 720)
            is_max = bool(state.get("is_maximized", False))

            w = max(720, int(w))
            h = max(620, int(h))

            # Multi-monitor bounds validation: verify coordinates intersect visible screen
            coords_valid = False
            if x is not None and y is not None:
                pt = QPoint(int(x), int(y))
                for screen in QApplication.screens():
                    if screen.availableGeometry().contains(pt):
                        coords_valid = True
                        break

            if coords_valid:
                self.setGeometry(int(x), int(y), w, h)
            else:
                # Center on primary screen if coordinates are invalid or monitor disconnected
                primary = QApplication.primaryScreen()
                if primary:
                    geo = primary.availableGeometry()
                    cx = geo.x() + (geo.width() - w) // 2
                    cy = geo.y() + (geo.height() - h) // 2
                    self.setGeometry(cx, cy, w, h)
                else:
                    self.resize(w, h)

            if is_max:
                QTimer.singleShot(0, self.showMaximized)
        except Exception as ex:
            logger.error(f"Error restoring window state: {ex}")
            self.resize(780, 720)

    def _save_window_state(self):
        """Serializes current window geometry and maximized state to configuration."""
        try:
            is_max = self.isMaximized()
            state = {
                "is_maximized": is_max
            }
            if is_max:
                prev = self.config.get("settings_window_state", {})
                state["x"] = prev.get("x", self.normalGeometry().x())
                state["y"] = prev.get("y", self.normalGeometry().y())
                state["width"] = max(720, prev.get("width", self.normalGeometry().width()))
                state["height"] = max(620, prev.get("height", self.normalGeometry().height()))
            else:
                state["x"] = self.x()
                state["y"] = self.y()
                state["width"] = max(720, self.width())
                state["height"] = max(620, self.height())

            self.config.set("settings_window_state", state)
            logger.debug(f"Saved window state: {state}")
        except Exception as ex:
            logger.error(f"Error saving window state: {ex}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_debounce_save_timer') and not self.isMaximized():
            self._debounce_save_timer.start(250)

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, '_debounce_save_timer') and not self.isMaximized():
            self._debounce_save_timer.start(250)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            if hasattr(self, '_debounce_save_timer'):
                self._debounce_save_timer.start(250)

    def closeEvent(self, event):
        self._stop_mic_test()
        if hasattr(self, 'live_sync_timer') and self.live_sync_timer:
            self.live_sync_timer.stop()
        if hasattr(self, '_debounce_save_timer') and self._debounce_save_timer.isActive():
            self._debounce_save_timer.stop()
        self._save_window_state()
        super().closeEvent(event)
