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

# ----- Tile image display scale ------------------------------
# Fraction of each slot's dimensions used as the max image size.
# load_image_fit preserves aspect ratio; the image is centred in the slot.
TILE_IMG_SCALE_CENTER = 0.68   # center slot (closest — largest image)
TILE_IMG_SCALE_SIDE   = 0.55   # left/right slots (further — smaller image)
# How far down (0.0–1.0) within the slot the tile image is placed.
# 0.5 = true centre, higher values push the image toward the bottom.
TILE_VERTICAL_BIAS    = 0.72   # push tiles toward the lower portion of each slot

# ----- Tile viewport — matches the transparent window areas of frame.png ---
# frame.png is 2360×1640; scaled to 1024×768 (x_scale≈0.434, y_scale≈0.468).
# Three windows: left side, centre, right side separated by pillars at ~34% / ~66%.
# Bottom floor starts at ~70% of height.  Top bar ~3.7% of height.
TILE_VIEWPORT_X      = 0     # full-width viewport; frame masks non-window areas
TILE_VIEWPORT_Y      = 28    # below the top dark bar of the frame
TILE_VIEWPORT_WIDTH  = 1024  # full screen width
TILE_VIEWPORT_HEIGHT = 450   # above the bottom floor of the frame

# ----- Slot regions (relative to TILE_VIEWPORT_X) ----------
# Pillars are at roughly x=347 and x=677 at 1024-wide scale.
SLOT_LEFT_X      = 0
SLOT_LEFT_W      = 347
SLOT_CENTER_X    = 347
SLOT_CENTER_W    = 330
SLOT_RIGHT_X     = 677
SLOT_RIGHT_W     = 347

# ----- Ocean background assets (depth-specific) -------------
BG_SHALLOW = "bg_shallow.png"   # Depths 1 & 2
BG_DEEP    = "bg_deep.png"      # Depths 3 & 4
DEPTH_SELECT_BG = "depth_select.png"  # menu screen background

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

# ----- Game structure ----------------------------------------
RUNS_PER_GAME = 5    # extractions needed to complete one full game

# ----- Shop items --------------------------------------------
# Flags:
#   resets_per_run  — item count in save zeroes at the start of each run
#   game_scoped_max — max_count enforced per game (not per-save total)
#   dynamic_price   — price computed from BATTERY_PACK_PRICE_INCREMENT
BATTERY_PACK_BASE_PRICE      = 150
BATTERY_PACK_PRICE_INCREMENT =  50   # +50 shuckles for each subsequent buy per game

SHOP_ITEMS = [
    {
        "id":             "harpoons",
        "name":           "Harpoon",
        "price":          100,
        "max_count":      3,
        "description":    "Strike your enemies from afar but beware you may miss",
        "asset":          "item_harpoon.png",
        "resets_per_run": False,
        "game_scoped_max": False,
        "dynamic_price":  False,
    },
    {
        "id":                 "emp_stun",
        "name":               "EMP Stun",
        "price":              500,
        "max_count":          1,
        "description":        "Stun enemies for 3 actions and extend nearby mine timers. Costs 20 energy. Auto-refills each run.",
        "asset":              "item_emp.png",
        "resets_per_run":     False,
        "game_scoped_max":    False,
        "dynamic_price":      False,
        "auto_refill_per_run": True,   # once bought: 1 charge auto-restored each run
    },
    {
        "id":             "romo_rescue",
        "name":           "Romo's Rescue",
        "price":          1500,
        "max_count":      1,
        "description":    "Call upon Romo to rescue you from the depths. Use wherever to extract instantly.",
        "asset":          "item_romo.png",
        "resets_per_run": False,
        "game_scoped_max": True,   # max 1 per game, not per run
        "dynamic_price":  False,
    },
    {
        "id":             "battery_pack",
        "name":           "Battery Pack",
        "price":          BATTERY_PACK_BASE_PRICE,
        "max_count":      99,      # effectively unlimited; price scaling is the limiter
        "description":    "Recharge your packs. Restores 100% of energy.",
        "asset":          "item_battery.png",
        "resets_per_run": True,    # count zeroes at run start; price keeps accumulating
        "game_scoped_max": False,
        "dynamic_price":  True,
    },
]

# ----- Scanner Upgrade in-game behaviour --------------------
SCAN_UPGRADE_USES        = 3    # uses granted per shop purchase
SCAN_UPGRADE_GRID        = 5    # 5×5 visual radar during enhanced scan
SCAN_UPGRADE_DURATION    = 3    # player actions the enhanced scan lasts
SCAN_UPGRADE_ENERGY_COST = 20   # energy cost for the enhanced (upgraded) scan
SCAN_BASE_RANGE          = 2    # Chebyshev radius for base-scan text readout (covers 5×5)

