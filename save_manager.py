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
    "total_score":         0,
    "runs_completed":      0,
    "shuckles":            0,
    # Inventory items
    "harpoons":            0,
    "emp_stun":            0,
    "emp_ever_bought":     0,   # 1 once EMP purchased; charge auto-refills each run
    "romo_rescue":         0,
    "battery_pack":        0,
    # Game-session state (resets after RUNS_PER_GAME extractions)
    "game_runs_done":      0,   # completed extractions this game
    "game_battery_bought": 0,   # total battery packs bought this game (price scaling)
    "game_romo_bought":    0,   # 0 or 1 — purchased Romo's Rescue this game
    # Persistent upgrades (survive across full games until save reset)
    "energy_upgrade_tier":  0,  # 0=none, 1/2/3
    "scanner_upgrade_uses": 0,  # remaining uses (0 = needs repurchase)
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
