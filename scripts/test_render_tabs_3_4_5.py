import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QTableWidgetItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PIL import Image

PROJECT_ROOT = Path(r"E:\W c One Drive\Wisper")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import ConfigManager
from app.ui.settings_dialog import SettingsDialog

app = QApplication.instance() or QApplication(sys.argv)
cfg = ConfigManager()
dlg = SettingsDialog(cfg, None)
dlg.resize(1536, 864)
dlg.show()
app.processEvents()

# 1. Enrich Custom Dictionary
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
dlg._refresh_dictionary()

# 2. Enrich Quick Text
snippets = [
    {"trigger": "my developer bio", "text": "Srinivas Awasthi | Senior AI Engineer | github.com/srinivas-awasthi | linkedin.com/in/srinivas-awasthi"},
    {"trigger": "insert bug report template", "text": "## Description\n\n## Reproduction Steps\n1. \n2. \n\n## Expected vs Actual Behavior\n"},
    {"trigger": "paste meeting sync agenda", "text": "Hi team, thanks for joining. Today's agenda: 1) Speech pipeline latency 2) Custom vocabulary normalization 3) CI/CD deployment."},
    {"trigger": "license header", "text": "// Copyright (c) 2026 Srinivas Awasthi. All rights reserved. Open-source under MIT License."},
]
cfg.set_snippets(snippets)
dlg._refresh_snippets()

# Render Tab 3: Vocabulary Engine
dlg.tabs.setCurrentIndex(3)
for i, b in enumerate(dlg.nav_buttons):
    b.set_active(i == 3)
dlg.vocab_test_input.setText("testing fast whisper with pie dantic and git hub")
dlg.vocab_test_output.setText("testing Faster-Whisper with Pydantic and GitHub")
app.processEvents()
img_vocab = dlg.grab().toImage()
img_vocab.save("videos/temp_3min_build/preview_tab_3_vocab_rich.png")

# Render Tab 4: Custom Dictionary
dlg.tabs.setCurrentIndex(4)
for i, b in enumerate(dlg.nav_buttons):
    b.set_active(i == 4)
dlg.dict_table.setCurrentCell(0, 0)
dlg._on_dict_row_selected()
app.processEvents()
img_dict = dlg.grab().toImage()
img_dict.save("videos/temp_3min_build/preview_tab_4_dict_rich.png")

# Render Tab 5: Quick Text
dlg.tabs.setCurrentIndex(5)
for i, b in enumerate(dlg.nav_buttons):
    b.set_active(i == 5)
dlg.snippet_table.setCurrentCell(0, 0)
app.processEvents()
img_snip = dlg.grab().toImage()
img_snip.save("videos/temp_3min_build/preview_tab_5_quicktext_rich.png")

print("Successfully captured preview_tab_3_vocab_rich.png, preview_tab_4_dict_rich.png, preview_tab_5_quicktext_rich.png")
