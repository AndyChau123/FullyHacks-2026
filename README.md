# Submarine Game — Phase 1

## Folder structure

```
submarine_game/
│
├── main.py           ← run this
├── game.py           ← Game class & main loop
├── settings.py       ← all constants (screen size, grid, paths)
├── asset_loader.py   ← load_image(), load_hud(), load_tile()
│
└── assets/
    ├── images/
    │   └── hud.png          ← your submarine cockpit image (place here)
    ├── tiles/
    │   ├── ocean.png        ← tile background images (place here)
    │   ├── coral.png
    │   └── trench.png
    └── ui/
        └── (buttons, icons — Phase 3)
```

## Setup

```bash
pip install pygame
python main.py
```

## Adding your HUD image

1. Copy your submarine cockpit image into `assets/images/`
2. Rename it `hud.png` (or change `load_hud()` in `game.py`)
3. Open `settings.py` and adjust `TILE_VIEWPORT_*` values so the tile
   renders inside the correct "porthole" region of your HUD art.

## Adding tile images

Drop `.png` files into `assets/tiles/`. Phase 2 will wire them up to
tile types via a dictionary. For now, any missing image shows a
checkerboard placeholder so the game still runs.

## Key settings to adjust (`settings.py`)

| Setting | Default | What it controls |
|---|---|---|
| `SCREEN_WIDTH / HEIGHT` | 1024 × 768 | Window size |
| `GRID_WIDTH / HEIGHT` | 10 × 10 | Map size |
| `TILE_VIEWPORT_*` | 112, 80, 800, 500 | Where tile renders inside HUD |
| `MOVE_COOLDOWN_MS` | 200 | Min ms between moves |
| `FPS` | 60 | Frame rate cap |