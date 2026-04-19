# =============================================================
#  fish.py  —  Enemy fish entities
#
#  Fish move like the player: they must face a direction before
#  moving into it.  Each "act" tick does ONE of:
#    • turn one 90° step towards their desired direction, OR
#    • move forward (if already facing their desired direction)
#
#  Behaviors
#  ---------
#  "random" — picks a passable direction at random; holds it
#             until moved or blocked (Depth 1).
#  "chase"  — re-evaluates target towards the player every tick
#             when the player is within FISH_CHASE_RADIUS tiles;
#             otherwise behaves randomly (Depths 2–4).
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
    behavior : str
        AI mode — "random" or "chase".
    """

    def __init__(self, x: int, y: int,
                 move_interval: int = 3,
                 behavior: str = "random",
                 chase_radius: int = 2):
        self.x             = x
        self.y             = y
        self.facing        = random.choice(_DIRS)
        self.desired_dir   = random.choice(_DIRS)
        self.move_interval  = move_interval
        self.behavior       = behavior
        self.chase_radius   = chase_radius
        self._action_count  = 0
        self.stun_remaining = 0

    # ----------------------------------------------------------
    #  Called once per player action
    # ----------------------------------------------------------

    def on_player_action(self, grid,
                         player_x: int = 0, player_y: int = 0) -> bool:
        """Advance internal counter; act when interval is reached.
        Returns True if the fish took an action this tick."""
        if self.stun_remaining > 0:
            self.stun_remaining -= 1
            return False

        self._action_count += 1
        if self._action_count < self.move_interval:
            return False

        self._action_count = 0
        self._act(grid, player_x, player_y)
        return True

    # ----------------------------------------------------------
    #  Act: one turn OR one move
    # ----------------------------------------------------------

    def _act(self, grid, player_x: int, player_y: int) -> None:
        # Chase fish re-evaluate their target every act tick
        if self.behavior == "chase":
            r = self.chase_radius
            if abs(self.x - player_x) <= r and abs(self.y - player_y) <= r:
                self.desired_dir = self._chase_dir(grid, player_x, player_y)

        if self.facing != self.desired_dir:
            # Not yet facing target — turn one 90° step
            self.facing = self._step_towards(self.desired_dir)
        else:
            # Facing target — try to move forward
            if self._try_move_forward(grid):
                # Moved — random fish pick a new direction; chase re-evaluates next tick
                if self.behavior == "random":
                    self.desired_dir = self._random_dir(grid)
            else:
                # Blocked — pick a new direction, avoiding the current one
                self.desired_dir = self._pick_dir(
                    grid, player_x, player_y, exclude=self.facing
                )

    # ----------------------------------------------------------
    #  Turning
    # ----------------------------------------------------------

    def _step_towards(self, target: int) -> int:
        """Return facing after one 90° step towards target (shortest path)."""
        right_steps = (target - self.facing) % 4
        left_steps  = (self.facing - target) % 4
        if right_steps <= left_steps:
            return (self.facing + 1) % 4
        return (self.facing - 1) % 4

    # ----------------------------------------------------------
    #  Movement
    # ----------------------------------------------------------

    def _try_move_forward(self, grid) -> bool:
        dx, dy = _DELTA[self.facing]
        nx, ny = self.x + dx, self.y + dy
        tile = grid.get(nx, ny)
        if tile is None or tile == TileType.ROCK:
            return False
        self.x, self.y = nx, ny
        return True

    # ----------------------------------------------------------
    #  Direction selection
    # ----------------------------------------------------------

    def _pick_dir(self, grid, player_x: int, player_y: int,
                  exclude: int | None = None) -> int:
        """Choose a desired direction based on behavior."""
        if self.behavior == "chase":
            r = self.chase_radius
            if abs(self.x - player_x) <= r and abs(self.y - player_y) <= r:
                return self._chase_dir(grid, player_x, player_y, exclude)
        return self._random_dir(grid, exclude)

    def _chase_dir(self, grid, player_x: int, player_y: int,
                   exclude: int | None = None) -> int:
        """Direction that best closes the gap to the player."""
        dx = player_x - self.x
        dy = player_y - self.y

        # Order candidates: close the larger axis first
        if abs(dx) >= abs(dy):
            primary   = settings.EAST  if dx > 0 else settings.WEST
            secondary = settings.SOUTH if dy > 0 else settings.NORTH
        else:
            primary   = settings.SOUTH if dy > 0 else settings.NORTH
            secondary = settings.EAST  if dx > 0 else settings.WEST

        order = [
            primary,
            secondary,
            (secondary + 2) % 4,
            (primary   + 2) % 4,
        ]

        for d in order:
            if d != exclude and self._passable(d, grid):
                return d
        return self._random_dir(grid, exclude)

    def _random_dir(self, grid, exclude: int | None = None) -> int:
        """Pick a random passable direction, optionally excluding one."""
        valid = [d for d in _DIRS if d != exclude and self._passable(d, grid)]
        if not valid:
            valid = [d for d in _DIRS if self._passable(d, grid)]
        return random.choice(valid) if valid else self.facing

    def _passable(self, direction: int, grid) -> bool:
        dx, dy = _DELTA[direction]
        tile = grid.get(self.x + dx, self.y + dy)
        return tile is not None and tile != TileType.ROCK

    # ----------------------------------------------------------
    #  EMP stun
    # ----------------------------------------------------------

    def stun(self, duration: int) -> None:
        """Stun for `duration` player actions. Stacks up to the longer."""
        self.stun_remaining = max(self.stun_remaining, duration)

    # ----------------------------------------------------------
    #  Properties
    # ----------------------------------------------------------

    @property
    def arrow(self) -> str:
        return ARROW[self.facing]

    @property
    def is_stunned(self) -> bool:
        return self.stun_remaining > 0


# =============================================================

class FishManager:
    """Manages all enemy fish for a single run."""

    def __init__(self):
        self.fish: list[Fish] = []

    # ----------------------------------------------------------
    #  Spawn
    # ----------------------------------------------------------

    def spawn(self, count: int, grid,
              spawn_x: int, spawn_y: int,
              move_interval: int = 3,
              behavior: str = "random",
              chase_radius: int = 2) -> None:
        """
        Place `count` fish on random EMPTY tiles outside the
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
                Fish(gx, gy, move_interval=move_interval,
                     behavior=behavior, chase_radius=chase_radius)
            )

        print(f"[Fish] Spawned {len(self.fish)} fish "
              f"(interval={move_interval}, behavior={behavior})")

    # ----------------------------------------------------------
    #  Per-action update
    # ----------------------------------------------------------

    def on_player_action(self, grid,
                         player_x: int = 0, player_y: int = 0) -> list[tuple[int, int]]:
        """
        Advance all fish by one player action.
        Returns the new (x, y) of every fish that moved this tick.
        """
        moved = []
        for f in self.fish:
            if f.on_player_action(grid, player_x, player_y):
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
