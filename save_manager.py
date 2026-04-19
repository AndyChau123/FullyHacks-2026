# =============================================================
#  save_manager.py  —  Local save file (save.json)
#
#  Persistent data survives between sessions.
#  Call load() to read, save(data) to write, reset() to clear.
# =============================================================

import json
import os

SAVE_PATH = os.path.join(os.path.dirname(__file__), "save.json")

_DEFAULTS: dict = {
    "total_score":    0,
    "runs_completed": 0,
}


def load() -> dict:
    """Return save data, filling missing keys with defaults."""
    if os.path.exists(SAVE_PATH):
        try:
            with open(SAVE_PATH, "r") as f:
                data = json.load(f)
            for k, v in _DEFAULTS.items():
                data.setdefault(k, v)
            return data
        except (json.JSONDecodeError, OSError):
            pass   # corrupted file — fall through to defaults
    return dict(_DEFAULTS)


def save(data: dict) -> None:
    """Write data to save.json."""
    with open(SAVE_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[Save] Saved — total_score={data['total_score']}  "
          f"runs={data['runs_completed']}")


def reset() -> dict:
    """Overwrite save with defaults and return fresh data."""
    data = dict(_DEFAULTS)
    save(data)
    print("[Save] Save data reset.")
    return data
