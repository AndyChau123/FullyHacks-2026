# =============================================================
#  settings.py  —  Submarine Game Global Configuration
#  Change values here and they ripple through the whole project
# =============================================================

# ----- Display -----------------------------------------------
SCREEN_WIDTH  = 1024
SCREEN_HEIGHT = 768
FPS           = 60
WINDOW_TITLE  = "Deep Dive"

# ----- Grid --------------------------------------------------
GRID_WIDTH    = 10   # columns  (default / fallback)
GRID_HEIGHT   = 10   # rows

# Difficulty depths  (label → (width, height))
DEPTHS = {
    "Depth 1": (10, 10),
    "Depth 2": (15, 15),
    "Depth 3": (25, 25),
    "Depth 4": (40, 40),
}

# ----- Facing directions (used by Player and Grid) -----------
NORTH = 0
EAST  = 1
SOUTH = 2
WEST  = 3
FACING_LABEL = {NORTH: "N", EAST: "E", SOUTH: "S", WEST: "W"}

# ----- Tile viewport (the "porthole" inside your HUD image) --
# Adjust these to match where the ocean window sits in your HUD art.
# (x, y) = top-left corner of the window region, in screen pixels.
TILE_VIEWPORT_X      = 112
TILE_VIEWPORT_Y      = 80
TILE_VIEWPORT_WIDTH  = 800
TILE_VIEWPORT_HEIGHT = 500

# ----- Slot regions inside the viewport ----------------------
# The viewport is split into LEFT / CENTER / RIGHT thirds.
# CENTER is wider (perspective depth illusion — closer = bigger).
# Tweak these once your HUD art is in place.
SLOT_LEFT_X      = 0      # relative to TILE_VIEWPORT_X
SLOT_LEFT_W      = 230
SLOT_CENTER_X    = 230
SLOT_CENTER_W    = 340
SLOT_RIGHT_X     = 570
SLOT_RIGHT_W     = 230

# ----- Asset paths -------------------------------------------
import os

BASE_DIR    = os.path.dirname(__file__)
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
IMAGES_DIR  = os.path.join(ASSETS_DIR, "images")   # HUD, misc images
TILES_DIR   = os.path.join(ASSETS_DIR, "tiles")    # per-tile backgrounds
UI_DIR      = os.path.join(ASSETS_DIR, "ui")       # buttons, icons

# ----- Colours (R, G, B) — fallbacks when images are missing -
BLACK        = (0,   0,   0)
WHITE        = (255, 255, 255)
DARK_BLUE    = (5,   15,  40)
OCEAN_BLUE   = (10,  40,  80)
HUD_GREEN          = (0,   200, 100)
TREASURE_HIGHLIGHT = (255, 215,   0)   # gold hover border on treasure tiles

# ----- Radar (bottom-right minimap) -------------------------
RADAR_CELL_SIZE = 36     # pixels per cell (3×3 grid = 108×108 total)
RADAR_PADDING   = 12     # gap from screen edges

# ----- Energy bar (bottom-left) ------------------------------
ENERGY_MAX            = 100
ENERGY_BAR_W          = 80    # battery image width  (px)
ENERGY_BAR_H          = 60    # battery image height (px)
ENERGY_BAR_X          = 12    # left edge padding
ENERGY_HIGH_THRESHOLD = 60    # energy % >= this → battery_high.png
ENERGY_MID_THRESHOLD  = 30    # energy % >= this → battery_mid.png  (below → battery_low.png)

# ----- Scan button (centred, below direction buttons) --------
SCAN_ENERGY_COST    = 10   # energy deducted per scan
SCAN_DURATION_MOVES = 3    # how many player actions the 5×5 radar lasts
SCAN_BTN_W          = 220
SCAN_BTN_H          = 40
SCAN_BTN_BOTTOM_PAD = 20   # gap from screen bottom edge

# ----- Extract button (appears at spawn tile) ----------------
EXTRACT_BTN_W = 280
EXTRACT_BTN_H = 50

# ----- Movement ----------------------------------------------
ACTION_ENERGY_COST = 1    # energy deducted per move or rotate
MOVE_COOLDOWN_MS   = 200  # milliseconds between moves when key held