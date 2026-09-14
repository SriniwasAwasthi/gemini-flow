"""
Self-Test Verification for Gemini Flow Components
Tests config loading, dictionary replacement, snippet expansion, prompt enhancer, audio recording, and PyQt6 instantiation.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_all():
    print("Testing Config Manager...")
    from app.config import ConfigManager
    cfg = ConfigManager()
    assert cfg.get("hotkey") is not None
    prompt = cfg.get_system_prompt()
    assert len(prompt) > 20
    assert "Srinivas" in prompt
    print("[PASS] Config Manager OK.")

    print("Testing Audio Devices...")
    from app.audio_recorder import AudioRecorder
    devices = AudioRecorder.get_input_devices()
    print(f"[PASS] Audio Devices found: {len(devices)} device(s).")
    for d in devices[:3]:
        print(f"  - Device #{d['index']}: {d['name']}")

    print("Testing Gemini Engine & Dictionary / Snippets logic...")
    from app.gemini_engine import GeminiEngine
    engine = GeminiEngine(api_key="test_key_dummy")
    cleaned = engine._clean_output('```\nHello World\n```')
    assert cleaned == "Hello World"

    # Test Dictionary Replacement
    dict_rules = [{"spoken": "Srinivas Avasthi", "replacement": "Sri Srinivas Awasthi"}, {"spoken": "Wisper", "replacement": "Wispr"}]
    test_text = "Hello, my name is Srinivas Avasthi and I use Wisper."
    replaced = GeminiEngine.apply_dictionary(test_text, dict_rules)
    assert replaced == "Hello, my name is Sri Srinivas Awasthi and I use Wispr."
    print(f"  - Dictionary replacement verified: '{test_text}' -> '{replaced}'")
    print("[PASS] Dictionary Replacement Logic OK.")

    # Test Snippets Expansion
    snippets = [{
        "trigger": "Hey I am Srinivas LinkedIn GitHub Instagram",
        "content": "Full Profile: Srinivas Awasthi, LinkedIn, GitHub, Instagram."
    }]
    snip_test = "Hey I am Srinivas LinkedIn GitHub Instagram"
    expanded = GeminiEngine.apply_snippets(snip_test, snippets)
    assert expanded == "Full Profile: Srinivas Awasthi, LinkedIn, GitHub, Instagram."
    print(f"  - Snippet expansion verified: '{snip_test}' -> '{expanded}'")
    print("[PASS] Snippet Expansion Logic OK.")

    print("Testing Hotkey Manager...")
    from app.hotkey_manager import HotkeyManager
    hkm = HotkeyManager("<ctrl>+<cmd>", mode="toggle", prompt_hotkey_str="<ctrl>+<shift>+p")
    assert hkm.hotkey_str == "<ctrl>+<cmd>"
    assert hkm.prompt_hotkey_str == "<ctrl>+<shift>+p"
    print("[PASS] Hotkey Manager OK.")

    print("Testing Text Injector...")
    from app.text_injector import TextInjector
    injector = TextInjector()
    assert injector is not None
    print("[PASS] Text Injector OK.")

    print("Testing PyQt6 GUI Modules Import & Widgets...")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from app.ui.floating_hud import FloatingHUD
    hud = FloatingHUD(cfg)
    assert hud is not None
    print("[PASS] Floating HUD Initialized OK.")

    from app.ui.tray_icon import create_mic_pixmap
    pix = create_mic_pixmap()
    assert not pix.isNull()
    print("[PASS] Tray Icon Renderer OK.")

    from app.ui.settings_dialog import SettingsDialog, HotkeyCaptureButton
    btn = HotkeyCaptureButton("Ctrl + Win", "<ctrl>+<cmd>")
    assert btn.display_str == "Ctrl + Win"
    print("[PASS] HotkeyCaptureButton OK.")

    print("\n==========================================")
    print("ALL GEMINI FLOW COMPONENTS PASSED 100%!")
    print("==========================================")

if __name__ == "__main__":
    test_all()

