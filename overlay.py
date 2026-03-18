import json
import os

from PyQt5.QtCore import Qt, QPoint, QRectF
from PyQt5.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QLabel, QHBoxLayout, QVBoxLayout, QWidget

from config import (
    ACCENT,
    POSITIONS_FILE,
    WIDGET_BG,
    WIDGET_BORDER,
    WIDGET_CORNER_RADIUS,
    WIDGET_DEFAULTS,
    WIDGET_OPACITY,
    WIDGET_WIDTH,
)

# ── Color detection ──────────────────────────────────────────────────────────

_KW = {
    "danger":  ["all-in", "engage", "gank", "dive", "back off", "careful",
                "incoming", "do not"],
    "caution": ["trade", "poke", "dragon", "baron", "recall", "missing",
                "powerspike", "objective", "contest", "back now", "watch"],
    "safe":    ["freeze", "safe", "farm", "clear", "scale", "patience",
                "wait", "sit back"],
    "info":    ["push", "rotate", "roam", "split", "group", "ward", "herald",
                "pressure", "crash", "shove", "buy"],
}


def _color_for(text: str) -> str:
    lo = text.lower()
    for cat, words in _KW.items():
        if any(w in lo for w in words):
            return ACCENT[cat]
    return ACCENT["neutral"]


# ── Saved positions ──────────────────────────────────────────────────────────

def _load_positions() -> dict:
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_positions(pos: dict):
    try:
        with open(POSITIONS_FILE, "w") as f:
            json.dump(pos, f, indent=2)
    except OSError as e:
        print(f"[Overlay] Failed to save positions: {e}")


# ── Widget ───────────────────────────────────────────────────────────────────

class CoachWidget(QWidget):
    """Small, frosted-glass, draggable coaching widget."""

    def __init__(self, key: str):
        super().__init__()
        self.key = key
        self._dragging = False
        self._drag_offset = QPoint()
        self._locked = True
        self._cur_action = ""
        self._cur_reason = "Waiting..."
        self._init_ui()
        self._init_window()

    def _init_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(WIDGET_WIDTH)
        self._set_clickthrough(True)

        saved = _load_positions()
        screen = QApplication.primaryScreen().geometry()
        if self.key in saved:
            self.move(saved[self.key]["x"], saved[self.key]["y"])
        else:
            d = WIDGET_DEFAULTS[self.key]
            self.move(screen.width() - WIDGET_WIDTH - d["x_offset"], d["y"])

    def _set_clickthrough(self, on: bool):
        self.setAttribute(Qt.WA_TransparentForMouseEvents, on)

    # ── UI ───────────────────────────────────────────────────────────────

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(8)

        self._tag = QLabel(self.key.upper())
        self._tag.setFixedHeight(18)
        self._tag.setStyleSheet(self._tag_css(ACCENT["neutral"]))
        top.addWidget(self._tag)

        self._action_lbl = QLabel("")
        self._action_lbl.setStyleSheet(
            "color: white; font-size: 12px; font-weight: 600;"
            " font-family: 'Segoe UI', sans-serif;"
        )
        self._action_lbl.setWordWrap(True)
        top.addWidget(self._action_lbl, 1)
        root.addLayout(top)

        self._reason_lbl = QLabel("Waiting...")
        self._reason_lbl.setWordWrap(True)
        self._reason_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.65); font-size: 11px;"
            " font-family: 'Segoe UI', sans-serif;"
        )
        root.addWidget(self._reason_lbl)

    @staticmethod
    def _tag_css(color: str) -> str:
        return (
            f"background-color: {color}25; color: {color};"
            f" border: 1px solid {color}40; border-radius: 4px;"
            f" padding: 1px 6px; font-size: 9px; font-weight: 700;"
            f" font-family: 'Segoe UI', sans-serif;"
        )

    # ── Paint ────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        r, g, b = WIDGET_BG

        path = QPainterPath()
        path.addRoundedRect(rect, WIDGET_CORNER_RADIUS, WIDGET_CORNER_RADIUS)
        p.fillPath(path, QColor(r, g, b, int(255 * WIDGET_OPACITY)))

        br, bg_, bb, ba = WIDGET_BORDER
        if not self._locked:
            p.setPen(QPen(QColor(129, 140, 248, 120), 1.5))
        else:
            p.setPen(QPen(QColor(br, bg_, bb, ba), 1))
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5),
                          WIDGET_CORNER_RADIUS, WIDGET_CORNER_RADIUS)

    # ── Drag ─────────────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if not self._locked and e.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_offset = e.globalPos() - self.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))

    def mouseMoveEvent(self, e):
        if self._dragging:
            self.move(e.globalPos() - self._drag_offset)

    def mouseReleaseEvent(self, e):
        if self._dragging and e.button() == Qt.LeftButton:
            self._dragging = False
            self.setCursor(QCursor(Qt.OpenHandCursor))
            self._persist_position()

    def _persist_position(self):
        saved = _load_positions()
        saved[self.key] = {"x": self.x(), "y": self.y()}
        _save_positions(saved)

    # ── Public ───────────────────────────────────────────────────────────

    def set_locked(self, locked: bool):
        self._locked = locked
        self._set_clickthrough(locked)
        self.setCursor(QCursor(Qt.ArrowCursor if locked else Qt.OpenHandCursor))
        self.update()

    def update_advice(self, action: str, reason: str):
        if action == self._cur_action and reason == self._cur_reason:
            return
        self._cur_action = action
        self._cur_reason = reason
        self._action_lbl.setText(action)
        self._reason_lbl.setText(reason)
        self._tag.setStyleSheet(self._tag_css(_color_for(action)))
        self.adjustSize()
        self.update()


# ── Manager ──────────────────────────────────────────────────────────────────

class OverlayManager:
    def __init__(self):
        self._widgets = {
            "lane":  CoachWidget("lane"),
            "macro": CoachWidget("macro"),
            "alert": CoachWidget("alert"),
        }
        self._visible = True
        self._locked = True

    def show(self):
        for w in self._widgets.values():
            w.show()
        self._visible = True

    def hide(self):
        for w in self._widgets.values():
            w.hide()
        self._visible = False

    def toggle(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def toggle_lock(self):
        self._locked = not self._locked
        for w in self._widgets.values():
            w.set_locked(self._locked)
        state = "locked" if self._locked else "unlocked — drag to reposition"
        print(f"[Overlay] Widgets {state}")

    def update_from_analysis(self, result: dict):
        for key, widget in self._widgets.items():
            if key in result:
                widget.update_advice(
                    result[key].get("action", "..."),
                    result[key].get("reason", ""),
                )
