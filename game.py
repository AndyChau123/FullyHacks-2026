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
from mine import MineManager
from home_screen import HomeScreen
from cutscene import Cutscene, DEPTH_TIPS

# Direction delta used for harpoon ray-casting (defined here to avoid importing fish internals)
_DIR_DELTA = {
    settings.NORTH: ( 0, -1),
    settings.EAST:  ( 1,  0),
    settings.SOUTH: ( 0,  1),
    settings.WEST:  (-1,  0),
}

# Game states
_HOME        = "home"
_CUTSCENE    = "cutscene"
_HOW_TO_PLAY = "how_to_play"
_DEPTH_TIP   = "depth_tip"
_MENU        = "menu"
_PLAYING     = "playing"
_DEAD        = "dead"
_RESULTS     = "results"
_SHOP        = "shop"
_GAME_OVER   = "game_over"


class Game:
    """
    Owns the Pygame window, clock, and top-level state machine.
    """

    # ----------------------------------------------------------
    #  Init
    # ----------------------------------------------------------

    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_caption(settings.WINDOW_TITLE)

        pygame.mixer.music.load("./assets/music/Below_the_Crushing_Weight.mp3")

        self.screen  = pygame.display.set_mode(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        )
        self.clock   = pygame.time.Clock()
        self.running = True
        self.state   = _HOME

        self.hud_image = asset_loader.load_hud(
            size=(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        )
        self.home_screen = HomeScreen(self.screen, self.hud_image)
        self.menu        = Menu(self.screen, self.hud_image)
        self.shop        = Shop(self.screen, self.hud_image)
        self.cutscene      = None
        self._depths_tipped: set[str] = set()

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
        self._treasure_log: list[dict] = []
        self._run_shuckles: int = 0
        self._results_scroll: int = 0
        self._death_reason: str = "energy"
        self.fish_manager = FishManager()
        self.mine_manager = MineManager()
        self._energy_upgrade_tier  = 0
        self._scanner_upgrade_uses = 0
        self._scan_enhanced        = False
        self._depth_bonus          = 0
        self._shuckle_bonus        = 0
        self._run_harpoon_kills    = 0
        self._game_score_total     = 0   # cumulative score across all runs of the current game
        self._final_game_score     = 0   # locked in when the game ends (shown on game-over screen)
        self._final_game_shuckles  = 0
        self.inv_harpoons = 0
        self.inv_emp      = 0
        self.inv_battery  = 0
        self.inv_romo     = 0

        # HUD message system
        self._hud_message       = ""
        self._hud_message_until = 0

        _rPW, _rPH = 680, 500
        _rpx = (settings.SCREEN_WIDTH  - _rPW) // 2
        _rpy = (settings.SCREEN_HEIGHT - _rPH) // 2
        self._results_panel  = pygame.Rect(_rpx, _rpy, _rPW, _rPH)
        self._results_close  = pygame.Rect(_rpx + _rPW - 42, _rpy + 10, 30, 30)

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
        self._treasure_log       = []
        self._run_shuckles       = 0
        self._results_scroll     = 0
        self._death_reason       = "energy"
        self._game_complete      = False
        self._depth_bonus        = 0
        self._shuckle_bonus      = 0
        self._run_harpoon_kills  = 0
        self._hud_message        = ""
        self._hud_message_until  = 0

        _sv = save_manager.load()

        if _sv.get("game_runs_done", 0) >= settings.RUNS_PER_GAME:
            _sv["game_runs_done"]      = 0
            _sv["game_battery_bought"] = 0
            _sv["game_romo_bought"]    = 0
            _sv["romo_rescue"]         = 0
            self._game_score_total     = 0

        self._current_run = _sv.get("game_runs_done", 0) + 1

        _sv["battery_pack"] = 0
        save_manager.save(_sv)

        self.inv_harpoons = max(1, _sv.get("harpoons", 0))
        # EMP auto-refills each run if ever purchased
        self.inv_emp      = 1 if _sv.get("emp_ever_bought", 0) else 0
        self.inv_battery  = 0
        self.inv_romo     = _sv.get("romo_rescue", 0)

        self._energy_upgrade_tier  = _sv.get("energy_upgrade_tier",  0)
        self._scanner_upgrade_uses = _sv.get("scanner_upgrade_uses", 0)
        self._scan_enhanced        = False

        depth      = self.menu.depth_label
        f_count    = settings.FISH_COUNT.get(depth, 2)
        f_intv     = settings.FISH_MOVE_INTERVAL.get(depth, 3)
        f_behavior = settings.FISH_BEHAVIOR.get(depth, "random")
        f_radius   = settings.FISH_CHASE_RADIUS.get(depth, 2)
        self.fish_manager.spawn(
            count=f_count, grid=self.grid,
            spawn_x=self.spawn_x, spawn_y=self.spawn_y,
            move_interval=f_intv, behavior=f_behavior, chase_radius=f_radius,
        )

        m_count = settings.MINE_COUNT.get(depth, 0)
        if m_count > 0:
            self.mine_manager.spawn(
                count=m_count, grid=self.grid,
                spawn_x=self.spawn_x, spawn_y=self.spawn_y,
            )
        else:
            self.mine_manager.mines.clear()

        self.state = _PLAYING
        self.grid.print_ascii(self.spawn_x, self.spawn_y)
        print(f"[Game] Ready — {w}×{h} grid. "
              f"Spawn ({self.spawn_x},{self.spawn_y}). WASD/arrows to move.")

    # ----------------------------------------------------------
    #  Main loop
    # ----------------------------------------------------------

    def run(self) -> None:
        pygame.mixer.music.play(loops=-1)
        while self.running:
            if self.state == _HOME:
                self._tick_home()
            elif self.state == _CUTSCENE:
                self._tick_cutscene()
            elif self.state == _HOW_TO_PLAY:
                self._tick_how_to_play()
            elif self.state == _DEPTH_TIP:
                self._tick_depth_tip()
            elif self.state == _MENU:
                self._tick_menu()
            elif self.state == _PLAYING:
                self._tick_game()
            elif self.state == _RESULTS:
                self._tick_results()
            elif self.state == _SHOP:
                self._tick_shop()
            elif self.state == _GAME_OVER:
                self._tick_game_over()
            else:
                self._tick_dead()
        self._quit()

    # ----------------------------------------------------------
    #  Home screen tick
    # ----------------------------------------------------------

    def _tick_home(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            result = self.home_screen.handle_event(event)
            if result == "start":
                self.cutscene = Cutscene(self.screen, self.hud_image)
                self.state    = _CUTSCENE
                return
            if result == "quit":
                self.running = False
                return

        self.home_screen.draw()
        pygame.display.flip()
        self.clock.tick(settings.FPS)

    # ----------------------------------------------------------
    #  Cutscene tick
    # ----------------------------------------------------------

    def _tick_cutscene(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if self.cutscene and self.cutscene.handle_event(event) == "done":
                self.state = _HOW_TO_PLAY
                return

        if self.cutscene:
            self.cutscene.draw()
        pygame.display.flip()
        self.clock.tick(settings.FPS)

    # ----------------------------------------------------------
    #  How-to-play infographic (shown once after intro cutscene)
    # ----------------------------------------------------------

    def _tick_how_to_play(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.state = _MENU
                return
            if event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                self.state = _MENU
                return

        self._draw_how_to_play()
        pygame.display.flip()
        self.clock.tick(settings.FPS)

    def _draw_how_to_play(self) -> None:
        # Delegate to home_screen — it already has the exact panel drawing logic.
        # Temporarily force the instructions overlay visible, draw, then restore.
        self.home_screen._ensure_fonts()
        self.home_screen._show_instructions = True
        self.home_screen.draw()
        self.home_screen._show_instructions = False

    # ----------------------------------------------------------
    #  Depth tip tick  (Romo's one-line tip before a new depth)
    # ----------------------------------------------------------

    def _tick_depth_tip(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if self.cutscene and self.cutscene.handle_event(event) == "done":
                self._start_game(self.menu.grid_size)
                return

        if self.cutscene:
            self.cutscene.draw()
        pygame.display.flip()
        self.clock.tick(settings.FPS)

    # ----------------------------------------------------------
    #  Menu tick
    # ----------------------------------------------------------

    def _tick_menu(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = _HOME
                return
            result = self.menu.handle_event(event)
            if result == "play":
                depth = self.menu.depth_label
                if depth not in self._depths_tipped and depth in DEPTH_TIPS:
                    self._depths_tipped.add(depth)
                    self.cutscene = Cutscene(
                        self.screen, self.hud_image,
                        dialog=DEPTH_TIPS[depth],
                        depth_label=depth,
                        show_cyndi=False,
                    )
                    self.state = _DEPTH_TIP
                else:
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
            return

        if action == ACTION_LEFT:
            self.player.rotate(-1)
        elif action == ACTION_RIGHT:
            self.player.rotate(1)
        elif action == ACTION_FORWARD:
            result = self.player.move_forward(self.grid)
            if result == MoveResult.BLOCKED:
                print("[Game] Bump! Can't move there.")
                return
            elif result == MoveResult.EDGE:
                print("[Game] Edge of the map!")
                return
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
                self._scan_enhanced = False
                print("[Game] Scan expired.")

        # Advance fish
        self.fish_manager.on_player_action(self.grid, self.player.x, self.player.y)
        if self.fish_manager.check_collision(self.player.x, self.player.y):
            self._die_by_fish()
            return

        # Advance mines (trigger, countdown, explode)
        explosions = self.mine_manager.on_player_action(
            self.player.x, self.player.y, self.grid, self.fish_manager
        )
        if explosions:
            self._handle_mine_explosions(explosions)

    # ----------------------------------------------------------
    #  Death helpers
    # ----------------------------------------------------------

    def _die_by_fish(self) -> None:
        print(f"[Game] CAUGHT BY FISH — run streak reset! Score: {self.score}")
        self._death_reason = "fish"
        _sv = save_manager.load()
        _sv["game_runs_done"] = 0
        save_manager.save(_sv)
        self.state = _DEAD

    def _die_by_mine(self) -> None:
        print(f"[Game] KILLED BY MINE EXPLOSION — run streak reset! Score: {self.score}")
        self._death_reason = "mine"
        _sv = save_manager.load()
        _sv["game_runs_done"] = 0
        save_manager.save(_sv)
        self.state = _DEAD

    def _handle_mine_explosions(self, explosions: list[dict]) -> None:
        for exp in explosions:
            if exp["killed_player"]:
                self._die_by_mine()
                return
            print(f"[Game] Mine exploded at ({exp['cx']},{exp['cy']}) — player safe")

    # ----------------------------------------------------------
    #  HUD message system
    # ----------------------------------------------------------

    def _show_hud_message(self, msg: str, duration_ms: int = 2500) -> None:
        self._hud_message       = msg
        self._hud_message_until = pygame.time.get_ticks() + duration_ms

    def _draw_hud_message(self) -> None:
        if pygame.time.get_ticks() >= self._hud_message_until:
            return
        font = pygame.font.SysFont("monospace", 18, bold=True)
        surf = font.render(self._hud_message, True, (255, 220, 50))
        x = settings.SCREEN_WIDTH  // 2 - surf.get_width()  // 2
        y = settings.TILE_VIEWPORT_Y + settings.TILE_VIEWPORT_HEIGHT + 62
        bg = pygame.Surface((surf.get_width() + 24, surf.get_height() + 10),
                             pygame.SRCALPHA)
        bg.fill((0, 0, 0, 200))
        self.screen.blit(bg, (x - 12, y - 5))
        self.screen.blit(surf, (x, y))

    # ----------------------------------------------------------
    #  Event handling
    # ----------------------------------------------------------

    def _handle_events(self) -> None:
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = _MENU
                else:
                    action = self._key_to_action(event.key)
                    if action and self._cooldown_ready():
                        self._do_action(action)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    _hrect, _erect, _brect, _rrect = self._get_inv_rects()
                    if _hrect.collidepoint(event.pos):
                        self._use_harpoon()
                    elif _erect.collidepoint(event.pos):
                        self._use_emp()
                    elif _brect.collidepoint(event.pos):
                        self._use_battery_pack()
                    elif _rrect.collidepoint(event.pos):
                        self._use_romo_rescue()
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

        self._depth_bonus = settings.DEPTH_CLEAR_SCORE.get(self.menu.depth_label, 0)
        self.score += self._depth_bonus

        data = save_manager.load()
        data["shuckles"]       += self._run_shuckles
        data["game_runs_done"]  = data.get("game_runs_done", 0) + 1
        self._game_complete     = data["game_runs_done"] >= settings.RUNS_PER_GAME

        self._shuckle_bonus = 0
        if self._game_complete:
            self._shuckle_bonus = data["shuckles"] * settings.SHUCKLE_SCORE_RATE
            self.score += self._shuckle_bonus
            print(f"[Game] GAME COMPLETE — "
                  f"{data['shuckles']} shuckles → +{self._shuckle_bonus} score!")

        data["total_score"]    += self.score
        data["runs_completed"] += 1
        self._game_score_total += self.score

        if self._game_complete:
            self._final_game_score    = self._game_score_total
            self._final_game_shuckles = data["shuckles"]

        save_manager.save(data)

        print(f"[Game] EXTRACTED! Run {self._current_run}/{settings.RUNS_PER_GAME} | "
              f"Score: {self.score} | Shuckles: {self._run_shuckles} | "
              f"Total: {data['shuckles']}")
        self.menu.reload_save()
        self._results_scroll = 0
        self.state = _RESULTS

    # ----------------------------------------------------------
    #  Draw
    # ----------------------------------------------------------

    def _draw(self) -> None:
        # 1. Dark base fill
        self.screen.fill(settings.DARK_BLUE)
        # 2. Depth-specific ocean background (full screen)
        self._draw_ocean_background()
        # 3. Tile entities (rocks/treasure sit on top of the ocean)
        self._draw_tile_viewport()
        # 4. Frame overlay — opaque walls hide edges, transparent windows reveal scene
        self.screen.blit(self.hud_image, (0, 0))
        # 5. UI elements rendered on top of the frame
        if self._at_spawn():
            self._draw_extract_button()
        self.buttons.draw(self.screen)
        self._draw_scan_button()
        self._draw_radar()
        self._draw_score()
        self._draw_energy_bar()
        self._draw_inventory_buttons()
        self._draw_hud_message()
        self._draw_debug()
        pygame.display.flip()

    def _draw_ocean_background(self) -> None:
        depth = self.menu.depth_label
        fname = settings.BG_SHALLOW if depth in ("Depth 1", "Depth 2") else settings.BG_DEEP
        if asset_loader.has_image(fname, settings.IMAGES_DIR):
            bg = asset_loader.load_image(
                fname,
                size=(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT),
                base_dir=settings.IMAGES_DIR,
            )
            self.screen.blit(bg, (0, 0))

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
        slots = self._get_slot_rects()
        fish_map = {(f.x, f.y): f for f in self.fish_manager.fish}
        mine_map = {(m.x, m.y): m for m in self.mine_manager.mines}
        depth = self.menu.depth_label
        for i, (tile, pos, rect) in enumerate(slots):
            scale = (settings.TILE_IMG_SCALE_CENTER if i == 1
                     else settings.TILE_IMG_SCALE_SIDE)
            self._draw_tile(tile, rect, scale, pos)
            if tile == TileType.TREASURE and rect.collidepoint(mouse_pos):
                self._draw_treasure_highlight(rect, scale)
            if pos and pos in mine_map:
                self._draw_entity_on_tile("landmine_tile.png", rect, scale)
            if pos and pos in fish_map:
                self._draw_fish_on_tile(fish_map[pos], i, rect, scale, depth)

    def _draw_treasure_highlight(self, rect: pygame.Rect, scale: float) -> None:
        filename = TILE_ASSETS.get(TileType.TREASURE)
        if not filename:
            return
        max_w = max(1, int(rect.w * scale))
        max_h = max(1, int(rect.h * scale))
        surf   = asset_loader.load_image_fit(filename, max_w, max_h,
                                             base_dir=settings.TILES_DIR)
        img_x  = rect.x + (rect.w - surf.get_width()) // 2
        free_y = rect.h - surf.get_height()
        img_y  = rect.y + int(free_y * settings.TILE_VERTICAL_BIAS)
        mask   = pygame.mask.from_surface(surf)
        points = [(px + img_x, py + img_y) for px, py in mask.outline(every=2)]
        if len(points) > 1:
            pygame.draw.lines(self.screen, settings.TREASURE_HIGHLIGHT, True, points, 2)

    def _draw_tile(self, tile, rect: pygame.Rect, scale: float, pos=None) -> None:
        if tile is None:
            return
        if tile == TileType.ROCK:
            depth = self.menu.depth_label
            if depth in ("Depth 3", "Depth 4"):
                variant = ((pos[0] + pos[1]) % 2) if pos else 0
                filename = "rock2_depth3and4.png" if variant else "rock_depth3and4.png"
            else:
                filename = "rock2_depth1and2.png"
        else:
            filename = TILE_ASSETS.get(tile)
        if filename is None:
            return
        max_w = max(1, int(rect.w * scale))
        max_h = max(1, int(rect.h * scale))
        surf  = asset_loader.load_image_fit(filename, max_w, max_h,
                                            base_dir=settings.TILES_DIR)
        img_x = rect.x + (rect.w - surf.get_width()) // 2
        free_y = rect.h - surf.get_height()
        img_y  = rect.y + int(free_y * settings.TILE_VERTICAL_BIAS)
        self.screen.blit(surf, (img_x, img_y))

    def _draw_entity_on_tile(self, filename: str, rect: pygame.Rect, scale: float) -> None:
        """Draw a non-tile entity (mine, fish) on top of the slot at the same bias position."""
        max_w = max(1, int(rect.w * scale))
        max_h = max(1, int(rect.h * scale))
        surf  = asset_loader.load_image_fit(filename, max_w, max_h,
                                            base_dir=settings.TILES_DIR)
        img_x = rect.x + (rect.w - surf.get_width()) // 2
        free_y = rect.h - surf.get_height()
        img_y  = rect.y + int(free_y * settings.TILE_VERTICAL_BIAS)
        self.screen.blit(surf, (img_x, img_y))

    # slot index: 0=left, 1=center, 2=right
    _FISH_ASSETS = {
        "depth1": {
            "front": "depth1fish_front.png",
            "side":  "depth1fish_facing_right.png",
            "side_faces": "right",
        },
        "depth2and3": {
            "front": "depth2and3fish_front.png",
            "side":  "depth2and3fish_side_angle_facing_right.png",
            "side_faces": "right",
        },
        "depth4": {
            "front": "depth4_fish_facing_front.png",
            "side":  "depth4_fish_facing_left.png",
            "side_faces": "left",
        },
    }

    def _draw_fish_on_tile(self, fish, slot_idx: int, rect: pygame.Rect,
                           scale: float, depth: str) -> None:
        if depth == "Depth 1":
            tier = "depth1"
        elif depth in ("Depth 2", "Depth 3"):
            tier = "depth2and3"
        else:
            tier = "depth4"
        assets = self._FISH_ASSETS[tier]

        if slot_idx == 1:
            # Center slot — fish coming straight at the player
            filename = assets["front"]
            flip_h   = False
        else:
            filename = assets["side"]
            side_faces = assets["side_faces"]
            if slot_idx == 0:
                # LEFT slot — fish should face left on screen
                flip_h = (side_faces == "right")
            else:
                # RIGHT slot — fish should face right on screen
                flip_h = (side_faces == "left")

        max_w = max(1, int(rect.w * scale))
        max_h = max(1, int(rect.h * scale))
        surf  = asset_loader.load_image_fit(filename, max_w, max_h,
                                            base_dir=settings.TILES_DIR)
        if flip_h:
            surf = pygame.transform.flip(surf, True, False)
        img_x  = rect.x + (rect.w - surf.get_width()) // 2
        free_y = rect.h - surf.get_height()
        img_y  = rect.y + int(free_y * settings.TILE_VERTICAL_BIAS)
        self.screen.blit(surf, (img_x, img_y))

    # ----------------------------------------------------------
    #  Treasure collection
    # ----------------------------------------------------------

    def _try_collect_treasure(self, click_pos) -> bool:
        for tile, grid_pos, rect in self._get_slot_rects():
            if tile == TileType.TREASURE and rect.collidepoint(click_pos) and grid_pos:
                self.grid.set(grid_pos[0], grid_pos[1], TileType.EMPTY)
                base   = random.randint(settings.TREASURE_MIN_VALUE,
                                        settings.TREASURE_MAX_VALUE)
                earned = round(base * self.depth_multiplier)
                self._treasure_log.append({"base": base, "earned": earned})
                print(f"[Game] Treasure at {grid_pos}! "
                      f"{base} × {self.depth_multiplier} = {earned} shuckles")
                return True
        return False

    # ----------------------------------------------------------
    #  Extract button
    # ----------------------------------------------------------

    def _draw_extract_button(self) -> None:
        hovered = self._extract_rect.collidepoint(pygame.mouse.get_pos())
        r       = self._extract_rect
        if asset_loader.has_image(settings.BTN_ASSET_EXTRACT, settings.UI_DIR):
            surf = asset_loader.load_image_fit(
                settings.BTN_ASSET_EXTRACT, r.w, r.h, base_dir=settings.UI_DIR
            )
            if hovered:
                tint = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
                tint.fill((255, 255, 255, 40))
                surf = surf.copy()
                surf.blit(tint, (0, 0))
            self.screen.blit(surf, surf.get_rect(center=r.center))
        else:
            fill   = (60, 120, 20) if hovered else (30, 80, 10)
            border = (150, 255, 50)
            pygame.draw.rect(self.screen, fill,   r, border_radius=8)
            pygame.draw.rect(self.screen, border, r, width=2, border_radius=8)
            font = pygame.font.SysFont("monospace", 17, bold=True)
            text = font.render(f"[ EXTRACT  —  SCORE: {self.score} ]", True, (200, 255, 100))
            self.screen.blit(text, text.get_rect(center=r.center))

    # ----------------------------------------------------------
    #  Energy reduction helper (applies to scan, EMP, items)
    # ----------------------------------------------------------

    def _apply_energy_reduction(self, base_cost: int) -> int:
        """Apply Energy Upgrade tier reduction to any base energy cost."""
        if self._energy_upgrade_tier > 0:
            r = settings.ENERGY_UPGRADE_TIERS[self._energy_upgrade_tier - 1]["reduction"]
            return max(1, round(base_cost * (1 - r)))
        return base_cost

    # ----------------------------------------------------------
    #  Scan helpers
    # ----------------------------------------------------------

    def _radar_grid_size(self) -> int:
        """Returns the visual radar grid size (3 when inactive, 5 when enhanced scan active)."""
        if self.scan_moves_remaining > 0 and self._scan_enhanced:
            return settings.SCAN_UPGRADE_GRID
        return 3

    def _try_activate_scan(self) -> None:
        if self.scan_moves_remaining > 0:
            return

        if self._scanner_upgrade_uses > 0:
            cost = self._apply_energy_reduction(settings.SCAN_UPGRADE_ENERGY_COST)
            if self.energy < cost:
                self._show_hud_message(f"Not enough energy! Need {cost}E for enhanced scan.")
                return
            self.energy -= cost
            self.scan_moves_remaining  = settings.SCAN_UPGRADE_DURATION
            self._scan_enhanced        = True
            self._scanner_upgrade_uses -= 1
            _sv = save_manager.load()
            _sv["scanner_upgrade_uses"] = self._scanner_upgrade_uses
            save_manager.save(_sv)
            print(f"[Game] Enhanced scan — {settings.SCAN_UPGRADE_GRID}×"
                  f"{settings.SCAN_UPGRADE_GRID}, {settings.SCAN_UPGRADE_DURATION} moves. "
                  f"Energy: {self.energy} | Uses left: {self._scanner_upgrade_uses}")
        else:
            cost = self._apply_energy_reduction(settings.SCAN_ENERGY_COST)
            if self.energy < cost:
                self._show_hud_message(f"Not enough energy to scan! Need {cost}E.")
                return
            self.energy -= cost
            self.scan_moves_remaining = settings.SCAN_DURATION_MOVES
            self._scan_enhanced       = False
            print(f"[Game] Scan activated for {settings.SCAN_DURATION_MOVES} moves. "
                  f"Energy: {self.energy}")

    def _draw_scan_button(self) -> None:
        active  = self.scan_moves_remaining > 0
        hovered = self._scan_rect.collidepoint(pygame.mouse.get_pos())
        upg     = self._scanner_upgrade_uses > 0

        if active and self._scan_enhanced:
            fill, border = (0, 55, 80), (0, 200, 255)
            label    = f"ENHANCED SCAN  ({self.scan_moves_remaining} left)"
            text_col = (100, 210, 255)
        elif active:
            fill, border = (0, 80, 35), (0, 255, 100)
            label    = f"SCANNING  ({self.scan_moves_remaining} left)"
            text_col = (100, 255, 160)
        elif upg:
            cost = self._apply_energy_reduction(settings.SCAN_UPGRADE_ENERGY_COST)
            if self.energy >= cost:
                fill     = (15, 55, 100) if hovered else (8, 30, 65)
                border   = (0, 180, 255)
                label    = f"[ ENHANCED SCAN  -{cost}E  ★{self._scanner_upgrade_uses} ]"
                text_col = (140, 210, 255)
            else:
                fill, border = (30, 30, 40), (60, 60, 80)
                label    = "[ ENHANCED SCAN  —  NO ENERGY ]"
                text_col = (80, 80, 100)
        else:
            cost = self._apply_energy_reduction(settings.SCAN_ENERGY_COST)
            if self.energy >= cost:
                fill     = (20, 70, 120) if hovered else (10, 40, 80)
                border   = (0, 150, 200)
                label    = f"[ SCAN  -{cost}E ]"
                text_col = (180, 230, 255)
            else:
                fill, border = (30, 30, 40), (60, 60, 80)
                label    = "[ SCAN  —  NO ENERGY ]"
                text_col = (80, 80, 100)

        r = self._scan_rect
        if asset_loader.has_image(settings.BTN_ASSET_SCAN, settings.UI_DIR):
            # Use sonar.png as the button background; tint it by state
            btn_surf = asset_loader.load_image_fit(
                settings.BTN_ASSET_SCAN, r.w, r.h, base_dir=settings.UI_DIR
            )
            tint_surf = pygame.Surface(btn_surf.get_size(), pygame.SRCALPHA)
            if active and self._scan_enhanced:
                tint_surf.fill((0, 120, 200, 80))
            elif active:
                tint_surf.fill((0, 180, 80, 80))
            elif self.energy < (self._apply_energy_reduction(
                    settings.SCAN_UPGRADE_ENERGY_COST if upg else settings.SCAN_ENERGY_COST)):
                tint_surf.fill((80, 80, 80, 120))
            else:
                tint_surf.fill((255, 255, 255, 30) if hovered else (0, 0, 0, 0))
            btn_surf = btn_surf.copy()
            btn_surf.blit(tint_surf, (0, 0))
            self.screen.blit(btn_surf, btn_surf.get_rect(center=r.center))
        else:
            pygame.draw.rect(self.screen, fill,   r, border_radius=8)
            pygame.draw.rect(self.screen, border, r, width=2, border_radius=8)
        font = pygame.font.SysFont("monospace", 15, bold=True)
        text = font.render(label, True, text_col)
        self.screen.blit(text, text.get_rect(center=self._scan_rect.center))

    # ----------------------------------------------------------
    #  Radar
    # ----------------------------------------------------------

    def _draw_radar(self) -> None:
        PAD  = settings.RADAR_PADDING
        CELL = settings.RADAR_CELL_SIZE

        # Base scan active (text readout, not visual grid)
        if self.scan_moves_remaining > 0 and not self._scan_enhanced:
            self._draw_scan_text_panel()
            return

        GRID = self._radar_grid_size()
        HALF = GRID // 2
        SIZE = CELL * GRID

        ox = settings.SCREEN_WIDTH  - SIZE - PAD
        oy = settings.SCREEN_HEIGHT - SIZE - PAD

        bg = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        self.screen.blit(bg, (ox, oy))

        font    = pygame.font.SysFont("monospace", 16, bold=True)
        font_sm = pygame.font.SysFont("monospace", 10, bold=True)

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
        ICON_SZ = CELL - 6

        def _blit_icon(icon_key: str, center: tuple) -> bool:
            fname = settings.RADAR_ICONS.get(icon_key, "")
            if fname and asset_loader.has_image(fname, settings.UI_DIR):
                surf = asset_loader.load_image_fit(fname, ICON_SZ, ICON_SZ,
                                                   base_dir=settings.UI_DIR)
                self.screen.blit(surf, surf.get_rect(center=center))
                return True
            return False

        fish_map: dict[tuple, object] = {
            (f.x, f.y): f for f in self.fish_manager.fish
        }
        mine_map: dict[tuple, object] = {
            (m.x, m.y): m for m in self.mine_manager.mines
        }

        for row in range(GRID):
            for col in range(GRID):
                dx, dy    = col - HALF, row - HALF
                cell_rect = pygame.Rect(ox + col * CELL, oy + row * CELL, CELL, CELL)
                pygame.draw.rect(self.screen, (0, 60, 30), cell_rect, 1)

                gx, gy = self.player.x + dx, self.player.y + dy

                if dx == 0 and dy == 0:
                    if not _blit_icon(_PFACING[self.player.facing], cell_rect.center):
                        ts = font.render(_ARROW[self.player.facing], True, (255, 255, 0))
                        self.screen.blit(ts, ts.get_rect(center=cell_rect.center))

                elif (gx, gy) in mine_map:
                    mine = mine_map[(gx, gy)]
                    icon_key = "mine_trig" if mine.triggered else "mine"
                    if not _blit_icon(icon_key, cell_rect.center):
                        col_m = (255, 120, 0) if mine.triggered else (200, 200, 50)
                        inner = cell_rect.inflate(-6, -6)
                        pygame.draw.rect(self.screen, (60, 40, 0), inner, border_radius=3)
                        pygame.draw.circle(self.screen, col_m, cell_rect.center, CELL // 4)
                    if mine.triggered:
                        cd_s = font_sm.render(str(mine.countdown), True, (255, 80, 0))
                        self.screen.blit(cd_s, (cell_rect.left + 2, cell_rect.top + 2))

                elif (gx, gy) in fish_map:
                    fish = fish_map[(gx, gy)]
                    icon_key = "fish_stun" if fish.is_stunned else "fish"
                    if not _blit_icon(icon_key, cell_rect.center):
                        inner = cell_rect.inflate(-4, -4)
                        pygame.draw.rect(self.screen, (120, 0, 0), inner, border_radius=3)
                        pygame.draw.circle(self.screen, (255, 60, 60),
                                           cell_rect.center, CELL // 5)
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

        if self.scan_moves_remaining > 0:
            border_col = (0, 200, 255)   # enhanced scan = cyan
        else:
            border_col = settings.HUD_GREEN
        pygame.draw.rect(self.screen, border_col, (ox, oy, SIZE, SIZE), 2)

        # Spawn marker
        sx, sy = self.spawn_x - self.player.x, self.spawn_y - self.player.y
        if -HALF <= sx <= HALF and -HALF <= sy <= HALF:
            sc = pygame.Rect(
                ox + (sx + HALF) * CELL,
                oy + (sy + HALF) * CELL,
                CELL, CELL
            )
            pygame.draw.rect(self.screen, (200, 255, 100), sc, 2)

    def _draw_scan_text_panel(self) -> None:
        """Base scan active — show entity counts in a text panel (no visual grid)."""
        PAD  = settings.RADAR_PADDING
        CELL = settings.RADAR_CELL_SIZE
        # Same position as the 3×3 radar
        SIZE   = CELL * 3
        panel_w = SIZE + 24
        panel_h = SIZE
        ox = settings.SCREEN_WIDTH  - panel_w - PAD
        oy = settings.SCREEN_HEIGHT - panel_h - PAD

        r  = settings.SCAN_BASE_RANGE
        px, py = self.player.x, self.player.y

        fish_near = sum(
            1 for f in self.fish_manager.fish
            if abs(f.x - px) <= r and abs(f.y - py) <= r
        )
        mine_near = sum(
            1 for m in self.mine_manager.mines
            if abs(m.x - px) <= r and abs(m.y - py) <= r
        )
        treasure_near = sum(
            1
            for gy in range(max(0, py - r), min(self.grid.height, py + r + 1))
            for gx in range(max(0, px - r), min(self.grid.width,  px + r + 1))
            if self.grid.get(gx, gy) == TileType.TREASURE
        )

        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 200))
        self.screen.blit(bg, (ox, oy))
        pygame.draw.rect(self.screen, settings.HUD_GREEN, (ox, oy, panel_w, panel_h), 2)

        font    = pygame.font.SysFont("monospace", 13, bold=True)
        font_sm = pygame.font.SysFont("monospace", 11)
        cx_mid  = ox + panel_w // 2

        title = font.render(f"SCAN ({self.scan_moves_remaining})", True, (100, 255, 160))
        self.screen.blit(title, title.get_rect(center=(cx_mid, oy + 14)))

        rng_s = font_sm.render(f"Range {r*2+1}×{r*2+1}", True, (70, 130, 100))
        self.screen.blit(rng_s, rng_s.get_rect(center=(cx_mid, oy + 27)))

        entries = [
            (f"Fish:      {fish_near}",     (255, 80,  80)  if fish_near     else (80, 120, 100)),
            (f"Mines:     {mine_near}",     (255, 160,  0)  if mine_near     else (80, 120, 100)),
            (f"Treasure:  {treasure_near}", (220, 200, 50)  if treasure_near else (80, 120, 100)),
        ]
        for i, (txt, col) in enumerate(entries):
            s = font.render(txt, True, col)
            self.screen.blit(s, (ox + 6, oy + 40 + i * 20))

    # ----------------------------------------------------------
    #  Score + energy
    # ----------------------------------------------------------

    def _draw_score(self) -> None:
        font = pygame.font.SysFont("monospace", 20, bold=True)
        surf = font.render(f"SCORE: {self.score}", True, settings.HUD_GREEN)
        self.screen.blit(surf, surf.get_rect(topright=(settings.SCREEN_WIDTH - 10, 10)))

        run_font = pygame.font.SysFont("monospace", 15, bold=True)
        run_surf = run_font.render(
            f"Run {self._current_run} / {settings.RUNS_PER_GAME}",
            True, (100, 170, 220),
        )
        self.screen.blit(run_surf, run_surf.get_rect(topright=(settings.SCREEN_WIDTH - 10, 36)))

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
                self.state = _GAME_OVER if self._game_complete else _MENU
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._results_close.collidepoint(event.pos):
                    self.state = _GAME_OVER if self._game_complete else _MENU
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

        dim = pygame.Surface(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA
        )
        dim.fill((0, 0, 0, 170))
        self.screen.blit(dim, (0, 0))

        pygame.draw.rect(self.screen, (4, 18, 36),  p, border_radius=12)
        pygame.draw.rect(self.screen, settings.HUD_GREEN, p, width=2, border_radius=12)

        f_lg = pygame.font.SysFont("monospace", 24, bold=True)
        f_md = pygame.font.SysFont("monospace", 16, bold=True)
        f_sm = pygame.font.SysFont("monospace", 14)

        cx = p.centerx

        title = f_lg.render("EXTRACTION COMPLETE", True, settings.HUD_GREEN)
        self.screen.blit(title, title.get_rect(center=(cx, p.top + 28)))

        sub = f_sm.render(
            f"{self.menu.depth_label}  ·  {self.depth_multiplier}× Multiplier  "
            f"·  Run {self._current_run}/{settings.RUNS_PER_GAME}",
            True, (100, 170, 130),
        )
        self.screen.blit(sub, sub.get_rect(center=(cx, p.top + 56)))

        if self._game_complete:
            gc = f_lg.render("★  GAME COMPLETE  ★", True, (255, 215, 0))
            self.screen.blit(gc, gc.get_rect(center=(cx, p.top + 82)))

        hov = self._results_close.collidepoint(mouse)
        pygame.draw.rect(self.screen,
                         (130, 25, 25) if hov else (80, 10, 10),
                         self._results_close, border_radius=6)
        pygame.draw.rect(self.screen, (200, 60, 60),
                         self._results_close, width=1, border_radius=6)
        xt = f_md.render("✕", True, (255, 110, 110))
        self.screen.blit(xt, xt.get_rect(center=self._results_close.center))

        div1_y = p.top + (100 if self._game_complete else 72)
        pygame.draw.line(self.screen, (0, 90, 55),
                         (p.left + 20, div1_y), (p.right - 20, div1_y))

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

        div2_y = LIST_TOP + LIST_H + (22 if len(log) > VISIBLE else 12)
        pygame.draw.line(self.screen, (0, 90, 55),
                         (p.left + 20, div2_y), (p.right - 20, div2_y))

        foot_y  = div2_y + 10
        col_lbl = (100, 170, 130)

        lines = [
            f"Treasures collected:  {len(log)}",
            f"Shuckles earned:      {self._run_shuckles}",
        ]
        if self._run_harpoon_kills > 0:
            lines.append(
                f"Harpoon kills:  {self._run_harpoon_kills} × "
                f"{settings.HARPOON_KILL_SCORE} = "
                f"{self._run_harpoon_kills * settings.HARPOON_KILL_SCORE}"
            )
        lines.append(
            f"Depth clear bonus:    +{self._depth_bonus} score"
            f"  ({self.menu.depth_label})"
        )
        if self._shuckle_bonus > 0:
            lines.append(f"Shuckles → score:     +{self._shuckle_bonus}")

        for i, line in enumerate(lines):
            s = f_sm.render(line, True, col_lbl)
            self.screen.blit(s, (p.left + 30, foot_y + i * 18))

        total_txt = f_lg.render(f"TOTAL SCORE:  {self.score}", True, (255, 215, 0))
        self.screen.blit(total_txt, (p.left + 30, foot_y + len(lines) * 18 + 6))

    # ----------------------------------------------------------
    #  Game-over screen  (shown after all 5 runs are complete)
    # ----------------------------------------------------------

    def _tick_game_over(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                save_manager.reset()
                self._game_score_total = 0
                self._depths_tipped    = set()
                self.menu.reload_save()
                self.home_screen = HomeScreen(self.screen, self.hud_image)
                self.state = _HOME
                return

        self.screen.fill(settings.DARK_BLUE)
        self._draw_game_over_screen()
        pygame.display.flip()
        self.clock.tick(settings.FPS)

    def _draw_game_over_screen(self) -> None:
        overlay = pygame.Surface(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 10, 230))
        self.screen.blit(overlay, (0, 0))

        cx = settings.SCREEN_WIDTH  // 2
        cy = settings.SCREEN_HEIGHT // 2

        f_xl  = pygame.font.SysFont("monospace", 52, bold=True)
        f_lg  = pygame.font.SysFont("monospace", 28, bold=True)
        f_md  = pygame.font.SysFont("monospace", 18, bold=True)
        f_sm  = pygame.font.SysFont("monospace", 14)

        # Stars banner
        stars = f_lg.render("★  ★  ★  ★  ★", True, (255, 215, 0))
        self.screen.blit(stars, stars.get_rect(center=(cx, cy - 170)))

        # Title
        shadow = f_xl.render("GAME COMPLETE", True, (0, 0, 0))
        title  = f_xl.render("GAME COMPLETE", True, settings.HUD_GREEN)
        self.screen.blit(shadow, shadow.get_rect(center=(cx + 2, cy - 112)))
        self.screen.blit(title,  title.get_rect(center=(cx, cy - 114)))

        # Panel background
        PW, PH = 560, 220
        panel = pygame.Rect(cx - PW // 2, cy - 60, PW, PH)
        pygame.draw.rect(self.screen, (4, 18, 36),       panel, border_radius=12)
        pygame.draw.rect(self.screen, settings.HUD_GREEN, panel, width=2, border_radius=12)

        # Stats
        run_line = f_md.render(
            f"Runs completed:    {settings.RUNS_PER_GAME} / {settings.RUNS_PER_GAME}",
            True, (140, 210, 175),
        )
        shk_line = f_md.render(
            f"Shuckles earned:   {self._final_game_shuckles}",
            True, (140, 210, 175),
        )
        scr_line = f_lg.render(
            f"FINAL SCORE:  {self._final_game_score}",
            True, (255, 215, 0),
        )

        self.screen.blit(run_line, run_line.get_rect(center=(cx, panel.top + 48)))
        self.screen.blit(shk_line, shk_line.get_rect(center=(cx, panel.top + 82)))

        pygame.draw.line(self.screen, (0, 90, 55),
                         (panel.left + 24, panel.top + 110),
                         (panel.right - 24, panel.top + 110))

        self.screen.blit(scr_line, scr_line.get_rect(center=(cx, panel.top + 148)))

        # Prompt
        hint = f_sm.render("Press any key or click to return to home", True, (80, 120, 100))
        self.screen.blit(hint, hint.get_rect(center=(cx, panel.bottom + 30)))

    # ----------------------------------------------------------
    #  Dead state
    # ----------------------------------------------------------

    def _tick_dead(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                save_manager.reset()
                self._game_score_total = 0
                self._depths_tipped    = set()
                self.menu.reload_save()
                self.home_screen = HomeScreen(self.screen, self.hud_image)
                self.state = _HOME
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
            sub_text   = "Devoured in the deep."
        elif self._death_reason == "mine":
            title_text = "MINE EXPLOSION"
            sub_text   = "The naval mine claimed another submarine."
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
    #  Inventory use buttons
    # ----------------------------------------------------------

    def _get_inv_rects(self) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect]:
        CELL     = settings.RADAR_CELL_SIZE
        PAD      = settings.RADAR_PADDING
        GRID     = self._radar_grid_size()
        SIZE     = CELL * GRID
        radar_ox = settings.SCREEN_WIDTH - SIZE - PAD
        inv_w, inv_h, gap = 100, 38, 6
        inv_x    = radar_ox - inv_w - 10
        btn_bottom = settings.SCREEN_HEIGHT - PAD
        rects = [
            pygame.Rect(inv_x, btn_bottom - (i + 1) * inv_h - i * gap, inv_w, inv_h)
            for i in range(4)
        ]
        return rects[3], rects[2], rects[1], rects[0]

    def _draw_inventory_buttons(self) -> None:
        mouse = pygame.mouse.get_pos()
        font  = pygame.font.SysFont("monospace", 13, bold=True)
        harpoon_rect, emp_rect, battery_rect, romo_rect = self._get_inv_rects()

        emp_cost = self._apply_energy_reduction(settings.EMP_ENERGY_COST)
        items = [
            ("⚔ Harpoon", self.inv_harpoons, 3,  harpoon_rect, ""),
            (f"⚡ EMP",    self.inv_emp,      1,  emp_rect,     f"-{emp_cost}E"),
            ("🔋 Battery", self.inv_battery,  99, battery_rect, ""),
            ("★ Rescue",  self.inv_romo,     1,  romo_rect,    ""),
        ]

        for label, count, max_c, rect, cost_label in items:
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
            count_s = font.render(
                f"{count}/{max_c}" + (f" {cost_label}" if cost_label else ""),
                True, (255, 215, 0) if has else (60, 60, 80),
            )
            self.screen.blit(name_s,  name_s.get_rect(
                center=(rect.centerx, rect.centery - 8)))
            self.screen.blit(count_s, count_s.get_rect(
                center=(rect.centerx, rect.centery + 10)))

    # ----------------------------------------------------------
    #  Harpoon — mine-aware ray cast
    # ----------------------------------------------------------

    def _use_harpoon(self) -> None:
        if self.inv_harpoons <= 0:
            return
        self.inv_harpoons -= 1
        _sv = save_manager.load()
        _sv["harpoons"] = self.inv_harpoons
        save_manager.save(_sv)

        dx, dy = _DIR_DELTA[self.player.facing]
        x, y   = self.player.x + dx, self.player.y + dy
        hit    = False

        while True:
            tile = self.grid.get(x, y)
            if tile is None or tile == TileType.ROCK:
                break

            # Mine check (mine absorbs the shot and detonates)
            mine = self.mine_manager.get_mine_at(x, y)
            if mine:
                explosions = self.mine_manager.explode_mine(
                    mine, self.grid, self.fish_manager,
                    self.player.x, self.player.y,
                )
                self._handle_mine_explosions(explosions)
                hit = True
                print(f"[Game] Harpoon hit a MINE at ({x},{y})!")
                break

            # Fish check
            fish_hit = False
            for i, f in enumerate(self.fish_manager.fish):
                if f.x == x and f.y == y:
                    self.fish_manager.fish.pop(i)
                    self.score              += settings.HARPOON_KILL_SCORE
                    self._run_harpoon_kills += 1
                    fish_hit = True
                    print(f"[Game] Harpoon killed fish at ({x},{y})! "
                          f"+{settings.HARPOON_KILL_SCORE} | "
                          f"Harpoons left: {self.inv_harpoons}")
                    break
            if fish_hit:
                hit = True
                break

            x += dx
            y += dy

        if not hit:
            print(f"[Game] Harpoon missed! ({self.inv_harpoons} remaining)")

    # ----------------------------------------------------------
    #  EMP — stuns fish, extends mine timers, costs energy
    # ----------------------------------------------------------

    def _use_emp(self) -> None:
        if self.inv_emp <= 0:
            return
        cost = self._apply_energy_reduction(settings.EMP_ENERGY_COST)
        if self.energy < cost:
            self._show_hud_message(f"Not enough energy for EMP! Need {cost}E.")
            return

        self.inv_emp  -= 1
        self.energy   -= cost
        _sv = save_manager.load()
        _sv["emp_stun"] = 0
        save_manager.save(_sv)

        self.fish_manager.stun_radius(
            self.player.x, self.player.y,
            radius=1, duration=settings.EMP_STUN_DURATION,
        )
        mine_count = self.mine_manager.emp_extend(
            self.player.x, self.player.y,
            radius=1, amount=settings.EMP_MINE_EXTEND,
        )
        print(f"[Game] EMP! Fish stunned {settings.EMP_STUN_DURATION}a | "
              f"Mines extended +{settings.EMP_MINE_EXTEND}a ({mine_count} affected) | "
              f"Energy: {self.energy}")

    # ----------------------------------------------------------
    #  Battery pack
    # ----------------------------------------------------------

    def _use_battery_pack(self) -> None:
        if self.inv_battery <= 0:
            self._show_hud_message("Out of Energy Packs!")
            return
        self.inv_battery -= 1
        self.energy = settings.ENERGY_MAX
        _sv = save_manager.load()
        _sv["battery_pack"] = self.inv_battery
        save_manager.save(_sv)
        print(f"[Game] Battery Pack used — energy restored! ({self.inv_battery} remaining)")

    # ----------------------------------------------------------
    #  Romo's Rescue — instant extract from anywhere
    # ----------------------------------------------------------

    def _use_romo_rescue(self) -> None:
        if self.inv_romo <= 0:
            return
        self.inv_romo = 0
        _sv = save_manager.load()
        _sv["romo_rescue"]     = 0
        _sv["game_romo_bought"] = 1   # block repurchase for rest of game
        save_manager.save(_sv)
        print("[Game] Romo's Rescue activated — instant extraction!")
        self._do_extract()

    # ----------------------------------------------------------
    #  Shutdown
    # ----------------------------------------------------------

    def _quit(self) -> None:
        asset_loader.clear_cache()
        pygame.quit()
        print("[Game] Closed cleanly.")
