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

# Shuckle multiplier per depth
DEPTH_MULTIPLIERS = {
    "Depth 1": 1.0,
    "Depth 2": 1.25,
    "Depth 3": 2.0,
    "Depth 4": 2.5,
}

# Shuckle value range per treasure (before multiplier)
TREASURE_MIN_VALUE = 10
TREASURE_MAX_VALUE = 100

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

# ----- Shop items --------------------------------------------
SHOP_ITEMS = [
    {
        "id":          "harpoons",
        "name":        "Harpoon",
        "price":       50,
        "max_count":   3,
        "description": "Strike your enemies from afar but beware you may miss",
        "asset":       "item_harpoon.png",
    },
    {
        "id":          "emp_stun",
        "name":        "EMP Stun",
        "price":       100,
        "max_count":   1,
        "description": "Take control of your surroundings by stunning in a 3x3 radius around the user.",
        "asset":       "item_emp.png",
    },
]

# ----- Extract button (appears at spawn tile) ----------------
EXTRACT_BTN_W = 280
EXTRACT_BTN_H = 50

# ----- Movement ----------------------------------------------
ACTION_ENERGY_COST = 1    # energy deducted per move or rotate
MOVE_COOLDOWN_MS   = 200  # milliseconds between moves when key held

# ----- Button asset names (place PNGs in assets/ui/) ---------
# Control buttons (ui_buttons.py)
BTN_ASSET_LEFT    = "btn_left.png"
BTN_ASSET_FORWARD = "btn_forward.png"
BTN_ASSET_RIGHT   = "btn_right.png"

# Menu action buttons (menu.py)
BTN_ASSET_PLAY    = "btn_play.png"
BTN_ASSET_SHOP    = "btn_shop.png"

# Menu depth-selector buttons — keyed by depth label
BTN_ASSET_DEPTH = {
    "Depth 1": "btn_depth_1.png",
    "Depth 2": "btn_depth_2.png",
    "Depth 3": "btn_depth_3.png",
    "Depth 4": "btn_depth_4.png",
}

# ----- Shop asset names --------------------------------------
SHOP_BG_ASSET   = "shop_bg.png"      # full-screen shop background
SHOP_CARD_ASSET = "shop_card.png"    # card frame (220×350, tiled per card)

# ----- Radar icon names (place PNGs in assets/ui/) -----------
# One icon per cell type; if the file is missing the text label is used instead.
RADAR_ICONS = {
    "rock":       "radar_rock.png",
    "treasure":   "radar_treasure.png",
    "empty":      "radar_empty.png",
    "player_n":   "radar_player_n.png",
    "player_e":   "radar_player_e.png",
    "player_s":   "radar_player_s.png",
    "player_w":   "radar_player_w.png",
    "fish":       "radar_fish.png",
    "fish_stun":  "radar_fish_stun.png",
}

# ----- Enemy Fish --------------------------------------------
# Exclusion zone: fish cannot spawn within this many tiles of the player spawn
# (2 → a 5×5 square centered on spawn is off-limits)
FISH_SPAWN_EXCLUSION = 2

# Fish count per depth
FISH_COUNT = {
    "Depth 1": 2,
    "Depth 2": 3,
    "Depth 3": 5,
    "Depth 4": 8,
}

# Player actions between each fish move (lower = faster)
FISH_MOVE_INTERVAL = {
    "Depth 1": 3,
    "Depth 2": 3,
    "Depth 3": 2,
    "Depth 4": 2,
}

# EMP stun: how many player actions fish are frozen
EMP_STUN_DURATION = 9