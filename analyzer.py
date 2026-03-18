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
    "alert": {"action": "Starting up", "reason": "First analysis incoming.", "urgency": "low"},
}

MAX_CONTEXT_HISTORY = 4
API_TIMEOUT_SEC = 15

# Regex to extract JSON object from model output (handles code fences, preamble text, etc.)
_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _extract_json(text: str) -> dict:
    """Extract and parse JSON from model output, handling code fences and extra text."""
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

    def _build_context(self) -> str:
        if not self._history:
            return ""
        lines = ["## Recent Context (oldest → newest)"]
        for entry in self._history:
            ago = entry["seconds_ago"]
            r = entry["result"]
            lines.append(f"\n~{ago}s ago:")
            for key in ("lane", "macro", "alert"):
                if key in r:
                    lines.append(f"  {key}: {r[key].get('action', '?')} — "
                                 f"{r[key].get('reason', '')}")
        lines.append("\nUse this to track changes: did the wave move? "
                     "Did the jungler show? Adjust advice accordingly.")
        return "\n".join(lines)

    def analyze(self, screenshot_b64: str) -> dict:
        try:
            start = time.time()

            now = time.time()
            for entry in self._history:
                entry["seconds_ago"] = int(now - entry["timestamp"])
            context = self._build_context()

            user_text = "Analyze this League of Legends screenshot."
            if context:
                user_text += f"\n\n{context}"

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{screenshot_b64}",
                                    "detail": "low",
                                },
                            },
                            {"type": "text", "text": user_text},
                        ],
                    },
                ],
                max_tokens=350,
                temperature=0.3,
            )

            elapsed = time.time() - start
            raw = response.choices[0].message.content.strip()

            if response.usage:
                self.total_tokens += response.usage.total_tokens
            self.call_count += 1

            result = _extract_json(raw)

            for key in ("lane", "macro", "alert"):
                if key not in result:
                    result[key] = copy.deepcopy(DEFAULT_RESPONSE[key])

            self._history.append({
                "timestamp": time.time(),
                "result": result,
                "seconds_ago": 0,
            })
            self.last_result = result
            print(f"[Analyzer] #{self.call_count} | {elapsed:.1f}s | "
                  f"{self.total_tokens} tokens")
            return result

        except json.JSONDecodeError as e:
            print(f"[Analyzer] JSON parse error: {e}")
            return self.last_result
        except Exception as e:
            print(f"[Analyzer] Error: {e}")
            return self.last_result

    def get_cost_estimate(self) -> float:
        return self.total_tokens * 0.0003 / 1000
