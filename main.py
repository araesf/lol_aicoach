import sys
import threading
import time

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication
import keyboard

from analyzer import Analyzer
from capture import capture_game_regions, capture_scoreboard, regions_size_kb
from config import CAPTURE_INTERVAL_SEC, TOGGLE_HOTKEY, LOCK_HOTKEY, SCOREBOARD_KEY
from overlay import OverlayManager

SCOREBOARD_COOLDOWN_SEC = 60


class _Signal(QObject):
    new_result = pyqtSignal(dict)
    toggle = pyqtSignal()
    toggle_lock = pyqtSignal()


def _capture_loop(analyzer: Analyzer, signal: _Signal, stop: threading.Event):
    print("[Coach] Capture loop started")
    while not stop.is_set():
        try:
            regions = capture_game_regions()
            print(f"[Capture] {regions_size_kb(regions):.0f} KB "
                  f"(main + minimap + hud)")
            result = analyzer.analyze(regions)
            signal.new_result.emit(result)
            for k in ("lane", "macro", "matchup", "objective", "alert"):
                if k in result:
                    print(f"  [{k.upper()}] {result[k].get('action', '?')}"
                          f" — {result[k].get('reason', '')}")
        except Exception as e:
            print(f"[Coach] Error: {e}")
        stop.wait(CAPTURE_INTERVAL_SEC)


_last_scoreboard_time = 0
_scoreboard_lock = threading.Lock()


def _on_tab_press(analyzer: Analyzer):
    """Capture scoreboard on Tab press. Debounced to once per 60s."""
    global _last_scoreboard_time

    with _scoreboard_lock:
        now = time.time()
        if now - _last_scoreboard_time < SCOREBOARD_COOLDOWN_SEC:
            remaining = int(SCOREBOARD_COOLDOWN_SEC - (now - _last_scoreboard_time))
            print(f"[Scoreboard] On cooldown — next update in {remaining}s")
            return
        _last_scoreboard_time = now

    time.sleep(0.3)  # Wait for scoreboard to render
    try:
        b64 = capture_scoreboard()
        analyzer.update_scoreboard(b64)
    except Exception as e:
        print(f"[Scoreboard] Error: {e}")


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
    print(f"  Scoreboard  : Tab (once per {SCOREBOARD_COOLDOWN_SEC}s)")
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

    keyboard.on_press_key(
        SCOREBOARD_KEY,
        lambda _: threading.Thread(
            target=_on_tab_press, args=(analyzer,), daemon=True
        ).start(),
        suppress=False,
    )

    overlay.show()
    print("[Coach] Overlay visible. Press Tab in-game to capture scoreboard.")

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
