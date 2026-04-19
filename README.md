# Deep Dive — Submarine Exploration Game

A top-down submarine exploration game built with Pygame. Navigate a procedurally generated ocean grid, collect treasure, survive enemy fish and naval mines, and extract before your energy runs out.

---

## Folder Structure

```
deep_dive/
├── main.py              ← entry point
├── game.py              ← main game loop & rendering
├── menu.py              ← main menu screen
├── shop.py              ← inter-run shop
├── settings.py          ← all constants & tunable values
├── save_manager.py      ← persistent save/load (JSON)
├── asset_loader.py      ← image loading with placeholder fallback
├── fish.py              ← enemy fish AI & manager
├── mine.py              ← naval mine system
│
└── assets/
    ├── images/
    │   ├── hud.png              ← submarine cockpit frame overlay
    │   ├── depth_select.png     ← main menu background
    │   ├── bg_shallow.png       ← ocean background for Depths 1 & 2
    │   └── bg_deep.png          ← ocean background for Depths 3 & 4
    ├── tiles/
    │   ├── rock.png             ← rock tile (Depths 1 & 2)
    │   ├── rock_deep.png        ← rock tile (Depths 3 & 4)
    │   └── treasure.png         ← treasure tile
    └── ui/
        ├── btn_play.png / btn_play_hover.png
        ├── btn_depth_1..4.png   ← depth selector buttons
        ├── btn_left/forward/right/extract/scan.png
        ├── item_harpoon/emp/romo/battery.png
        └── upgrade_scanner/energy.png
```

---

## Setup

```bash
pip install pygame
python main.py
```

---

## Gameplay Overview

### Depths
Select a depth from the main menu before each game. Deeper = bigger grid, more enemies, higher score multiplier.

| Depth   | Grid     | Fish | Mines | Multiplier |
|---------|----------|------|-------|------------|
| Depth 1 | 10 × 10  | 2    | 0     | 1.0×       |
| Depth 2 | 15 × 15  | 3    | 0     | 1.25×      |
| Depth 3 | 25 × 25  | 5    | 3     | 2.0×       |
| Depth 4 | 40 × 40  | 8    | 5     | 2.5×       |

### Controls
- **W / ↑** — move forward
- **A / ←** — rotate left
- **D / →** — rotate right
- **Scan button** — reveal nearby tile info (costs energy)
- **Extract button** — surface when standing on spawn tile
- Direction buttons also available on-screen (HUD)

### Energy
Every move or rotation costs 1 energy. Bumping into a rock or map edge costs **no energy**. Running out of energy while away from spawn = game over.

### Items (bought in the Shop between runs)
| Item | Effect |
|------|--------|
| Harpoon | Fire in facing direction — kills fish, detonates mines |
| EMP Stun | Stuns all fish for 3 actions; extends nearby mine timers. Costs 20 energy. Auto-refills each run once purchased. |
| Romo's Rescue | Instantly extract from anywhere (max 1 per game) |
| Battery Pack | Fully restores energy. Price increases each purchase. |

### Upgrades
| Upgrade | Effect |
|---------|--------|
| Scanner Upgrade | Upgrades scan to a 5×5 visual radar for 3 actions. 3 uses per purchase. |
| Energy Upgrade | Reduces energy cost of actions (3 tiers: 10% / 20% / 30%) |

### Naval Mines (Depths 3 & 4)
- Mines are dormant until the submarine enters their 3×3 trigger zone
- Once triggered, a countdown of 5 player actions begins — move away fast
- Detonation destroys everything in the 3×3 blast radius
- Harpoons detonate mines instantly; EMP extends their timers by 4 actions

---

## Score & Progression
- Collect treasure tiles for **shuckles** (in-game currency)
- Extract after each run to bank your score; 5 successful extractions complete a game
- Shuckles carry over to the Shop between runs
- Final score = depth clear bonuses + harpoon kills + shuckles earned

---

## Key Settings (`settings.py`)

| Setting | Default | What it controls |
|---------|---------|-----------------|
| `SCREEN_WIDTH / HEIGHT` | 1024 × 768 | Window size |
| `DEPTHS` | 4 presets | Grid sizes per depth |
| `TILE_VERTICAL_BIAS` | 0.72 | How far down tiles sit in viewport slots |
| `MOVE_COOLDOWN_MS` | 200 | Min ms between moves when key held |
| `FPS` | 60 | Frame rate cap |
| `RUNS_PER_GAME` | 5 | Extractions needed to complete a game |
| `MINE_COUNTDOWN` | 5 | Actions before mine detonates |
| `FISH_MOVE_INTERVAL` | 2–3 | Player actions between each fish move |
