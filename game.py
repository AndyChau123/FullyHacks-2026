# =============================================================
#  game.py  —  Core Game class and main loop
# =============================================================

import pygame
import settings
import asset_loader
import save_manager
from grid import Grid
from menu import Menu
from player import Player, MoveResult
from tile_types import TILE_ASSETS, TileType
from ui_buttons import DirectionButtons, ACTION_LEFT, ACTION_FORWARD, ACTION_RIGHT

# Game states
_MENU    = "menu"
_PLAYING = "playing"
_DEAD    = "dead"


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
        self.state   = _PLAYING

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
                print("[Shop] Coming soon!")  # placeholder

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

        self.energy = max(0, self.energy - settings.ACTION_ENERGY_COST)

        if self.energy <= 0 and not self._at_spawn():
            print(f"[Game] OUT OF ENERGY — stranded! Score: {self.score}")
            self.state = _DEAD

        if self.scan_moves_remaining > 0:
            self.scan_moves_remaining -= 1
            if self.scan_moves_remaining == 0:
                print("[Game] Scan expired — radar back to normal.")

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
                    if self._at_spawn() and self._extract_rect.collidepoint(event.pos):
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
        data = save_manager.load()
        data["total_score"]    += self.score
        data["runs_completed"] += 1
        save_manager.save(data)
        print(f"[Game] EXTRACTED! Run score: {self.score} | "
              f"Total score: {data['total_score']} | "
              f"Energy remaining: {self.energy}")
        self.menu.reload_save()
        self.state = _MENU

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
                print(f"[Game] Treasure collected at {grid_pos}! Score: {self.score}")
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

        font = pygame.font.SysFont("monospace", 16, bold=True)
        _ARROW = {settings.NORTH:"^", settings.EAST:">",
                  settings.SOUTH:"v", settings.WEST:"<"}
        _LABEL = {
            TileType.ROCK:     ("R", (200, 100,  60)),
            TileType.TREASURE: ("T", (220, 200,  50)),
            TileType.EMPTY:    ("·", (  0, 120,  60)),
        }

        for row in range(GRID):
            for col in range(GRID):
                dx, dy    = col - HALF, row - HALF
                cell_rect = pygame.Rect(ox + col * CELL, oy + row * CELL, CELL, CELL)
                pygame.draw.rect(self.screen, (0, 60, 30), cell_rect, 1)

                if dx == 0 and dy == 0:
                    label, color = _ARROW[self.player.facing], (255, 255, 0)
                else:
                    tile = self.grid.get(self.player.x + dx, self.player.y + dy)
                    label, color = ("▓", (50, 50, 50)) if tile is None \
                                   else _LABEL.get(tile, ("?", (200, 200, 200)))

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

        title = f_large.render("OUT OF ENERGY", True, (220, 60, 60))
        self.screen.blit(title, title.get_rect(center=(cx, cy - 80)))

        sub = f_mid.render("Stranded — you never made it back.", True, (180, 100, 100))
        self.screen.blit(sub, sub.get_rect(center=(cx, cy - 10)))

        score = f_mid.render(f"Score: {self.score}", True, settings.HUD_GREEN)
        self.screen.blit(score, score.get_rect(center=(cx, cy + 50)))

        hint = f_small.render("Press any key or click to return to menu", True, (120, 120, 140))
        self.screen.blit(hint, hint.get_rect(center=(cx, cy + 110)))

    # ----------------------------------------------------------
    #  Shutdown
    # ----------------------------------------------------------

    def _quit(self) -> None:
        asset_loader.clear_cache()
        pygame.quit()
        print("[Game] Closed cleanly.")