# ----- Scoring -----------------------------------------------
HARPOON_KILL_SCORE = 500   # score for killing a fish with a harpoon
DEPTH_CLEAR_SCORE  = {     # bonus score awarded on successful extraction per depth
    "Depth 1": 100,
    "Depth 2": 200,
    "Depth 3": 400,
    "Depth 4": 800,
}
SHUCKLE_SCORE_RATE = 1     # shuckles → score at end of game (1:1)

# ----- Energy Upgrade tiers ----------------------------------
ENERGY_UPGRADE_TIERS = [
    {"tier": 1, "price": 500, "reduction": 0.10},
    {"tier": 2, "price": 700, "reduction": 0.20},
    {"tier": 3, "price": 900, "reduction": 0.30},
]

# ----- Shop upgrades (persistent across runs) ----------------
SHOP_UPGRADES = [
    {
        "id":           "scanner_upgrade",
        "name":         "Scanner Upgrade",
        "price":        600,
        "description":  "Upgrade scanner to 5×5 visual grid for 3 actions. "
                        "Costs 20 energy (vs 10 base). 3 uses before repurchase.",
        "asset":        "upgrade_scanner.png",
        "upgrade_type": "consumable_uses",   # repurchasable when uses hit 0
    },
    {
        "id":           "energy_upgrade",
        "name":         "Energy Upgrade",
        "description":  "Increase efficiency of your system.",
        "asset":        "upgrade_energy.png",
        "upgrade_type": "tiered",            # 3-tier permanent progression
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

# In-game action buttons
BTN_ASSET_EXTRACT = "btn_extract.png"
BTN_ASSET_SCAN    = "btn_scan.png"

# Menu action buttons (menu.py)
BTN_ASSET_PLAY       = "btn_play.png"
BTN_ASSET_PLAY_HOVER = "btn_play_hover.png"
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
    "rock":        "radar_rock.png",
    "treasure":    "radar_treasure.png",
    "empty":       "radar_empty.png",
    "player_n":    "radar_player_n.png",
    "player_e":    "radar_player_e.png",
    "player_s":    "radar_player_s.png",
    "player_w":    "radar_player_w.png",
    "fish":        "radar_fish.png",
    "fish_stun":   "radar_fish_stun.png",
    "mine":        "radar_mine.png",        # dormant mine
    "mine_trig":   "radar_mine_trig.png",   # triggered (counting down)
}

# ----- Enemy Fish --------------------------------------------
# Exclusion zone: fish cannot spawn within this many tiles of the player spawn
# (2 → a 5×5 square centered on spawn is off-limits)
FISH_SPAWN_EXCLUSION = 2

# Fish count per depth
FISH_COUNT = {
    "Depth 1": 2,
    "Depth 2": 2,
    "Depth 3": 3,
    "Depth 4": 3,
}

# Player actions between each fish act (lower = faster)
FISH_MOVE_INTERVAL = {
    "Depth 1": 3,
    "Depth 2": 3,
    "Depth 3": 2,
    "Depth 4": 2,
}

# Fish AI behavior per depth
# "random" — completely random turning and movement
# "chase"  — tracks player when within FISH_CHASE_RADIUS tiles
FISH_BEHAVIOR = {
    "Depth 1": "random",
    "Depth 2": "chase",
    "Depth 3": "chase",
    "Depth 4": "chase",
}

# Chebyshev radius for chase detection per depth
# radius 2 = 5×5 area, radius 3 = 7×7 area
FISH_CHASE_RADIUS = {
    "Depth 1": 2,
    "Depth 2": 2,
    "Depth 3": 2,
    "Depth 4": 4,
}

# EMP stun
EMP_STUN_DURATION = 3    # player actions fish are frozen
EMP_ENERGY_COST   = 20   # energy deducted when EMP is used (reduced by energy upgrade)
EMP_MINE_EXTEND   = 4    # actions added to a mine's countdown when hit by EMP

# ----- Naval Mines -------------------------------------------
MINE_COUNTDOWN        = 5   # player actions after trigger before detonation
MINE_TRIGGER_RADIUS   = 1   # Chebyshev radius that activates the countdown (3×3 area)
MINE_EXPLOSION_RADIUS = 1   # Chebyshev blast radius (3×3 area)
MINE_SPAWN_EXCLUSION  = 3   # mines won't spawn within this many tiles of player spawn

# Mine count per depth (depths 1 & 2 have none)
MINE_COUNT = {
    "Depth 1": 0,
    "Depth 2": 0,
    "Depth 3": 3,
    "Depth 4": 5,
}