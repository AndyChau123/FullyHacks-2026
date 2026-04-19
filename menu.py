# =============================================================
#  menu.py  —  Main menu screen
#
#  Buttons are drawn programmatically now.
#  To replace any button with a PNG, drop the file into
#  assets/ui/ and set the matching asset_name on the button —
#  the draw() method will load it automatically.
# =============================================================

import pygame
import settings
import asset_loader
import save_manager

# ----- Colour palettes ---------------------------------------
_NORMAL    = ( 10,  40,  70)
_HOVER     = ( 20,  70, 110)
_PRESSED   = (  5,  25,  45)
_BORDER    = (  0, 150, 200)
_TEXT      = (180, 230, 255)
_SEL       = (  0,  70,  25)
_SEL_BDR   = (  0, 200,  80)

_SHOP_FILL   = ( 80,  55,   5)
_SHOP_HOVER  = (120,  85,  10)
_SHOP_BORDER = (220, 170,  40)
_SHOP_TEXT   = (255, 220,  80)

_RESET_FILL   = ( 80,  10,  10)
_RESET_HOVER  = (130,  20,  20)
_RESET_BORDER = (200,  50,  50)
_RESET_TEXT   = (255, 100, 100)


class _MenuButton:
    """
    A single menu button.  Draws itself programmatically unless
    asset_name is set AND the PNG exists in assets/ui/.
    """

    def __init__(self, rect: pygame.Rect, label: str,
                 value=None, asset_name: str | None = None,
                 fill=_NORMAL, hover=_HOVER, border=_BORDER, text_col=_TEXT):
        self.rect      = rect
        self.label     = label
        self.value     = value
        self.asset_name = asset_name
        self._fill     = fill
        self._hover    = hover
        self._border   = border
        self._text_col = text_col
        self._pressed  = False

    def draw(self, surface: pygame.Surface,
             font: pygame.font.Font,
             mouse_pos: tuple[int, int],
             selected: bool = False) -> None:

        if self.asset_name:
            surf = asset_loader.load_image_fit(
                self.asset_name, self.rect.w, self.rect.h,
                base_dir=settings.UI_DIR,
            )
            surface.blit(surf, self.rect.topleft)
            if selected:
                pygame.draw.rect(surface, _SEL_BDR, self.rect, width=3, border_radius=10)
            return

        hovered = self.rect.collidepoint(mouse_pos)
        if selected:
            fill, border = _SEL, _SEL_BDR
        elif self._pressed:
            fill, border = _PRESSED, self._border
        elif hovered:
            fill, border = self._hover, self._border
        else:
            fill, border = self._fill, self._border

        pygame.draw.rect(surface, fill,   self.rect, border_radius=10)
        pygame.draw.rect(surface, border, self.rect, width=2, border_radius=10)
        text = font.render(self.label, True, self._text_col)
        surface.blit(text, text.get_rect(center=self.rect.center))

    def handle_click(self, pos: tuple[int, int]):
        if self.rect.collidepoint(pos):
            self._pressed = True
            return self.value
        return None

    def handle_release(self) -> None:
        self._pressed = False


# =============================================================

