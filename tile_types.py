# =============================================================
#  tile_types.py  —  All tile definitions and their asset maps
#
#  To add a new tile type:
#    1. Add a member to TileType
#    2. Add its image filename to TILE_ASSETS
#    3. Optionally mark it blocked in BLOCKED_TILES
# =============================================================

from enum import Enum, auto


class TileType(Enum):
    EMPTY    = auto()   # open water — nothing rendered over HUD
    ROCK     = auto()   # impassable rock formation
    TREASURE = auto()   # collectible treasure chest


# --------------------------------------------------------------
#  Which tile types block movement?
#  The player cannot move forward into a BLOCKED tile.
# --------------------------------------------------------------
BLOCKED_TILES: set[TileType] = {
    TileType.ROCK,
}


# --------------------------------------------------------------
#  Maps each TileType to an image filename inside assets/tiles/
#  EMPTY maps to None — nothing is blitted; the HUD shows through.
# --------------------------------------------------------------
TILE_ASSETS: dict[TileType, str | None] = {
    TileType.EMPTY:    None,
    TileType.ROCK:     "rock.png",
    TileType.TREASURE: "treasure.png",
}


# --------------------------------------------------------------
#  Spawn weights used during random grid generation.
#  Higher number = more likely to appear.
#  EMPTY should always dominate so the grid feels open.
# --------------------------------------------------------------
TILE_WEIGHTS: dict[TileType, int] = {
    TileType.EMPTY:    70,
    TileType.ROCK:     20,
    TileType.TREASURE: 10,
}