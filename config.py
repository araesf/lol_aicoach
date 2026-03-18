import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

# Capture
CAPTURE_INTERVAL_SEC = 60
SCREENSHOT_JPEG_QUALITY = 60
SCREENSHOT_MAX_DIMENSION = 1920

# Hotkeys
TOGGLE_HOTKEY = "ctrl+shift+x"
LOCK_HOTKEY = "ctrl+shift+l"
SCOREBOARD_KEY = "tab"

# Widget appearance
WIDGET_WIDTH = 300
WIDGET_OPACITY = 0.82
WIDGET_CORNER_RADIUS = 18
WIDGET_BG = (15, 18, 35)            # Deeper navy
WIDGET_BORDER = (255, 255, 255, 12) # Barely visible

# Default positions (right column, evenly spaced)
WIDGET_DEFAULTS = {
    "lane":      {"x_offset": 14, "y": 50},
    "macro":     {"x_offset": 14, "y": 160},
    "matchup":   {"x_offset": 14, "y": 270},
    "objective": {"x_offset": 14, "y": 380},
    "alert":     {"x_offset": 14, "y": 490},
}

# Accent colors (softer, pastel-ish)
ACCENT = {
    "safe": "#6ee7b7",
    "caution": "#fcd34d",
    "danger": "#fca5a5",
    "neutral": "#cbd5e1",
    "info": "#a5b4fc",
}

# Positions save file
POSITIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "widget_positions.json")
