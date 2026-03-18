import sys
import threading

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication
import keyboard

from analyzer import Analyzer
from capture import capture_screenshot, screenshot_size_kb
from config import CAPTURE_INTERVAL_SEC, TOGGLE_HOTKEY, LOCK_HOTKEY
from overlay import OverlayManager


class _Signal(QObject):
    new_result = pyqtSignal(dict)
    toggle = pyqtSignal()
    toggle_lock = pyqtSignal()


def _capture_loop(analyzer: Analyzer, signal: _Signal, stop: threading.Event):
    print("[Coach] Capture loop started")
    while not stop.is_set():
        try:
            b64 = capture_screenshot()
            print(f"[Capture] {screenshot_size_kb(b64):.0f} KB")
            result = analyzer.analyze(b64)
            signal.new_result.emit(result)
            for k in ("lane", "macro", "alert"):
                if k in result:
                    print(f"  [{k.upper()}] {result[k].get('action', '?')}"
                          f" — {result[k].get('reason', '')}")
        except Exception as e:
            print(f"[Coach] Error: {e}")
        stop.wait(CAPTURE_INTERVAL_SEC)


def main():
    if not (sys.modules.get("config") and __import__("config").OPENAI_API_KEY):
        import os
        if not os.environ.get("OPENAI_API_KEY"):
            print("[Error] OPENAI_API_KEY not set.")
            print("  Set it with: set OPENAI_API_KEY=sk-your-key-here")
            sys.exit(1)

    print("=" * 50)
    print("  League AI Coach")
    print("=" * 50)
    print(f"  Interval    : every {CAPTURE_INTERVAL_SEC}s")
    print(f"  Show/Hide   : {TOGGLE_HOTKEY}")
    print(f"  Lock/Unlock : {LOCK_HOTKEY}")
    print(f"  Quit        : Ctrl+C")
    print("=" * 50)

    app = QApplication(sys.argv)
    analyzer = Analyzer()
    overlay = OverlayManager()
    signal = _Signal()

    signal.new_result.connect(overlay.update_from_analysis)
    signal.toggle.connect(overlay.toggle)
    signal.toggle_lock.connect(overlay.toggle_lock)

    keyboard.add_hotkey(TOGGLE_HOTKEY, lambda: signal.toggle.emit())
    keyboard.add_hotkey(LOCK_HOTKEY, lambda: signal.toggle_lock.emit())

    overlay.show()
    print("[Coach] Overlay visible. Waiting for game...")

    stop = threading.Event()
    thread = threading.Thread(target=_capture_loop,
                              args=(analyzer, signal, stop), daemon=True)
    thread.start()

    try:
        app.exec_()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n[Coach] Shutting down...")
        stop.set()
        keyboard.unhook_all()
        thread.join(timeout=5)
        cost = analyzer.get_cost_estimate()
        print(f"[Coach] {analyzer.call_count} calls | "
              f"{analyzer.total_tokens} tokens | ~${cost:.4f}")

    sys.exit(0)


if __name__ == "__main__":
    main()
