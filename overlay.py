import json
import os

from PyQt5.QtCore import Qt, QPoint, QRectF
from PyQt5.QtGui import QColor, QCursor, QLinearGradient, QPainter, QPainterPath, QPen
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
                "incoming", "do not", "don't fight", "avoid"],
    "caution": ["trade", "poke", "dragon", "baron", "recall", "missing",
                "powerspike", "objective", "contest", "back now", "watch",
                "respect", "caution"],
    "safe":    ["freeze", "safe", "farm", "clear", "scale", "patience",
                "wait", "sit back", "stay", "hold"],
    "info":    ["push", "rotate", "roam", "split", "group", "ward", "herald",
                "pressure", "crash", "shove", "buy", "build", "rush"],
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


# ── Icons ────────────────────────────────────────────────────────────────────

_ICONS = {
    "lane": "\u2694",       # Crossed swords
    "macro": "\u2691",      # Flag
    "matchup": "\u2696",    # Scales
    "objective": "\u25C6",  # Diamond
    "alert": "\u26A0",      # Warning triangle
}

_TITLES = {
    "lane": "Lane",
    "macro": "Macro",
    "matchup": "Matchup",
    "objective": "Objective",
    "alert": "Alert",
}


# ── Widget ───────────────────────────────────────────────────────────────────

class CoachWidget(QWidget):
    """Apple glass-style frosted coaching widget."""

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
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(6)

        # Header row: icon + title
        header = QHBoxLayout()
        header.setSpacing(7)

        icon = QLabel(_ICONS.get(self.key, ""))
        icon.setStyleSheet(
            "color: rgba(255,255,255,0.45); font-size: 12px;"
        )
        icon.setFixedWidth(16)
        header.addWidget(icon)

        title = QLabel(_TITLES.get(self.key, self.key.upper()))
        title.setStyleSheet(
            "color: rgba(255,255,255,0.45); font-size: 11px; font-weight: 500;"
            " letter-spacing: 0.5px;"
            " font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;"
        )
        header.addWidget(title)
        header.addStretch()

        self._tag = QLabel("")
        self._tag.setFixedHeight(20)
        self._tag.setStyleSheet(self._tag_css(ACCENT["neutral"]))
        header.addWidget(self._tag)

        root.addLayout(header)

        # Action text (main advice — larger, white, bold)
        self._action_lbl = QLabel("")
        self._action_lbl.setWordWrap(True)
        self._action_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.95); font-size: 14px; font-weight: 600;"
            " font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;"
            " line-height: 1.3;"
        )
        root.addWidget(self._action_lbl)

        # Reason text (context — smaller, muted)
        self._reason_lbl = QLabel("Waiting...")
        self._reason_lbl.setWordWrap(True)
        self._reason_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.50); font-size: 12px; font-weight: 400;"
            " font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;"
            " line-height: 1.3;"
        )
        root.addWidget(self._reason_lbl)

    @staticmethod
    def _tag_css(color: str) -> str:
        return (
            f"background-color: {color}20; color: {color};"
            f" border: 1px solid {color}30; border-radius: 5px;"
            f" padding: 2px 8px; font-size: 10px; font-weight: 600;"
            f" font-family: 'Segoe UI', 'SF Pro Display', sans-serif;"
        )

    # ── Paint (Apple glass effect) ───────────────────────────────────────

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        r, g, b = WIDGET_BG

        # Glass gradient — slightly lighter at top
        path = QPainterPath()
        path.addRoundedRect(rect, WIDGET_CORNER_RADIUS, WIDGET_CORNER_RADIUS)

        grad = QLinearGradient(0, 0, 0, rect.height())
        grad.setColorAt(0, QColor(r + 12, g + 12, b + 12, int(255 * WIDGET_OPACITY)))
        grad.setColorAt(1, QColor(r, g, b, int(255 * (WIDGET_OPACITY + 0.05))))
        p.fillPath(path, grad)

        # Top highlight (subtle light edge like real glass)
        highlight = QPainterPath()
        highlight_rect = QRectF(rect.x() + 1, rect.y() + 1,
                                rect.width() - 2, rect.height() * 0.45)
        highlight.addRoundedRect(highlight_rect,
                                 WIDGET_CORNER_RADIUS - 1, WIDGET_CORNER_RADIUS - 1)
        p.fillPath(highlight, QColor(255, 255, 255, 8))

        # Border
        br, bg_, bb, ba = WIDGET_BORDER
        if not self._locked:
            p.setPen(QPen(QColor(129, 140, 248, 100), 1.5))
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
        accent = _color_for(action)
        self._action_lbl.setText(action)
        self._reason_lbl.setText(reason)
        self._tag.setStyleSheet(self._tag_css(accent))
        self._tag.setText(self.key.upper())
        self.adjustSize()
        self.update()


# ── Manager ──────────────────────────────────────────────────────────────────

WIDGET_KEYS = ["lane", "macro", "matchup", "objective", "alert"]


class OverlayManager:
    def __init__(self):
        self._widgets = {k: CoachWidget(k) for k in WIDGET_KEYS}
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