class Menu:
    """
    Main menu.  handle_event() returns:
      "play"  — start a game with .grid_size
      "shop"  — open shop (not yet implemented)
      None    — no action
    """

    def __init__(self, screen: pygame.Surface, hud_image: pygame.Surface):
        self.screen    = screen
        self.hud_image = hud_image
        self._save     = save_manager.load()

        self._font_title = None
        self._font_btn   = None
        self._font_sub   = None
        self._font_save  = None

        cx = settings.SCREEN_WIDTH  // 2
        cy = settings.SCREEN_HEIGHT // 2

        # ----- Depth selector buttons -----
        depths  = list(settings.DEPTHS.items())
        GBW, GBH, GAP = 140, 60, 16
        total_w = GBW * len(depths) + GAP * (len(depths) - 1)
        gx = cx - total_w // 2
        gy = cy - GBH // 2

        self.grid_size   = depths[0][1]
        self.depth_label = depths[0][0]   # e.g. "Depth 1"

        self._grid_btns: list[_MenuButton] = [
            _MenuButton(
                pygame.Rect(gx + i * (GBW + GAP), gy, GBW, GBH),
                label, value=size, asset_name=None,
            )
            for i, (label, size) in enumerate(depths)
        ]

        # ----- PLAY + SHOP buttons (side by side below depth) -----
        ABW, ABH = 220, 65
        btn_y = gy + GBH + 36
        self._play_btn = _MenuButton(
            pygame.Rect(cx - ABW - 10, btn_y, ABW, ABH),
            "▶   PLAY", value="play", asset_name=None,
        )
        self._shop_btn = _MenuButton(
            pygame.Rect(cx + 10, btn_y, ABW, ABH),
            "⚙   SHOP", value="shop", asset_name=None,
            fill=_SHOP_FILL, hover=_SHOP_HOVER,
            border=_SHOP_BORDER, text_col=_SHOP_TEXT,
        )

        # ----- Top-right save panel + reset button -----
        # Reset (X) button — top right corner
        self._reset_rect = pygame.Rect(
            settings.SCREEN_WIDTH - 42, 12, 30, 30
        )
        # Save info panel sits to the left of the X button
        self._save_panel_rect = pygame.Rect(
            settings.SCREEN_WIDTH - 42 - 220 - 8, 12, 220, 30
        )

    # ----------------------------------------------------------
    #  Save management
    # ----------------------------------------------------------

    def reload_save(self) -> None:
        """Call this after returning from a game run so score refreshes."""
        self._save = save_manager.load()

    # ----------------------------------------------------------
    #  Event handling
    # ----------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Reset save
            if self._reset_rect.collidepoint(event.pos):
                self._save = save_manager.reset()
                return None

            # Depth selection
            for btn in self._grid_btns:
                val = btn.handle_click(event.pos)
                if val:
                    self.grid_size   = val
                    self.depth_label = btn.label

            # Action buttons
            if (val := self._play_btn.handle_click(event.pos)):
                return val
            if (val := self._shop_btn.handle_click(event.pos)):
                return val

        if event.type == pygame.MOUSEBUTTONUP:
            for btn in self._grid_btns:
                btn.handle_release()
            self._play_btn.handle_release()
            self._shop_btn.handle_release()

        return None

    # ----------------------------------------------------------
    #  Drawing
    # ----------------------------------------------------------

    def draw(self) -> None:
        self._ensure_fonts()
        mouse = pygame.mouse.get_pos()

        # Background
        self.screen.blit(self.hud_image, (0, 0))
        overlay = pygame.Surface(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 20, 190))
        self.screen.blit(overlay, (0, 0))

        cx = settings.SCREEN_WIDTH // 2

        # Title
        title = self._font_title.render("DEEP  DIVE", True, settings.HUD_GREEN)
        self.screen.blit(title, title.get_rect(center=(cx, 190)))

        # Depth label + buttons
        sub = self._font_sub.render("SELECT DEPTH", True, (90, 160, 120))
        gy  = self._grid_btns[0].rect.top
        self.screen.blit(sub, sub.get_rect(center=(cx, gy - 28)))
        for btn in self._grid_btns:
            btn.draw(self.screen, self._font_btn, mouse,
                     selected=(btn.value == self.grid_size))

        # PLAY + SHOP
        self._play_btn.draw(self.screen, self._font_btn, mouse)
        self._shop_btn.draw(self.screen, self._font_btn, mouse)

        # Save panel (top right)
        self._draw_save_panel(mouse)

    def _draw_save_panel(self, mouse: tuple[int, int]) -> None:
        # Info panel background
        pygame.draw.rect(self.screen, (5, 20, 40),
                         self._save_panel_rect, border_radius=6)
        pygame.draw.rect(self.screen, (0, 80, 60),
                         self._save_panel_rect, width=1, border_radius=6)

        score_txt = self._font_save.render(
            f"SCORE: {self._save['total_score']}   "
            f"RUNS: {self._save['runs_completed']}",
            True, settings.HUD_GREEN,
        )
        self.screen.blit(
            score_txt,
            score_txt.get_rect(midleft=(self._save_panel_rect.left + 8,
                                        self._save_panel_rect.centery)),
        )

        # Reset (X) button
        hovered = self._reset_rect.collidepoint(mouse)
        fill   = _RESET_HOVER if hovered else _RESET_FILL
        pygame.draw.rect(self.screen, fill,         self._reset_rect, border_radius=6)
        pygame.draw.rect(self.screen, _RESET_BORDER, self._reset_rect, width=1, border_radius=6)
        x_surf = self._font_save.render("✕", True, _RESET_TEXT)
        self.screen.blit(x_surf, x_surf.get_rect(center=self._reset_rect.center))

    def _ensure_fonts(self) -> None:
        if self._font_title is None:
            self._font_title = pygame.font.SysFont("monospace", 58, bold=True)
            self._font_btn   = pygame.font.SysFont("monospace", 22, bold=True)
            self._font_sub   = pygame.font.SysFont("monospace", 15)
            self._font_save  = pygame.font.SysFont("monospace", 13, bold=True)
