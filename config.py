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
CAPTURE_INTERVAL_SEC = 30
SCREENSHOT_JPEG_QUALITY = 60
SCREENSHOT_MAX_DIMENSION = 1920

# Hotkeys
TOGGLE_HOTKEY = "ctrl+shift+x"
LOCK_HOTKEY = "ctrl+shift+l"
SCOREBOARD_KEY = "tab"

# Widget appearance (Apple glass style)
WIDGET_WIDTH = 320
WIDGET_OPACITY = 0.78
WIDGET_CORNER_RADIUS = 16
WIDGET_BG = (25, 30, 52)           # Deep navy blue glass
WIDGET_BORDER = (255, 255, 255, 15)

# Default positions (right column, stacked with breathing room)
WIDGET_DEFAULTS = {
    "lane":      {"x_offset": 16, "y": 60},
    "macro":     {"x_offset": 16, "y": 172},
    "matchup":   {"x_offset": 16, "y": 284},
    "objective": {"x_offset": 16, "y": 396},
    "alert":     {"x_offset": 16, "y": 508},
}

# Accent colors
ACCENT = {
    "safe": "#34d399",
    "caution": "#fbbf24",
    "danger": "#f87171",
    "neutral": "#94a3b8",
    "info": "#818cf8",
}

# Positions save file
POSITIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "widget_positions.json")
