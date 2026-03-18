import os

# OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

# Capture
CAPTURE_INTERVAL_SEC = 5
SCREENSHOT_JPEG_QUALITY = 60
SCREENSHOT_MAX_DIMENSION = 1920

# Hotkeys
TOGGLE_HOTKEY = "ctrl+shift+x"      # Show / hide widgets
LOCK_HOTKEY = "ctrl+shift+l"        # Lock / unlock drag mode

# Widget appearance
WIDGET_WIDTH = 280
WIDGET_OPACITY = 0.82
WIDGET_CORNER_RADIUS = 14
WIDGET_BG = (30, 30, 42)
WIDGET_BORDER = (255, 255, 255, 25)

# Default positions (right side, stacked with spacing)
WIDGET_DEFAULTS = {
    "lane":  {"x_offset": 20, "y": 120},
    "macro": {"x_offset": 20, "y": 210},
    "alert": {"x_offset": 20, "y": 300},
}

# Accent colors
ACCENT = {
    "safe": "#22c55e",
    "caution": "#f59e0b",
    "danger": "#ef4444",
    "neutral": "#94a3b8",
    "info": "#818cf8",
}

# Positions save file
POSITIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "widget_positions.json")
