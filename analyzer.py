import copy
import json
import os
import re
import time
from collections import deque
from pathlib import Path

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL

_PROMPT_PATH = Path(__file__).parent / "prompts" / "macro_coach.txt"
SYSTEM_PROMPT = _PROMPT_PATH.read_text()

DEFAULT_RESPONSE = {
    "lane": {"action": "Analyzing...", "reason": "Waiting for first screenshot."},
    "macro": {"action": "Analyzing...", "reason": "Waiting for first screenshot."},
    "matchup": {"action": "Press Tab", "reason": "Press Tab in-game to capture the scoreboard for matchup analysis."},
    "objective": {"action": "Analyzing...", "reason": "Scanning for objective timers."},
    "alert": {"action": "Starting up", "reason": "First analysis incoming.", "urgency": "low"},
}

MAX_CONTEXT_HISTORY = 4
API_TIMEOUT_SEC = 25
WIDGET_KEYS = ("lane", "macro", "matchup", "objective", "alert")

_JSON_RE = re.compile(r"\{[\s\S]*\}")

SCOREBOARD_EXTRACT_PROMPT = """Look at this League of Legends Tab scoreboard screenshot. Extract ALL data you can see into this exact format:

BLUE TEAM:
- [Champion] | Level [X] | [K/D/A] | [CS] CS | Items: [list items] | Summoners: [spell1, spell2]
(repeat for all 5)

RED TEAM:
- [Champion] | Level [X] | [K/D/A] | [CS] CS | Items: [list items] | Summoners: [spell1, spell2]
(repeat for all 5)

GAME TIME: [X:XX]
GOLD LEAD: [Blue/Red] ahead by ~[X]g (estimate from items)

Be precise. Read every number carefully. List every visible item including components."""


def _extract_json(text: str) -> dict:
    m = _JSON_RE.search(text)
    if not m:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    return json.loads(m.group())


class Analyzer:
    def __init__(self):
        api_key = OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("Set OPENAI_API_KEY environment variable.")
        self.client = OpenAI(api_key=api_key, timeout=API_TIMEOUT_SEC)
        self.last_result = copy.deepcopy(DEFAULT_RESPONSE)
        self.total_tokens = 0
        self.call_count = 0
        self._history: deque[dict] = deque(maxlen=MAX_CONTEXT_HISTORY)
        # Scoreboard stored as TEXT (cheap), not image (expensive)
        self._scoreboard_text: str | None = None
        self._scoreboard_time: float = 0

    def update_scoreboard(self, b64: str):
        """Send scoreboard image to LLM ONCE, extract text, store text forever."""
        print("[Analyzer] Parsing scoreboard...")
        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": SCOREBOARD_EXTRACT_PROMPT},
                    ],
                }],
                max_tokens=600,
                temperature=0.1,
            )

            self._scoreboard_text = response.choices[0].message.content.strip()
            self._scoreboard_time = time.time()

            if response.usage:
                self.total_tokens += response.usage.total_tokens

            print(f"[Analyzer] Scoreboard parsed — stored as text context")
            # Print first few lines for verification
            for line in self._scoreboard_text.split("\n")[:6]:
                print(f"  {line}")

        except Exception as e:
            print(f"[Analyzer] Scoreboard parse error: {e}")

    def _build_context(self) -> str:
        if not self._history:
            return ""
        lines = ["## Recent Context (oldest to newest)"]
        for entry in self._history:
            ago = entry["seconds_ago"]
            r = entry["result"]
            lines.append(f"\n~{ago}s ago:")
            for key in WIDGET_KEYS:
                if key in r:
                    lines.append(f"  {key}: {r[key].get('action', '?')} — "
                                 f"{r[key].get('reason', '')}")
        lines.append("\nTrack what changed between frames. Adjust advice accordingly.")
        return "\n".join(lines)

    def analyze(self, regions: dict[str, str]) -> dict:
        try:
            start = time.time()
            now = time.time()

            for entry in self._history:
                entry["seconds_ago"] = int(now - entry["timestamp"])
            context = self._build_context()

            # 3 game region images
            content: list[dict] = [
                {"type": "text", "text": "[MAIN — Lane/Gameplay View]"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{regions['main']}",
                        "detail": "high",
                    },
                },
                {"type": "text", "text": "[MINIMAP — Enemy Positions]"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{regions['minimap']}",
                        "detail": "high",
                    },
                },
                {"type": "text", "text": "[HUD — Stats, CS, Gold, Items, Clock]"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{regions['hud']}",
                        "detail": "high",
                    },
                },
            ]

            # Scoreboard as TEXT (not image) — almost free in tokens
            scoreboard_note = ""
            if self._scoreboard_text:
                age = int(now - self._scoreboard_time)
                scoreboard_note = (
                    f"\n\n## SCOREBOARD DATA (captured {age}s ago)\n"
                    f"{self._scoreboard_text}\n\n"
                    f"Use this data: compare CS to find leads, check items for powerspikes, "
                    f"identify which lanes are winning/losing."
                )

            user_text = (
                "Analyze these League of Legends game regions. "
                "Give specific advice for all 5 categories."
                + scoreboard_note
            )
            if context:
                user_text += f"\n\n{context}"

            content.append({"type": "text", "text": user_text})

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                max_tokens=500,
                temperature=0.3,
            )

            elapsed = time.time() - start
            raw = response.choices[0].message.content.strip()

            if response.usage:
                self.total_tokens += response.usage.total_tokens
            self.call_count += 1

            result = _extract_json(raw)

            for key in WIDGET_KEYS:
                if key not in result:
                    result[key] = copy.deepcopy(DEFAULT_RESPONSE[key])

            self._history.append({
                "timestamp": time.time(),
                "result": result,
                "seconds_ago": 0,
            })
            self.last_result = result

            sb = " +scoreboard" if self._scoreboard_text else ""
            print(f"[Analyzer] #{self.call_count} | {elapsed:.1f}s | "
                  f"{self.total_tokens} tokens{sb}")
            return result

        except json.JSONDecodeError as e:
            print(f"[Analyzer] JSON parse error: {e}")
            return self.last_result
        except Exception as e:
            print(f"[Analyzer] Error: {e}")
            return self.last_result

    def get_cost_estimate(self) -> float:
        return self.total_tokens * 0.0003 / 1000
