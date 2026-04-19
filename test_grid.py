# =============================================================
#  test_grid.py  —  Run this any time to verify the grid logic
#  Usage:  python test_grid.py
#  No Pygame required.
# =============================================================

from grid import Grid, ViewSlice
from tile_types import TileType
import settings


def separator(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)


# ----------------------------------------------------------
# 1. Basic generation
# ----------------------------------------------------------
separator("1. Grid generation (seed=1)")
g = Grid(width=10, height=10)
g.generate(seed=1)
g.print_ascii()


# ----------------------------------------------------------
# 2. Spawn is always in-bounds and not blocked
# ----------------------------------------------------------
separator("2. Spawn point")
import random
spawn_x, spawn_y = g.find_spawn(rng=random.Random(1))
tile = g.get(spawn_x, spawn_y)
assert g.in_bounds(spawn_x, spawn_y), "Spawn out of bounds!"
assert not g.is_blocked(spawn_x, spawn_y), f"Spawn on blocked tile {tile}!"
print(f"  Spawn at ({spawn_x}, {spawn_y})  tile={tile.name}  OK")


# ----------------------------------------------------------
# 3. get_view — all four facing directions on a known map
# ----------------------------------------------------------
separator("3. get_view — known 5x5 grid")

#  Hand-craft a tiny 5×5 map:
#
#  col:  0  1  2  3  4
#  row 0: .  .  R  .  .
#  row 1: .  .  .  .  .
#  row 2: .  .  @  .  .   ← player at (2,2) facing North
#  row 3: .  T  .  .  .
#  row 4: .  .  .  .  .
#
#  Facing North from (2,2):
#    front  = (2, 1)  → EMPTY
#    left   = (1, 1)  → EMPTY
#    right  = (3, 1)  → EMPTY
#
#  One row further north (2,0):  ROCK   (not in view — only 1 step ahead)

mini = Grid(width=5, height=5)
mini.generate(seed=0)
# Override specific tiles
for row in range(5):
    for col in range(5):
        mini.set(col, row, TileType.EMPTY)

mini.set(2, 0, TileType.ROCK)
mini.set(1, 3, TileType.TREASURE)

print("\n  Map (@ = player at 2,2 facing North):")
mini.print_ascii(player_x=2, player_y=2)

tests = [
    # (facing, expected_left, expected_center, expected_right, label)
    #
    # Treasure is at (1,3). Player at (2,2).
    # Facing South: forward=(2,3), perp_right=(-1,0)
    #   center=(2,3)=EMPTY  left=(3,3)=EMPTY  right=(1,3)=TREASURE
    # Facing West:  forward=(1,2), perp_right=(0,-1)
    #   center=(1,2)=EMPTY  left=(1,3)=TREASURE  right=(1,1)=EMPTY
    (settings.NORTH, TileType.EMPTY,    TileType.EMPTY, TileType.EMPTY,    "North"),
    (settings.EAST,  TileType.EMPTY,    TileType.EMPTY, TileType.EMPTY,    "East"),
    (settings.SOUTH, TileType.EMPTY,    TileType.EMPTY, TileType.TREASURE, "South"),
    (settings.WEST,  TileType.TREASURE, TileType.EMPTY, TileType.EMPTY,    "West"),
]

all_ok = True
for facing, exp_l, exp_c, exp_r, label in tests:
    v = mini.get_view(2, 2, facing)
    ok = (v.left == exp_l and v.center == exp_c and v.right == exp_r)
    status = "OK " if ok else "FAIL"
    if not ok:
        all_ok = False
    print(f"  [{status}] facing {label:5s}  "
          f"L={v.left and v.left.name or 'None':8s} "
          f"C={v.center and v.center.name or 'None':8s} "
          f"R={v.right and v.right.name or 'None':8s}")
    if not ok:
        print(f"         expected  L={exp_l.name} C={exp_c.name} R={exp_r.name}")


# ----------------------------------------------------------
# 4. Edge / out-of-bounds returns None (not a crash)
# ----------------------------------------------------------
separator("4. Out-of-bounds handling")
corner_view = mini.get_view(0, 0, settings.NORTH)
print(f"  View from top-left corner facing North:")
print(f"    L={corner_view.left}  C={corner_view.center}  R={corner_view.right}")
assert corner_view.center is None, "Center should be None (out of bounds)"
assert corner_view.left   is None, "Left should be None (out of bounds)"
print("  Out-of-bounds returns None correctly  OK")


# ----------------------------------------------------------
# 5. BLOCKED tiles stop movement
# ----------------------------------------------------------
separator("5. is_blocked")
mini.set(2, 1, TileType.ROCK)
assert mini.is_blocked(2, 1),  "Rock should be blocked"
assert mini.is_blocked(-1, 0), "Out-of-bounds should be blocked"
assert not mini.is_blocked(2, 2), "Empty tile should not be blocked"
print("  ROCK blocked=True          OK")
print("  out-of-bounds blocked=True OK")
print("  EMPTY blocked=False        OK")


# ----------------------------------------------------------
# Summary
# ----------------------------------------------------------
separator("Results")
if all_ok:
    print("  All tests passed!")
else:
    print("  Some tests FAILED — check output above.")