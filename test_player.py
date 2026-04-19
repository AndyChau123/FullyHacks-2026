# =============================================================
#  test_player.py  —  Verify Player movement logic
#  Usage:  python test_player.py
#  No Pygame required.
# =============================================================

from grid import Grid
from player import Player, MoveResult
from tile_types import TileType
import settings


def separator(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)


# ------ Build a known 5x5 grid --------------------------------
#
#   col:  0  1  2  3  4
#   row 0: .  .  .  .  .
#   row 1: .  .  .  .  .
#   row 2: .  .  @  R  .   R = ROCK at (3,2)
#   row 3: .  .  .  .  .
#   row 4: .  .  .  .  .
#
g = Grid(5, 5)
for row in range(5):
    for col in range(5):
        g.set(col, row, TileType.EMPTY)
g.set(3, 2, TileType.ROCK)


# ------ 1. Rotation -------------------------------------------
separator("1. Rotation — full 360 cycle")

p = Player(x=2, y=2, facing=settings.NORTH)
expected_cycle = [
    (settings.EAST,  "E"),
    (settings.SOUTH, "S"),
    (settings.WEST,  "W"),
    (settings.NORTH, "N"),
]
for exp_facing, exp_label in expected_cycle:
    p.rotate(1)
    assert p.facing == exp_facing, f"Expected {exp_label}, got {p.facing_label}"
    print(f"  rotate right -> {p.facing_label}  OK")

# Rotate left back to West
p.rotate(-1)
assert p.facing == settings.WEST
print(f"  rotate left  -> {p.facing_label}  OK")


# ------ 2. Move forward — success -----------------------------
separator("2. Move forward — open tile")

p = Player(x=2, y=2, facing=settings.NORTH)
result = p.move_forward(g)
assert result == MoveResult.MOVED, f"Expected MOVED, got {result}"
assert p.pos == (2, 1), f"Expected (2,1), got {p.pos}"
print(f"  Moved North to {p.pos}  OK")

p.rotate(1)   # now facing East
result = p.move_forward(g)
assert result == MoveResult.MOVED
assert p.pos == (3, 1)
print(f"  Moved East  to {p.pos}  OK")


# ------ 3. Move forward — blocked by ROCK --------------------
separator("3. Move forward — blocked tile")

p = Player(x=2, y=2, facing=settings.EAST)   # ROCK is at (3,2)
result = p.move_forward(g)
assert result == MoveResult.BLOCKED, f"Expected BLOCKED, got {result}"
assert p.pos == (2, 2), "Position should not change when blocked"
print(f"  Blocked by ROCK — pos unchanged {p.pos}  OK")


# ------ 4. Move forward — grid edge --------------------------
separator("4. Move forward — grid edge")

p = Player(x=2, y=0, facing=settings.NORTH)  # top row, facing North
result = p.move_forward(g)
assert result == MoveResult.EDGE, f"Expected EDGE, got {result}"
assert p.pos == (2, 0), "Position should not change at edge"
print(f"  Edge detected — pos unchanged {p.pos}  OK")

p2 = Player(x=4, y=2, facing=settings.EAST)  # right column, facing East
result2 = p2.move_forward(g)
assert result2 == MoveResult.EDGE
print(f"  Edge detected (right side) — pos unchanged {p2.pos}  OK")


# ------ 5. Full navigation sequence --------------------------
separator("5. Full navigation — rotate then move")

# Start centre, navigate to (2,0) via North moves
p = Player(x=2, y=2, facing=settings.NORTH)
for step in range(2):
    r = p.move_forward(g)
    assert r == MoveResult.MOVED, f"Step {step+1} failed: {r}"
assert p.pos == (2, 0), f"Expected (2,0), got {p.pos}"
print(f"  Moved 2 steps North to {p.pos}  OK")

# Rotate right (now East), move 2 steps
p.rotate(1)
for step in range(2):
    r = p.move_forward(g)
    assert r == MoveResult.MOVED
assert p.pos == (4, 0)
print(f"  Rotated East, moved 2 steps to {p.pos}  OK")

# Rotate right again (now South), move 2 steps
p.rotate(1)
for step in range(2):
    r = p.move_forward(g)
    assert r == MoveResult.MOVED
assert p.pos == (4, 2)
print(f"  Rotated South, moved 2 steps to {p.pos}  OK")


# ------ 6. facing_label and pos properties -------------------
separator("6. Properties")

p = Player(x=1, y=3, facing=settings.WEST)
assert p.facing_label == "W"
assert p.pos == (1, 3)
print(f"  facing_label={p.facing_label}  pos={p.pos}  OK")


# ------ Summary ----------------------------------------------
separator("Results")
print("  All tests passed!")