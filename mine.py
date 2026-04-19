# =============================================================
#  mine.py  —  Naval Mine entities
#
#  Mines spawn on depth 3 & 4.  They are dormant until the
#  player enters their 3×3 detection radius, then count down
#  MINE_COUNTDOWN player actions before detonating in a 3×3
#  blast.  The blast destroys rocks, treasures, kills fish,
#  and kills the player.
#
#  EMP stun extends a mine's countdown.
#  A harpoon shot that hits a mine detonates it immediately.
# =============================================================

import random
import settings
from tile_types import TileType


class Mine:
    def __init__(self, x: int, y: int):
        self.x         = x
        self.y         = y
        self.countdown = settings.MINE_COUNTDOWN
        self.triggered = False

    def check_in_range(self, px: int, py: int) -> bool:
        """True if (px,py) is within the 3×3 trigger area (Chebyshev ≤ 1)."""
        return (abs(self.x - px) <= settings.MINE_TRIGGER_RADIUS and
                abs(self.y - py) <= settings.MINE_TRIGGER_RADIUS)

    def on_player_action(self) -> bool:
        """Advance countdown (only when triggered). Returns True when it hits 0."""
        if not self.triggered:
            return False
        self.countdown -= 1
        return self.countdown <= 0

    def extend_countdown(self, amount: int) -> None:
        self.countdown += amount


class MineManager:
    """Manages all naval mines for a single run."""

    def __init__(self):
        self.mines: list[Mine] = []

    # ----------------------------------------------------------
    #  Spawn
    # ----------------------------------------------------------

    def spawn(self, count: int, grid, spawn_x: int, spawn_y: int) -> None:
        self.mines.clear()
        excl = settings.MINE_SPAWN_EXCLUSION
        candidates = [
            (gx, gy)
            for gy in range(grid.height)
            for gx in range(grid.width)
            if not (abs(gx - spawn_x) <= excl and abs(gy - spawn_y) <= excl)
            and grid.get(gx, gy) == TileType.EMPTY
        ]
        random.shuffle(candidates)
        for gx, gy in candidates[:count]:
            self.mines.append(Mine(gx, gy))
        print(f"[Mines] Spawned {len(self.mines)} naval mines")

    # ----------------------------------------------------------
    #  Per-action update
    # ----------------------------------------------------------

    def on_player_action(self, px: int, py: int, grid,
                          fish_manager) -> list[dict]:
        """
        1. Trigger dormant mines the player has entered.
        2. Advance triggered mine countdowns.
        3. Detonate any that hit 0.
        4. Destroy other mines caught in blasts (no chain-detonation).
        Returns list of explosion dicts: {cx, cy, killed_player}.
        """
        for mine in self.mines:
            if not mine.triggered and mine.check_in_range(px, py):
                mine.triggered = True
                print(f"[Mine] Mine at ({mine.x},{mine.y}) triggered! "
                      f"T-{mine.countdown}")

        to_detonate, remaining = [], []
        for mine in self.mines:
            (to_detonate if mine.on_player_action() else remaining).append(mine)
        self.mines = remaining

        explosions: list[dict] = []
        for mine in to_detonate:
            self._explode(mine, grid, fish_manager, px, py, explosions)

        self._cull_mines_in_blasts(explosions)
        return explosions

    # ----------------------------------------------------------
    #  Harpoon detonation
    # ----------------------------------------------------------

    def explode_mine(self, mine: Mine, grid, fish_manager,
                     px: int, py: int) -> list[dict]:
        """Immediately detonate a specific mine (harpoon hit)."""
        if mine not in self.mines:
            return []
        self.mines.remove(mine)
        explosions: list[dict] = []
        self._explode(mine, grid, fish_manager, px, py, explosions)
        self._cull_mines_in_blasts(explosions)
        return explosions

    # ----------------------------------------------------------
    #  EMP
    # ----------------------------------------------------------

    def emp_extend(self, cx: int, cy: int, radius: int, amount: int) -> int:
        """Extend countdown of every mine within Chebyshev `radius`. Returns count."""
        count = 0
        for mine in self.mines:
            if abs(mine.x - cx) <= radius and abs(mine.y - cy) <= radius:
                mine.extend_countdown(amount)
                count += 1
        return count

    # ----------------------------------------------------------
    #  Query
    # ----------------------------------------------------------

    def get_mine_at(self, x: int, y: int) -> Mine | None:
        for m in self.mines:
            if m.x == x and m.y == y:
                return m
        return None

    @property
    def positions(self) -> list[tuple[int, int]]:
        return [(m.x, m.y) for m in self.mines]

    # ----------------------------------------------------------
    #  Internal helpers
    # ----------------------------------------------------------

    def _explode(self, mine: Mine, grid, fish_manager,
                 px: int, py: int, out: list) -> None:
        cx, cy = mine.x, mine.y
        r      = settings.MINE_EXPLOSION_RADIUS
        print(f"[Mine] BOOM at ({cx},{cy})!")

        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                tile = grid.get(cx + dx, cy + dy)
                if tile in (TileType.ROCK, TileType.TREASURE):
                    grid.set(cx + dx, cy + dy, TileType.EMPTY)

        fish_manager.fish = [
            f for f in fish_manager.fish
            if not (abs(f.x - cx) <= r and abs(f.y - cy) <= r)
        ]
        out.append({
            "cx":           cx,
            "cy":           cy,
            "killed_player": abs(px - cx) <= r and abs(py - cy) <= r,
        })

    def _cull_mines_in_blasts(self, explosions: list[dict]) -> None:
        if not explosions:
            return
        r = settings.MINE_EXPLOSION_RADIUS
        self.mines = [
            m for m in self.mines
            if not any(abs(m.x - e["cx"]) <= r and abs(m.y - e["cy"]) <= r
                       for e in explosions)
        ]
