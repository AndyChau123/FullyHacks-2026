# =============================================================
#  game.py  —  Core Game class and main loop
# =============================================================

import random
import pygame
import settings
import asset_loader
import save_manager
from grid import Grid
from menu import Menu
from shop import Shop
from player import Player, MoveResult
from tile_types import TILE_ASSETS, TileType
from ui_buttons import DirectionButtons, ACTION_LEFT, ACTION_FORWARD, ACTION_RIGHT
from fish import FishManager

# Game states
_MENU    = "menu"
_PLAYING = "playing"
_DEAD    = "dead"
_RESULTS = "results"
_SHOP    = "shop"


class Game:
    """
    Owns the Pygame window, clock, and top-level state machine.

    States
    ------
    menu    — main menu (grid size + play button)
    playing — active run; Escape returns to menu
    """

    # ----------------------------------------------------------
    #  Init  (pygame + persistent UI only — game data via _start_game)
    # ----------------------------------------------------------

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(settings.WINDOW_TITLE)

        self.screen  = pygame.display.set_mode(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        )
        self.clock   = pygame.time.Clock()
        self.running = True
        self.state   = _MENU

        self.hud_image = asset_loader.load_hud(
            size=(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        )
        self.menu = Menu(self.screen, self.hud_image)
        self.shop = Shop(self.screen, self.hud_image)

        # Fixed button rects (computed once, used in playing state)
        _sbx = (settings.SCREEN_WIDTH  - settings.SCAN_BTN_W) // 2
        _sby = settings.SCREEN_HEIGHT  - settings.SCAN_BTN_H  - settings.SCAN_BTN_BOTTOM_PAD
        self._scan_rect = pygame.Rect(_sbx, _sby, settings.SCAN_BTN_W, settings.SCAN_BTN_H)

        _evp_bottom = settings.TILE_VIEWPORT_Y + settings.TILE_VIEWPORT_HEIGHT
        _ebx = (settings.SCREEN_WIDTH - settings.EXTRACT_BTN_W) // 2
        self._extract_rect = pygame.Rect(
            _ebx, _evp_bottom + 8, settings.EXTRACT_BTN_W, settings.EXTRACT_BTN_H
        )

        # Game-state fields (populated by _start_game)
        self.grid    = None
        self.player  = None
        self.buttons = None
        self.score   = 0
        self.energy  = settings.ENERGY_MAX
        self.scan_moves_remaining = 0
        self.spawn_x = self.spawn_y = 0
        self._last_action_ms: int = 0
        self.depth_multiplier: float = 1.0
        self._treasure_log: list[dict] = []   # {"base": int, "earned": int}
        self._run_shuckles: int = 0
        self._results_scroll: int = 0
        self._death_reason: str = "energy"    # "energy" | "fish"
        self.fish_manager = FishManager()

        # Results panel geometry (fixed — computed once)
        _rPW, _rPH = 680, 500
        _rpx = (settings.SCREEN_WIDTH  - _rPW) // 2
        _rpy = (settings.SCREEN_HEIGHT - _rPH) // 2
        self._results_panel  = pygame.Rect(_rpx, _rpy, _rPW, _rPH)
        self._results_close  = pygame.Rect(_rpx + _rPW - 42, _rpy + 10, 30, 30)

        # In-game inventory counts (loaded from save on run start)
        self.inv_harpoons = 0
        self.inv_emp      = 0

    # ----------------------------------------------------------
    #  Start a new run
    # ----------------------------------------------------------

    def _start_game(self, grid_size: tuple[int, int]) -> None:
        w, h = grid_size
        self.grid = Grid(width=w, height=h)
        self.grid.generate()
        self.spawn_x, self.spawn_y = self.grid.find_spawn()

        self.player  = Player(x=self.spawn_x, y=self.spawn_y, facing=settings.NORTH)
        self.buttons = DirectionButtons()
        self.score   = 0
        self.energy  = settings.ENERGY_MAX
        self.scan_moves_remaining = 0
        self._last_action_ms = 0
        self.depth_multiplier = settings.DEPTH_MULTIPLIERS.get(
            self.menu.depth_label, 1.0
        )
        self._treasure_log   = []
        self._run_shuckles   = 0
        self._results_scroll = 0
        self._death_reason   = "energy"
        _sv = save_manager.load()
        self.inv_harpoons = _sv.get("harpoons", 0)
        self.inv_emp      = _sv.get("emp_stun",  0)

        # Spawn fish — count and interval are depth-configurable
        depth   = self.menu.depth_label
        f_count = settings.FISH_COUNT.get(depth, 2)
        f_intv  = settings.FISH_MOVE_INTERVAL.get(depth, 3)
        self.fish_manager.spawn(
            count         = f_count,
            grid          = self.grid,
            spawn_x       = self.spawn_x,
            spawn_y       = self.spawn_y,
            move_interval = f_intv,
        )

        self.state = _PLAYING
        self.grid.print_ascii(self.spawn_x, self.spawn_y)
        print(f"[Game] Ready — {w}×{h} grid. "
              f"Spawn ({self.spawn_x},{self.spawn_y}). WASD/arrows to move.")

    # ----------------------------------------------------------
    #  Main loop
    # ----------------------------------------------------------

    def run(self) -> None:
        while self.running:
            if self.state == _MENU:
                self._tick_menu()
            elif self.state == _PLAYING:
                self._tick_game()
            elif self.state == _RESULTS:
                self._tick_results()
            elif self.state == _SHOP:
                self._tick_shop()
            else:
                self._tick_dead()
        self._quit()

    # ----------------------------------------------------------
    #  Menu tick
    # ----------------------------------------------------------

    def _tick_menu(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
                return
            result = self.menu.handle_event(event)
            if result == "play":
                self._start_game(self.menu.grid_size)
                return
            if result == "shop":
                self.shop.reload_save()
                self.state = _SHOP
                return

        self.menu.draw()
        pygame.display.flip()
        self.clock.tick(settings.FPS)

    # ----------------------------------------------------------
    #  Game tick
    # ----------------------------------------------------------

    def _tick_game(self) -> None:
        self._handle_events()
        self._handle_held_keys()
        self._draw()
        self.clock.tick(settings.FPS)

    # ----------------------------------------------------------
    #  Cooldown helper
    # ----------------------------------------------------------

    def _cooldown_ready(self) -> bool:
        now = pygame.time.get_ticks()
        if now - self._last_action_ms >= settings.MOVE_COOLDOWN_MS:
            self._last_action_ms = now
            return True
        return False

    # ----------------------------------------------------------
    #  Action dispatcher
    # ----------------------------------------------------------

    def _do_action(self, action: str) -> None:
        if self.energy <= 0:
            return  # no energy — all movement blocked

        if action == ACTION_LEFT:
            self.player.rotate(-1)
        elif action == ACTION_RIGHT:
            self.player.rotate(1)
        elif action == ACTION_FORWARD:
            result = self.player.move_forward(self.grid)
            if result == MoveResult.BLOCKED:
                print("[Game] Bump! Can't move there.")
            elif result == MoveResult.EDGE:
                print("[Game] Edge of the map!")
            # Player walked into a fish
            if self.fish_manager.check_collision(self.player.x, self.player.y):
                self._die_by_fish()
                return

        self.energy = max(0, self.energy - settings.ACTION_ENERGY_COST)

        if self.energy <= 0 and not self._at_spawn():
            print(f"[Game] OUT OF ENERGY — stranded! Score: {self.score}")
            self._death_reason = "energy"
            self.state = _DEAD
            return

        if self.scan_moves_remaining > 0:
            self.scan_moves_remaining -= 1
            if self.scan_moves_remaining == 0:
                print("[Game] Scan expired — radar back to normal.")

        # Advance fish; check if any moved onto the player
        self.fish_manager.on_player_action(self.grid)
        if self.fish_manager.check_collision(self.player.x, self.player.y):
            self._die_by_fish()

    def _die_by_fish(self) -> None:
        print(f"[Game] CAUGHT BY FISH — game over! Score: {self.score}")
        self._death_reason = "fish"
        self.state = _DEAD

    # ----------------------------------------------------------
    #  Event handling
    # ----------------------------------------------------------

    def _handle_events(self) -> None:
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = _MENU      # back to menu, not quit
                else:
                    action = self._key_to_action(event.key)
                    if action and self._cooldown_ready():
                        self._do_action(action)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    _hrect, _erect = self._get_inv_rects()
                    if _hrect.collidepoint(event.pos):
                        self._use_harpoon()
                    elif _erect.collidepoint(event.pos):
                        self._use_emp()
                    elif self._at_spawn() and self._extract_rect.collidepoint(event.pos):
                        self._do_extract()
                    elif self._scan_rect.collidepoint(event.pos):
                        self._try_activate_scan()
                    elif not self._try_collect_treasure(event.pos):
                        action = self.buttons.handle_click(event.pos)
                        if action and self._cooldown_ready():
                            self._do_action(action)

            elif event.type == pygame.MOUSEBUTTONUP:
                self.buttons.handle_release()

    # ----------------------------------------------------------
    #  Held-key polling
    # ----------------------------------------------------------

    def _handle_held_keys(self) -> None:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            action = ACTION_FORWARD
        elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
            action = ACTION_LEFT
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            action = ACTION_RIGHT
        else:
            return
        if self._cooldown_ready():
            self._do_action(action)

    # ----------------------------------------------------------
    #  Key → action mapping
    # ----------------------------------------------------------

    @staticmethod
    def _key_to_action(key: int) -> str | None:
        return {
            pygame.K_w:     ACTION_FORWARD,
            pygame.K_UP:    ACTION_FORWARD,
            pygame.K_a:     ACTION_LEFT,
            pygame.K_LEFT:  ACTION_LEFT,
            pygame.K_d:     ACTION_RIGHT,
            pygame.K_RIGHT: ACTION_RIGHT,
        }.get(key)

    # ----------------------------------------------------------
    #  Spawn / extract helpers
    # ----------------------------------------------------------

    def _at_spawn(self) -> bool:
        return self.player.x == self.spawn_x and self.player.y == self.spawn_y

    def _do_extract(self) -> None:
        self._run_shuckles = sum(t["earned"] for t in self._treasure_log)
        data = save_manager.load()
        data["total_score"]    += self.score
        data["runs_completed"] += 1
        data["shuckles"]       += self._run_shuckles
        save_manager.save(data)
        print(f"[Game] EXTRACTED! Score: {self.score} | "
              f"Shuckles earned: {self._run_shuckles} | "
              f"Total shuckles: {data['shuckles']}")
        self.menu.reload_save()
        self._results_scroll = 0
        self.state = _RESULTS

    # ----------------------------------------------------------
    #  Draw
    # ----------------------------------------------------------

    def _draw(self) -> None:
        # 1. HUD base
        self.screen.blit(self.hud_image, (0, 0))

        # 2. Tile viewport
        self._draw_tile_viewport()

        # 3. Extract button (only at spawn tile)
        if self._at_spawn():
            self._draw_extract_button()

        # 4. Direction buttons
        self.buttons.draw(self.screen)

        # 5. Scan button
        self._draw_scan_button()

        # 6. Radar
        self._draw_radar()

        # 7. Score + energy
        self._draw_score()
        self._draw_energy_bar()

        # 8. Inventory use buttons
        self._draw_inventory_buttons()

        # 8. Debug overlay
        self._draw_debug()

        pygame.display.flip()

    # ----------------------------------------------------------
    #  Tile viewport
    # ----------------------------------------------------------

    def _get_slot_rects(self):
        view = self.grid.get_view(self.player.x, self.player.y, self.player.facing)
        vx = settings.TILE_VIEWPORT_X
        vy = settings.TILE_VIEWPORT_Y
        vh = settings.TILE_VIEWPORT_HEIGHT
        return [
            (view.left,   view.left_pos,
             pygame.Rect(vx + settings.SLOT_LEFT_X,   vy, settings.SLOT_LEFT_W,   vh)),
            (view.center, view.center_pos,
             pygame.Rect(vx + settings.SLOT_CENTER_X, vy, settings.SLOT_CENTER_W, vh)),
            (view.right,  view.right_pos,
             pygame.Rect(vx + settings.SLOT_RIGHT_X,  vy, settings.SLOT_RIGHT_W,  vh)),
        ]

    def _draw_tile_viewport(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        for tile, _pos, rect in self._get_slot_rects():
            self._draw_tile(tile, rect.x, rect.y, rect.w, rect.h)
            if tile == TileType.TREASURE and rect.collidepoint(mouse_pos):
                self._draw_treasure_highlight(rect)

    def _draw_treasure_highlight(self, rect: pygame.Rect) -> None:
        filename = TILE_ASSETS.get(TileType.TREASURE)
        if not filename:
            return
        surf = asset_loader.load_image(
            filename, size=(rect.w, rect.h), base_dir=settings.TILES_DIR
        )
        mask   = pygame.mask.from_surface(surf)
        points = [(px + rect.x, py + rect.y) for px, py in mask.outline(every=2)]
        if len(points) > 1:
            pygame.draw.lines(self.screen, settings.TREASURE_HIGHLIGHT, True, points, 2)

    def _draw_tile(self, tile, x: int, y: int, w: int, h: int) -> None:
        if tile is None:
            return
        filename = TILE_ASSETS.get(tile)
        if filename is None:
            return
        surf = asset_loader.load_image(
            filename, size=(w, h), base_dir=settings.TILES_DIR
        )
        self.screen.blit(surf, (x, y))

    # ----------------------------------------------------------
    #  Treasure collection
    # ----------------------------------------------------------

    def _try_collect_treasure(self, click_pos) -> bool:
        for tile, grid_pos, rect in self._get_slot_rects():
            if tile == TileType.TREASURE and rect.collidepoint(click_pos) and grid_pos:
                self.grid.set(grid_pos[0], grid_pos[1], TileType.EMPTY)
                self.score += 1
                base   = random.randint(settings.TREASURE_MIN_VALUE,
                                        settings.TREASURE_MAX_VALUE)
                earned = round(base * self.depth_multiplier)
                self._treasure_log.append({"base": base, "earned": earned})
                print(f"[Game] Treasure at {grid_pos}! "
                      f"{base} × {self.depth_multiplier} = {earned} shuckles | "
                      f"Score: {self.score}")
                return True
        return False

    # ----------------------------------------------------------
    #  Extract button
    # ----------------------------------------------------------

    def _draw_extract_button(self) -> None:
        hovered  = self._extract_rect.collidepoint(pygame.mouse.get_pos())
        fill     = (60, 120, 20) if hovered else (30, 80, 10)
        border   = (150, 255, 50)
        pygame.draw.rect(self.screen, fill,   self._extract_rect, border_radius=8)
        pygame.draw.rect(self.screen, border, self._extract_rect, width=2, border_radius=8)
        font = pygame.font.SysFont("monospace", 17, bold=True)
        text = font.render(f"[ EXTRACT  —  SCORE: {self.score} ]", True, (200, 255, 100))
        self.screen.blit(text, text.get_rect(center=self._extract_rect.center))

    # ----------------------------------------------------------
    #  Scan
    # ----------------------------------------------------------

    def _try_activate_scan(self) -> None:
        if self.scan_moves_remaining > 0:
            return
        if self.energy < settings.SCAN_ENERGY_COST:
            print(f"[Game] Not enough energy to scan! "
                  f"({self.energy}/{settings.SCAN_ENERGY_COST} needed)")
            return
        self.energy -= settings.SCAN_ENERGY_COST
        self.scan_moves_remaining = settings.SCAN_DURATION_MOVES
        print(f"[Game] Scan activated for {settings.SCAN_DURATION_MOVES} moves. "
              f"Energy: {self.energy}")

    def _draw_scan_button(self) -> None:
        can_scan = self.energy >= settings.SCAN_ENERGY_COST
        active   = self.scan_moves_remaining > 0
        hovered  = self._scan_rect.collidepoint(pygame.mouse.get_pos())

        if active:
            fill, border = (0, 80, 35), (0, 255, 100)
            label, text_col = f"SCANNING  ({self.scan_moves_remaining} left)", (100, 255, 160)
        elif can_scan:
            fill   = (20, 70, 120) if hovered else (10, 40, 80)
            border = (0, 150, 200)
            label, text_col = f"[ SCAN  -{settings.SCAN_ENERGY_COST}E ]", (180, 230, 255)
        else:
            fill, border = (30, 30, 40), (60, 60, 80)
            label, text_col = "[ SCAN  —  NO ENERGY ]", (80, 80, 100)

        pygame.draw.rect(self.screen, fill,   self._scan_rect, border_radius=8)
        pygame.draw.rect(self.screen, border, self._scan_rect, width=2, border_radius=8)
        font = pygame.font.SysFont("monospace", 15, bold=True)
        text = font.render(label, True, text_col)
        self.screen.blit(text, text.get_rect(center=self._scan_rect.center))

    # ----------------------------------------------------------
    #  Radar
    # ----------------------------------------------------------

    def _draw_radar(self) -> None:
        CELL = settings.RADAR_CELL_SIZE
        PAD  = settings.RADAR_PADDING
        GRID = 5 if self.scan_moves_remaining > 0 else 3
        HALF = GRID // 2
        SIZE = CELL * GRID

        ox = settings.SCREEN_WIDTH  - SIZE - PAD
        oy = settings.SCREEN_HEIGHT - SIZE - PAD

        bg = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        self.screen.blit(bg, (ox, oy))

        font     = pygame.font.SysFont("monospace", 16, bold=True)
        font_sm  = pygame.font.SysFont("monospace", 10, bold=True)
        _PFACING = {settings.NORTH: "player_n", settings.EAST: "player_e",
                    settings.SOUTH: "player_s", settings.WEST: "player_w"}
        _ARROW   = {settings.NORTH: "^", settings.EAST: ">",
                    settings.SOUTH: "v", settings.WEST: "<"}
        _LABEL   = {
            TileType.ROCK:     ("R", (200, 100,  60)),
            TileType.TREASURE: ("T", (220, 200,  50)),
            TileType.EMPTY:    ("·", (  0, 120,  60)),
        }
        _TILE_KEY = {
            TileType.ROCK:     "rock",
            TileType.TREASURE: "treasure",
            TileType.EMPTY:    "empty",
        }
        ICON_SZ = CELL - 6   # icon fits inside cell with padding

        def _blit_icon(icon_key: str, center: tuple[int, int]) -> bool:
            """Try to blit a radar icon PNG; return True if drawn."""
            fname = settings.RADAR_ICONS.get(icon_key, "")
            if fname and asset_loader.has_image(fname, settings.UI_DIR):
                surf = asset_loader.load_image_fit(fname, ICON_SZ, ICON_SZ,
                                                   base_dir=settings.UI_DIR)
                self.screen.blit(surf, surf.get_rect(center=center))
                return True
            return False

        # Build a quick lookup: grid pos → fish
        fish_map: dict[tuple[int, int], object] = {
            (f.x, f.y): f for f in self.fish_manager.fish
        }

        for row in range(GRID):
            for col in range(GRID):
                dx, dy    = col - HALF, row - HALF
                cell_rect = pygame.Rect(ox + col * CELL, oy + row * CELL, CELL, CELL)
                pygame.draw.rect(self.screen, (0, 60, 30), cell_rect, 1)

                gx, gy = self.player.x + dx, self.player.y + dy

                if dx == 0 and dy == 0:
                    # Player cell
                    if not _blit_icon(_PFACING[self.player.facing], cell_rect.center):
                        ts = font.render(_ARROW[self.player.facing], True, (255, 255, 0))
                        self.screen.blit(ts, ts.get_rect(center=cell_rect.center))

                elif (gx, gy) in fish_map:
                    # Fish cell
                    fish = fish_map[(gx, gy)]
                    icon_key = "fish_stun" if fish.is_stunned else "fish"
                    if not _blit_icon(icon_key, cell_rect.center):
                        # Programmatic fallback: red fill + dot + arrow
                        inner = cell_rect.inflate(-4, -4)
                        pygame.draw.rect(self.screen, (120, 0, 0), inner, border_radius=3)
                        pygame.draw.circle(self.screen, (255, 60, 60),
                                           cell_rect.center, CELL // 5)
                    # Direction arrow overlay (small, top-left) — always shown
                    arrow_col = (200, 200, 200) if not fish.is_stunned else (100, 100, 160)
                    arrow_surf = font_sm.render(fish.arrow, True, arrow_col)
                    self.screen.blit(arrow_surf, (cell_rect.left + 3, cell_rect.top + 2))

                else:
                    tile = self.grid.get(gx, gy)
                    if tile is None:
                        ts = font.render("▓", True, (50, 50, 50))
                        self.screen.blit(ts, ts.get_rect(center=cell_rect.center))
                    else:
                        tkey = _TILE_KEY.get(tile)
                        if not (tkey and _blit_icon(tkey, cell_rect.center)):
                            label, color = _LABEL.get(tile, ("?", (200, 200, 200)))
                            ts = font.render(label, True, color)
                            self.screen.blit(ts, ts.get_rect(center=cell_rect.center))

        border_col = (0, 255, 100) if self.scan_moves_remaining > 0 else settings.HUD_GREEN
        pygame.draw.rect(self.screen, border_col, (ox, oy, SIZE, SIZE), 2)

        # Spawn marker on radar
        sx, sy = self.spawn_x - self.player.x, self.spawn_y - self.player.y
        if -HALF <= sx <= HALF and -HALF <= sy <= HALF:
            sc = pygame.Rect(
                ox + (sx + HALF) * CELL,
                oy + (sy + HALF) * CELL,
                CELL, CELL
            )
            pygame.draw.rect(self.screen, (200, 255, 100), sc, 2)

    # ----------------------------------------------------------
    #  Score + energy
    # ----------------------------------------------------------

    def _draw_score(self) -> None:
        font = pygame.font.SysFont("monospace", 20, bold=True)
        surf = font.render(f"SCORE: {self.score}", True, settings.HUD_GREEN)
        self.screen.blit(surf, surf.get_rect(topright=(settings.SCREEN_WIDTH - 10, 10)))

    def _draw_energy_bar(self) -> None:
        pct = self.energy / settings.ENERGY_MAX
        if pct * 100 >= settings.ENERGY_HIGH_THRESHOLD:
            filename = "battery_high.png"
        elif pct * 100 >= settings.ENERGY_MID_THRESHOLD:
            filename = "battery_mid.png"
        else:
            filename = "battery_low.png"

        bar_y = settings.SCREEN_HEIGHT - settings.ENERGY_BAR_H - settings.SCAN_BTN_BOTTOM_PAD
        surf  = asset_loader.load_image_fit(
            filename, settings.ENERGY_BAR_W, settings.ENERGY_BAR_H,
            base_dir=settings.UI_DIR,
        )
        img_y = bar_y + (settings.ENERGY_BAR_H - surf.get_height())
        self.screen.blit(surf, (settings.ENERGY_BAR_X, img_y))

        font  = pygame.font.SysFont("monospace", 15, bold=True)
        label = font.render(f"{self.energy}/{settings.ENERGY_MAX}", True, settings.HUD_GREEN)
        self.screen.blit(label, (
            settings.ENERGY_BAR_X + surf.get_width() + 8,
            img_y + surf.get_height() // 2 - label.get_height() // 2,
        ))

    # ----------------------------------------------------------
    #  Debug overlay
    # ----------------------------------------------------------

    def _draw_debug(self) -> None:
        font = pygame.font.SysFont("monospace", 16)
        view = self.grid.get_view(self.player.x, self.player.y, self.player.facing)

        def tile_name(t):
            return t.name if t else "edge"

        lines = [
            f"FPS: {int(self.clock.get_fps())}",
            f"Pos: ({self.player.x},{self.player.y})  Facing: {self.player.facing_label}",
            f"View  L:{tile_name(view.left)}"
            f"  C:{tile_name(view.center)}"
            f"  R:{tile_name(view.right)}",
        ]
        for i, line in enumerate(lines):
            surf = font.render(line, True, settings.HUD_GREEN)
            self.screen.blit(surf, (10, 10 + i * 22))

    # ----------------------------------------------------------
    #  Shop state
    # ----------------------------------------------------------

    def _tick_shop(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            result = self.shop.handle_event(event)
            if result == "back":
                self.menu.reload_save()
                self.state = _MENU
                return

        self.shop.draw()
        pygame.display.flip()
        self.clock.tick(settings.FPS)

    # ----------------------------------------------------------
    #  Results screen
    # ----------------------------------------------------------

    def _tick_results(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = _MENU
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._results_close.collidepoint(event.pos):
                    self.state = _MENU
                    return
            if event.type == pygame.MOUSEWHEEL:
                max_scroll = max(0, len(self._treasure_log) - 8)
                self._results_scroll = max(
                    0, min(self._results_scroll - event.y, max_scroll)
                )

        self.menu.draw()
        self._draw_results_panel()
        pygame.display.flip()
        self.clock.tick(settings.FPS)

    def _draw_results_panel(self) -> None:
        p      = self._results_panel
        mouse  = pygame.mouse.get_pos()
        log    = self._treasure_log

        # Dim background
        dim = pygame.Surface(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA
        )
        dim.fill((0, 0, 0, 170))
        self.screen.blit(dim, (0, 0))

        # Panel body
        pygame.draw.rect(self.screen, (4, 18, 36),  p, border_radius=12)
        pygame.draw.rect(self.screen, settings.HUD_GREEN, p, width=2, border_radius=12)

        f_lg = pygame.font.SysFont("monospace", 24, bold=True)
        f_md = pygame.font.SysFont("monospace", 16, bold=True)
        f_sm = pygame.font.SysFont("monospace", 14)

        cx = p.centerx

        # Title
        title = f_lg.render("EXTRACTION COMPLETE", True, settings.HUD_GREEN)
        self.screen.blit(title, title.get_rect(center=(cx, p.top + 28)))

        # Depth + multiplier
        mult_label = f"{self.depth_multiplier}×"
        sub = f_sm.render(
            f"{self.menu.depth_label}  ·  {mult_label} Multiplier",
            True, (100, 170, 130),
        )
        self.screen.blit(sub, sub.get_rect(center=(cx, p.top + 56)))

        # Close button
        hov = self._results_close.collidepoint(mouse)
        pygame.draw.rect(self.screen,
                         (130, 25, 25) if hov else (80, 10, 10),
                         self._results_close, border_radius=6)
        pygame.draw.rect(self.screen, (200, 60, 60),
                         self._results_close, width=1, border_radius=6)
        xt = f_md.render("✕", True, (255, 110, 110))
        self.screen.blit(xt, xt.get_rect(center=self._results_close.center))

        # Divider
        div1_y = p.top + 72
        pygame.draw.line(self.screen, (0, 90, 55),
                         (p.left + 20, div1_y), (p.right - 20, div1_y))

        # Treasure list
        ROW_H    = 30
        LIST_TOP = div1_y + 8
        VISIBLE  = 8
        LIST_H   = ROW_H * VISIBLE

        if not log:
            empty = f_sm.render("No treasures collected.", True, (80, 120, 100))
            self.screen.blit(empty, empty.get_rect(
                center=(cx, LIST_TOP + LIST_H // 2)
            ))
        else:
            max_scroll = max(0, len(log) - VISIBLE)
            self._results_scroll = max(0, min(self._results_scroll, max_scroll))

            for i, entry in enumerate(
                log[self._results_scroll: self._results_scroll + VISIBLE]
            ):
                idx    = i + self._results_scroll
                row_y  = LIST_TOP + i * ROW_H
                base   = entry["base"]
                earned = entry["earned"]
                row = f_sm.render(
                    f"  #{idx+1:>2}   {base:>3} shuckles  ×  "
                    f"{self.depth_multiplier}  =  {earned:>4} shuckles",
                    True, (150, 215, 175),
                )
                self.screen.blit(row, (p.left + 24, row_y + 8))

            if len(log) > VISIBLE:
                hint = f_sm.render(
                    f"scroll ↑↓   "
                    f"({self._results_scroll+1}–"
                    f"{min(self._results_scroll+VISIBLE, len(log))} "
                    f"of {len(log)})",
                    True, (60, 100, 80),
                )
                self.screen.blit(hint, hint.get_rect(
                    center=(cx, LIST_TOP + LIST_H + 4)
                ))

        # Divider
        div2_y = LIST_TOP + LIST_H + (22 if len(log) > VISIBLE else 12)
        pygame.draw.line(self.screen, (0, 90, 55),
                         (p.left + 20, div2_y), (p.right - 20, div2_y))

        # Footer
        foot_y = div2_y + 14
        count_txt = f_md.render(
            f"Treasures collected:  {len(log)}", True, (100, 170, 130)
        )
        self.screen.blit(count_txt, (p.left + 30, foot_y))

        total_txt = f_lg.render(
            f"TOTAL:  {self._run_shuckles} shuckles",
            True, (255, 215, 0),
        )
        self.screen.blit(total_txt, (p.left + 30, foot_y + 32))

    # ----------------------------------------------------------
    #  Dead state
    # ----------------------------------------------------------

    def _tick_dead(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.state = _MENU
                return

        self.screen.blit(self.hud_image, (0, 0))
        self._draw_game_over_overlay()
        pygame.display.flip()
        self.clock.tick(settings.FPS)

    def _draw_game_over_overlay(self) -> None:
        overlay = pygame.Surface(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        cx = settings.SCREEN_WIDTH  // 2
        cy = settings.SCREEN_HEIGHT // 2

        f_large = pygame.font.SysFont("monospace", 52, bold=True)
        f_mid   = pygame.font.SysFont("monospace", 24, bold=True)
        f_small = pygame.font.SysFont("monospace", 16)

        if self._death_reason == "fish":
            title_text = "CAUGHT BY A FISH"
            sub_text   = "Devoured in the deep — no treasures gained."
        else:
            title_text = "OUT OF ENERGY"
            sub_text   = "Stranded — you never made it back."

        title = f_large.render(title_text, True, (220, 60, 60))
        self.screen.blit(title, title.get_rect(center=(cx, cy - 80)))

        sub = f_mid.render(sub_text, True, (180, 100, 100))
        self.screen.blit(sub, sub.get_rect(center=(cx, cy - 10)))

        score = f_mid.render(f"Score: {self.score}", True, settings.HUD_GREEN)
        self.screen.blit(score, score.get_rect(center=(cx, cy + 50)))

        hint = f_small.render("Press any key or click to return to menu", True, (120, 120, 140))
        self.screen.blit(hint, hint.get_rect(center=(cx, cy + 110)))

    # ----------------------------------------------------------
    #  Inventory use buttons (in-game, left of radar)
    # ----------------------------------------------------------

    def _get_inv_rects(self) -> tuple[pygame.Rect, pygame.Rect]:
        """Compute inventory button rects from the live radar size so they
        always sit flush to the left edge of the radar, even during a 5×5 scan."""
        CELL     = settings.RADAR_CELL_SIZE
        PAD      = settings.RADAR_PADDING
        GRID     = 5 if self.scan_moves_remaining > 0 else 3
        SIZE     = CELL * GRID
        radar_ox = settings.SCREEN_WIDTH  - SIZE - PAD
        radar_oy = settings.SCREEN_HEIGHT - SIZE - PAD
        inv_w, inv_h = 100, 46
        inv_x    = radar_ox - inv_w - 10
        harpoon  = pygame.Rect(inv_x, radar_oy,              inv_w, inv_h)
        emp      = pygame.Rect(inv_x, radar_oy + inv_h + 8,  inv_w, inv_h)
        return harpoon, emp

    def _draw_inventory_buttons(self) -> None:
        mouse = pygame.mouse.get_pos()
        font  = pygame.font.SysFont("monospace", 13, bold=True)
        harpoon_rect, emp_rect = self._get_inv_rects()

        items = [
            ("⚔ Harpoon", self.inv_harpoons, 3, harpoon_rect),
            ("⚡ EMP",     self.inv_emp,      1, emp_rect),
        ]

        for label, count, max_c, rect in items:
            has     = count > 0
            hovered = rect.collidepoint(mouse)

            if has:
                fill   = (20, 70, 110) if hovered else (10, 40, 75)
                border = (0, 180, 220)
                t_col  = (180, 230, 255)
            else:
                fill, border, t_col = (20, 20, 28), (50, 50, 65), (60, 60, 80)

            pygame.draw.rect(self.screen, fill,   rect, border_radius=7)
            pygame.draw.rect(self.screen, border, rect, width=1, border_radius=7)

            name_s  = font.render(label, True, t_col)
            count_s = font.render(f"{count}/{max_c}", True,
                                  (255, 215, 0) if has else (60, 60, 80))
            self.screen.blit(name_s,  name_s.get_rect(
                center=(rect.centerx, rect.centery - 8)))
            self.screen.blit(count_s, count_s.get_rect(
                center=(rect.centerx, rect.centery + 10)))

    def _use_harpoon(self) -> None:
        if self.inv_harpoons <= 0:
            return
        self.inv_harpoons -= 1
        _sv = save_manager.load()
        _sv["harpoons"] = self.inv_harpoons
        save_manager.save(_sv)
        print(f"[Game] Harpoon fired! ({self.inv_harpoons} remaining) — effect TBD")

    def _use_emp(self) -> None:
        if self.inv_emp <= 0:
            return
        self.inv_emp -= 1
        _sv = save_manager.load()
        _sv["emp_stun"] = self.inv_emp
        save_manager.save(_sv)
        # Stun all fish within 1 tile (Chebyshev) = 3×3 area around player
        self.fish_manager.stun_radius(
            self.player.x, self.player.y,
            radius=1, duration=settings.EMP_STUN_DURATION,
        )
        print(f"[Game] EMP detonated! — fish stunned for "
              f"{settings.EMP_STUN_DURATION} actions")

    # ----------------------------------------------------------
    #  Shutdown
    # ----------------------------------------------------------

    def _quit(self) -> None:
        asset_loader.clear_cache()
        pygame.quit()
        print("[Game] Closed cleanly.")
