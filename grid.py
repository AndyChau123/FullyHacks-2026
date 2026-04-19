# =============================================================
#  grid.py  —  Grid data layer
#
#  Responsibilities:
#    - Holds the 2D list of TileType values
#    - Generates the map randomly on startup
#    - Answers queries: what tile is at (x,y)? is (x,y) blocked?
#    - Computes the 3-tile forward view for the renderer
#    - Picks a valid player spawn position
#
#  This module is pure data — no Pygame, no drawing.
# =============================================================

import random
from tile_types import TileType, TILE_ASSETS, TILE_WEIGHTS, BLOCKED_TILES
import settings


# --------------------------------------------------------------
#  Direction vectors
#  Index matches Player.facing:  0=North 1=East 2=South 3=West
# --------------------------------------------------------------
#  forward (dx, dy) for each facing
FORWARD = [
    (0, -1),   # North  — y decreases (up on grid)
    (1,  0),   # East
    (0,  1),   # South
    (-1, 0),   # West
]

#  right-perpendicular for each facing
#  (used to find the LEFT and RIGHT view tiles)
PERP_RIGHT = [
    (1,  0),   # facing North → right is East
    (0,  1),   # facing East  → right is South
    (-1, 0),   # facing South → right is West
    (0, -1),   # facing West  → right is North
]


class ViewSlice:
    """
    The three tiles the player can see from their current position.
    Passed to the renderer so it knows what to draw on the HUD.

    Attributes
    ----------
    left, center, right         : TileType | None  (None = out-of-bounds)
    left_pos, center_pos, right_pos : (x, y) | None  grid coords of each tile
    """
    def __init__(self, left, center, right,
                 left_pos=None, center_pos=None, right_pos=None):
        self.left   = left
        self.center = center
        self.right  = right
        self.left_pos   = left_pos
        self.center_pos = center_pos
        self.right_pos  = right_pos

    def __repr__(self):
        return f"ViewSlice(L={self.left}, C={self.center}, R={self.right})"


class Grid:
    """
    The game map.

    Usage
    -----
        grid = Grid()               # uses settings.GRID_WIDTH / HEIGHT
        grid.generate(seed=42)      # fill with random tiles
        spawn_x, spawn_y = grid.find_spawn()

        tile = grid.get(3, 5)       # → TileType
        view = grid.get_view(px, py, facing)  # → ViewSlice
    """

    def __init__(self,
                 width:  int = settings.GRID_WIDTH,
                 height: int = settings.GRID_HEIGHT):
        self.width  = width
        self.height = height
        # Internal 2D list: self._cells[row][col]
        self._cells: list[list[TileType]] = [
            [TileType.EMPTY] * width for _ in range(height)
        ]

    # ----------------------------------------------------------
    #  Generation
    # ----------------------------------------------------------

    def generate(self, seed: int | None = None) -> None:
        """
        Fill the grid with randomly weighted tiles.

        Parameters
        ----------
        seed : optional int for reproducible maps (useful for testing)
        """
        rng = random.Random(seed)

        population = list(TILE_WEIGHTS.keys())
        weights    = [TILE_WEIGHTS[t] for t in population]

        for row in range(self.height):
            for col in range(self.width):
                self._cells[row][col] = rng.choices(population, weights)[0]

        print(f"[Grid] Generated {self.width}×{self.height} map "
              f"(seed={seed})")
        self._print_stats()

    def _print_stats(self) -> None:
        counts: dict[TileType, int] = {}
        for row in self._cells:
            for tile in row:
                counts[tile] = counts.get(tile, 0) + 1
        parts = [f"{t.name}={n}" for t, n in counts.items()]
        print(f"[Grid] Tile counts: {', '.join(parts)}")

    # ----------------------------------------------------------
    #  Querying
    # ----------------------------------------------------------

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x: int, y: int) -> TileType | None:
        """
        Return the TileType at (x, y), or None if out of bounds.
        x = column, y = row  (top-left is 0,0).
        """
        if not self.in_bounds(x, y):
            return None
        return self._cells[y][x]

    def set(self, x: int, y: int, tile: TileType) -> None:
        """Manually place a tile — useful for level scripting."""
        if self.in_bounds(x, y):
            self._cells[y][x] = tile

    def is_blocked(self, x: int, y: int) -> bool:
        """
        True if the tile blocks movement (wall, out-of-bounds, ROCK, etc.)
        """
        if not self.in_bounds(x, y):
            return True   # treat edges as walls
        return self._cells[y][x] in BLOCKED_TILES

    # ----------------------------------------------------------
    #  The 3-tile forward view  ← the heart of the game
    # ----------------------------------------------------------

    def get_view(self, player_x: int, player_y: int, facing: int) -> ViewSlice:
        """
        Return the three tiles directly in front of the player.

        Parameters
        ----------
        player_x, player_y : current player grid position
        facing             : 0=N  1=E  2=S  3=W

        Layout (from the player's perspective)
        ─────────────────────────────────────
          [ LEFT ]  [ CENTER ]  [ RIGHT ]
                       ↑
                    player

        Math
        ────
          forward  = FORWARD[facing]
          perp     = PERP_RIGHT[facing]   (points to the right)

          front    = player + forward
          center   = front
          right    = front + perp
          left     = front - perp
        """
        fdx, fdy = FORWARD[facing]
        pdx, pdy = PERP_RIGHT[facing]

        front_x = player_x + fdx
        front_y = player_y + fdy

        lx, ly = front_x - pdx, front_y - pdy
        cx, cy = front_x,       front_y
        rx, ry = front_x + pdx, front_y + pdy

        return ViewSlice(
            left=self.get(lx, ly),   left_pos=(lx, ly)   if self.in_bounds(lx, ly) else None,
            center=self.get(cx, cy), center_pos=(cx, cy) if self.in_bounds(cx, cy) else None,
            right=self.get(rx, ry),  right_pos=(rx, ry)  if self.in_bounds(rx, ry) else None,
        )

    # ----------------------------------------------------------
    #  Spawn selection
    # ----------------------------------------------------------

    def find_spawn(self, rng: random.Random | None = None) -> tuple[int, int]:
        """
        Pick a random EMPTY, unblocked tile as the player start.
        Tries random positions first; falls back to a linear scan
        if the map is very crowded.

        Returns (x, y) grid coordinates.
        """
        if rng is None:
            rng = random.Random()

        # Collect all valid spawn cells
        candidates = [
            (col, row)
            for row in range(self.height)
            for col in range(self.width)
            if self._cells[row][col] == TileType.EMPTY
        ]

        if candidates:
            return rng.choice(candidates)

        # Absolute fallback — just pick any in-bounds cell
        print("[Grid] WARNING: No empty spawn found — spawning at (0,0)")
        return (0, 0)

    # ----------------------------------------------------------
    #  Debug helpers
    # ----------------------------------------------------------

    def print_ascii(self, player_x: int = -1, player_y: int = -1) -> None:
        """Print a simple ASCII map to the console for debugging."""
        symbols = {
            TileType.EMPTY:    ".",
            TileType.ROCK:     "R",
            TileType.TREASURE: "T",
        }
        print(f"  " + " ".join(str(c % 10) for c in range(self.width)))
        for row in range(self.height):
            row_str = f"{row % 10} "
            for col in range(self.width):
                if col == player_x and row == player_y:
                    row_str += "@ "
                else:
                    row_str += symbols.get(self._cells[row][col], "?") + " "
            print(row_str)