# =============================================================
#  player.py  —  Player state and movement
#
#  Responsibilities:
#    - Tracks grid position (x, y) and facing direction
#    - rotate(dir)        — turn left (-1) or right (+1)
#    - move_forward()     — step one tile in the facing direction
#    - Enforces grid boundaries and blocked-tile collision
#    - Reports what just happened (moved, blocked, rotated)
#
#  No Pygame input here — Game handles events and calls these.
# =============================================================

import settings
from grid import Grid, FORWARD
from tile_types import BLOCKED_TILES


class MoveResult:
    """Simple result object returned by move_forward()."""
    MOVED   = "moved"
    BLOCKED = "blocked"   # tile is a BLOCKED type (rock, wall)
    EDGE    = "edge"      # would leave the grid boundary


class Player:
    """
    Represents the player submarine on the grid.

    Attributes
    ----------
    x, y    : current grid cell (column, row)
    facing  : int  0=N  1=E  2=S  3=W  (matches settings constants)
    """

    def __init__(self, x: int, y: int, facing: int = settings.NORTH):
        self.x      = x
        self.y      = y
        self.facing = facing
        print(f"[Player] Spawned at ({x}, {y}) "
              f"facing {settings.FACING_LABEL[facing]}")

    # ----------------------------------------------------------
    #  Rotation
    # ----------------------------------------------------------

    def rotate(self, direction: int) -> None:
        """
        Rotate the player's facing direction.

        Parameters
        ----------
        direction : -1 = rotate left (counter-clockwise)
                    +1 = rotate right (clockwise)
        """
        self.facing = (self.facing + direction) % 4
        label = settings.FACING_LABEL[self.facing]
        turn  = "left" if direction == -1 else "right"
        print(f"[Player] Rotated {turn} → now facing {label}")

    # ----------------------------------------------------------
    #  Forward movement
    # ----------------------------------------------------------

    def move_forward(self, grid: Grid) -> str:
        """
        Attempt to move one tile in the current facing direction.

        Parameters
        ----------
        grid : the Grid instance used for boundary and block checks

        Returns
        -------
        MoveResult.MOVED   — success, position updated
        MoveResult.BLOCKED — tile ahead is impassable
        MoveResult.EDGE    — would move off the grid
        """
        dx, dy   = FORWARD[self.facing]
        target_x = self.x + dx
        target_y = self.y + dy

        # 1. Boundary check
        if not grid.in_bounds(target_x, target_y):
            print(f"[Player] Can't move — grid edge")
            return MoveResult.EDGE

        # 2. Blocked tile check
        if grid.is_blocked(target_x, target_y):
            tile = grid.get(target_x, target_y)
            print(f"[Player] Can't move — {tile.name} at "
                  f"({target_x}, {target_y})")
            return MoveResult.BLOCKED

        # 3. Move
        self.x = target_x
        self.y = target_y
        print(f"[Player] Moved to ({self.x}, {self.y})")
        return MoveResult.MOVED

    # ----------------------------------------------------------
    #  Convenience properties
    # ----------------------------------------------------------

    @property
    def facing_label(self) -> str:
        return settings.FACING_LABEL[self.facing]

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)

    def __repr__(self) -> str:
        return (f"Player(pos=({self.x},{self.y}), "
                f"facing={self.facing_label})")