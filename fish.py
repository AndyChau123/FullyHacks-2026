# =============================================================
#  fish.py  —  Enemy fish entities
#
#  Fish class: single fish with configurable move_interval and
#  behavior type so depth-specific AI can be added later.
#
#  FishManager: spawns + drives all fish, exposes collision
#  helpers and EMP stun API.
# =============================================================

import random
import settings
from tile_types import TileType

_DIRS = [settings.NORTH, settings.EAST, settings.SOUTH, settings.WEST]

_DELTA = {
    settings.NORTH: ( 0, -1),
    settings.EAST:  ( 1,  0),
    settings.SOUTH: ( 0,  1),
    settings.WEST:  (-1,  0),
}

ARROW = {
    settings.NORTH: "^",
    settings.EAST:  ">",
    settings.SOUTH: "v",
    settings.WEST:  "<",
}


class Fish:
    """
    Single enemy fish.

    Parameters
    ----------
    move_interval : int
        The fish acts once every this many player actions.
        Change per depth or per fish type (e.g. boss fish = 1).
    behavior : str
        AI mode — "random" now; more added later ("chase", "patrol", …).
    """

    def __init__(self, x: int, y: int,
                 move_interval: int = 3,
                 behavior: str = "random"):
        self.x = x
        self.y = y
        self.move_interval  = move_interval
        self.behavior       = behavior
        self._action_count  = 0          # player actions since last fish move
        self.stun_remaining = 0          # player actions left while stunned
        self.next_dir       = random.choice(_DIRS)  # shown as arrow on radar

    # ----------------------------------------------------------
    #  Called once per player action
    # ----------------------------------------------------------

    def on_player_action(self, grid) -> bool:
        """Advance internal counter; move when interval reached.
        Returns True if the fish actually moved this tick."""
        if self.stun_remaining > 0:
            self.stun_remaining -= 1
            return False

        self._action_count += 1
        if self._action_count < self.move_interval:
            return False

        self._action_count = 0
        self._move(grid)
        return True

    # ----------------------------------------------------------
    #  Movement
    # ----------------------------------------------------------

    def _move(self, grid) -> None:
        """Attempt to move in next_dir; pick a new direction if blocked."""
        if self._try_dir(self.next_dir, grid):
            self._pick_next(grid)
            return

        dirs = _DIRS[:]
        random.shuffle(dirs)
        for d in dirs:
            if self._try_dir(d, grid):
                self._pick_next(grid)
                return

        # Completely boxed in — stay put but still refresh arrow
        self._pick_next(grid)

    def _try_dir(self, direction: int, grid) -> bool:
        dx, dy = _DELTA[direction]
        nx, ny = self.x + dx, self.y + dy
        tile = grid.get(nx, ny)
        if tile is None or tile == TileType.ROCK:
            return False
        self.x, self.y = nx, ny
        return True

    def _pick_next(self, grid) -> None:
        """Pre-select next direction for radar arrow. Override per behavior."""
        if self.behavior == "random":
            valid = [d for d in _DIRS if self._passable(d, grid)]
            self.next_dir = random.choice(valid) if valid else random.choice(_DIRS)

    def _passable(self, direction: int, grid) -> bool:
        dx, dy = _DELTA[direction]
        tile = grid.get(self.x + dx, self.y + dy)
        return tile is not None and tile != TileType.ROCK

    # ----------------------------------------------------------
    #  EMP stun
    # ----------------------------------------------------------

    def stun(self, duration: int) -> None:
        """Stun for `duration` player actions (EMP). Stacks up to the longer."""
        self.stun_remaining = max(self.stun_remaining, duration)

    # ----------------------------------------------------------
    #  Properties
    # ----------------------------------------------------------

    @property
    def arrow(self) -> str:
        return ARROW[self.next_dir]

    @property
    def is_stunned(self) -> bool:
        return self.stun_remaining > 0


class FishManager:
    """
    Manages all enemy fish for a single run.
    Built for extension: swap in new behavior strings or move_intervals
    per depth without touching this class.
    """

    def __init__(self):
        self.fish: list[Fish] = []

    # ----------------------------------------------------------
    #  Spawn
    # ----------------------------------------------------------

    def spawn(self, count: int, grid,
              spawn_x: int, spawn_y: int,
              move_interval: int = 3,
              behavior: str = "random") -> None:
        """
        Place `count` fish on random EMPTY tiles that are outside the
        FISH_SPAWN_EXCLUSION radius around (spawn_x, spawn_y).
        """
        self.fish.clear()
        excl = settings.FISH_SPAWN_EXCLUSION

        candidates = [
            (gx, gy)
            for gy in range(grid.height)
            for gx in range(grid.width)
            if not (abs(gx - spawn_x) <= excl and abs(gy - spawn_y) <= excl)
            and grid.get(gx, gy) == TileType.EMPTY
        ]

        random.shuffle(candidates)
        for gx, gy in candidates[:count]:
            self.fish.append(
                Fish(gx, gy, move_interval=move_interval, behavior=behavior)
            )

        print(f"[Fish] Spawned {len(self.fish)} fish "
              f"(interval={move_interval}, behavior={behavior})")

    # ----------------------------------------------------------
    #  Per-action update
    # ----------------------------------------------------------

    def on_player_action(self, grid) -> list[tuple[int, int]]:
        """
        Advance all fish by one player action.
        Returns the new (x, y) of every fish that moved this tick.
        """
        moved = []
        for f in self.fish:
            if f.on_player_action(grid):
                moved.append((f.x, f.y))
        return moved

    # ----------------------------------------------------------
    #  Collision
    # ----------------------------------------------------------

    def check_collision(self, px: int, py: int) -> bool:
        """True if any fish occupies tile (px, py)."""
        return any(f.x == px and f.y == py for f in self.fish)

    # ----------------------------------------------------------
    #  EMP helpers
    # ----------------------------------------------------------

    def stun_all(self, duration: int) -> None:
        for f in self.fish:
            f.stun(duration)

    def stun_radius(self, cx: int, cy: int, radius: int, duration: int) -> None:
        """Stun every fish within `radius` tiles (Chebyshev) of (cx, cy)."""
        for f in self.fish:
            if abs(f.x - cx) <= radius and abs(f.y - cy) <= radius:
                f.stun(duration)

    def fire_harpoon(self, px: int, py: int, direction: int, grid) -> bool:
        """
        Trace a ray from (px, py) in direction; remove the first fish hit.
        Stops at rocks or grid edges. Returns True if a fish was killed.
        """
        dx, dy = _DELTA[direction]
        x, y   = px + dx, py + dy
        while True:
            tile = grid.get(x, y)
            if tile is None or tile == TileType.ROCK:
                break
            for i, f in enumerate(self.fish):
                if f.x == x and f.y == y:
                    self.fish.pop(i)
                    return True
            x += dx
            y += dy
        return False

    # ----------------------------------------------------------
    #  Convenience
    # ----------------------------------------------------------

    @property
    def positions(self) -> list[tuple[int, int]]:
        return [(f.x, f.y) for f in self.fish]
