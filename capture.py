import base64
import io
import threading

import mss
from PIL import Image

from config import SCREENSHOT_JPEG_QUALITY

_local = threading.local()


def _get_sct():
    if not hasattr(_local, "sct"):
        _local.sct = mss.mss()
    return _local.sct


def _img_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=SCREENSHOT_JPEG_QUALITY)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def capture_game_regions() -> dict[str, str]:
    """Capture and crop the 3 key regions of a League game.

    Returns dict with base64 JPEGs for:
      - "main"    : center of screen (lane, champion, wave, fights) — 60% of screen
      - "minimap" : bottom-right corner (enemy positions, jungle tracking)
      - "hud"     : bottom-center + top bar (HP, mana, CS, gold, KDA, items, game clock)

    All regions are at native resolution for detail:high to read text clearly.
    Total payload is ~3x smaller than sending the full screen.
    """
    sct = _get_sct()
    mon = sct.monitors[1]
    raw = sct.grab(mon)
    full = Image.frombytes("RGB", (raw.width, raw.height), raw.rgb)
    w, h = full.size

    # Main gameplay area — center 60% of screen (lane, wave, champion, fights)
    main_crop = full.crop((int(w * 0.15), int(h * 0.05), int(w * 0.85), int(h * 0.75)))

    # Minimap — bottom-right ~20% (shows all enemy positions, jungle)
    minimap_crop = full.crop((int(w * 0.78), int(h * 0.72), w, h))

    # HUD bar — bottom center (HP, mana, abilities, items, CS, gold)
    # Plus top bar for game clock, KDA, tower status
    hud_bottom = full.crop((int(w * 0.25), int(h * 0.78), int(w * 0.75), h))
    hud_top = full.crop((int(w * 0.3), 0, int(w * 0.7), int(h * 0.06)))

    # Stitch top + bottom HUD into one image
    hud_combined = Image.new("RGB", (hud_bottom.width, hud_top.height + hud_bottom.height))
    hud_combined.paste(hud_top.resize((hud_bottom.width, hud_top.height)), (0, 0))
    hud_combined.paste(hud_bottom, (0, hud_top.height))

    return {
        "main": _img_to_b64(main_crop),
        "minimap": _img_to_b64(minimap_crop),
        "hud": _img_to_b64(hud_combined),
    }


def capture_scoreboard() -> str:
    """Capture the center of screen where the Tab scoreboard appears.

    The Tab scoreboard shows: all 10 champions, CS, KDA, items, gold,
    summoner spells, levels. This is the richest data source in the game.
    """
    sct = _get_sct()
    mon = sct.monitors[1]
    raw = sct.grab(mon)
    full = Image.frombytes("RGB", (raw.width, raw.height), raw.rgb)
    w, h = full.size

    # Scoreboard is centered, roughly 70% of screen width, 60% height
    scoreboard = full.crop((int(w * 0.12), int(h * 0.1), int(w * 0.88), int(h * 0.85)))
    return _img_to_b64(scoreboard)


def regions_size_kb(regions: dict[str, str]) -> float:
    total = sum(len(v) for v in regions.values())
    return total * 3 / 4 / 1024
