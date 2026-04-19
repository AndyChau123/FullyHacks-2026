# =============================================================
#  home_screen.py  —  Title / home screen shown on launch
#
#  Three buttons: START GAME → depth-select menu
#                 OPTIONS    → options overlay (save reset)
#                 HOW TO PLAY → controls / tips overlay
# =============================================================

import pygame
import settings
import asset_loader
import save_manager

# ----- Colour palettes ----------------------------------------
_NORMAL    = ( 10,  40,  70)
_HOVER     = ( 20,  70, 110)
_PRESSED   = (  5,  25,  45)
_BORDER    = (  0, 150, 200)
_TEXT      = (180, 230, 255)

_OPT_FILL   = ( 10,  40,  55)
_OPT_HOVER  = ( 20,  65,  85)
_OPT_BORDER = (  0, 120, 160)
_OPT_TEXT   = (140, 200, 230)

_INFO_FILL   = (  8,  30,  50)
_INFO_HOVER  = ( 15,  55,  80)
_INFO_BORDER = (  0, 100, 140)
_INFO_TEXT   = (120, 185, 220)

_QUIT_FILL   = ( 60,   8,   8)
_QUIT_HOVER  = (110,  18,  18)
_QUIT_BORDER = (180,  40,  40)
_QUIT_TEXT   = (240,  90,  90)

_RESET_FILL   = ( 80,  10,  10)
_RESET_HOVER  = (130,  20,  20)
_RESET_BORDER = (200,  50,  50)
_RESET_TEXT   = (255, 100, 100)

_PANEL_BG     = (  4,  18,  36)
_PANEL_BORDER = (  0, 200, 100)


class _HomeButton:
    """Single home-screen button — programmatic draw, PNG asset optional."""

    def __init__(self, rect: pygame.Rect, label: str, value: str,
                 asset_name: str | None = None,
                 fill=_NORMAL, hover=_HOVER, border=_BORDER, text_col=_TEXT):
        self.rect       = rect
        self.label      = label
        self.value      = value
        self.asset_name = asset_name
        self._fill      = fill
        self._hover     = hover
        self._border    = border
        self._text_col  = text_col
        self._pressed   = False

    def draw(self, surface: pygame.Surface,
             font: pygame.font.Font,
             mouse_pos: tuple[int, int]) -> None:

        hovered = self.rect.collidepoint(mouse_pos)

        if self.asset_name and asset_loader.has_image(self.asset_name, settings.UI_DIR):
            surf = asset_loader.load_image_fit(
                self.asset_name, self.rect.width, self.rect.height,
                base_dir=settings.UI_DIR,
            )
            surface.blit(surf, surf.get_rect(center=self.rect.center))
            if hovered:
                tint = pygame.Surface(self.rect.size, pygame.SRCALPHA)
                tint.fill((255, 255, 255, 30))
                surface.blit(tint, self.rect.topleft)
            return

        if self._pressed:
            fill = _PRESSED
        elif hovered:
            fill = self._hover
        else:
            fill = self._fill

        pygame.draw.rect(surface, fill,         self.rect, border_radius=12)
        pygame.draw.rect(surface, self._border, self.rect, width=2, border_radius=12)
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

class HomeScreen:
    """
    Title / home screen shown on launch.

    handle_event() returns:
      "start"  — proceed to the depth-select menu
      None     — no action (overlays handled internally)
    """

    def __init__(self, screen: pygame.Surface, hud_image: pygame.Surface):
        self.screen    = screen
        self.hud_image = hud_image

        self._font_title = None
        self._font_btn   = None
        self._font_sub   = None
        self._font_body  = None
        self._font_sm    = None

        self._show_instructions = False
        self._show_options      = False

        cx  = settings.SCREEN_WIDTH  // 2
        BTW = 260   # button width
        BTH = 65    # button height
        GAP = 18    # gap between buttons
        bx  = cx - BTW // 2
        by  = 340   # top of first button

        self._start_btn = _HomeButton(
            pygame.Rect(bx, by,                   BTW, BTH),
            "▶   START GAME", value="start",
        )
        self._opts_btn = _HomeButton(
            pygame.Rect(bx, by + BTH + GAP,       BTW, BTH),
            "⚙   OPTIONS",    value="options",
            fill=_OPT_FILL, hover=_OPT_HOVER,
            border=_OPT_BORDER, text_col=_OPT_TEXT,
        )
        self._info_btn = _HomeButton(
            pygame.Rect(bx, by + (BTH + GAP) * 2, BTW, BTH),
            "?   HOW TO PLAY", value="instructions",
            fill=_INFO_FILL, hover=_INFO_HOVER,
            border=_INFO_BORDER, text_col=_INFO_TEXT,
        )
        self._quit_btn = _HomeButton(
            pygame.Rect(bx, by + (BTH + GAP) * 3, BTW, BTH),
            "✕   QUIT",        value="quit",
            fill=_QUIT_FILL, hover=_QUIT_HOVER,
            border=_QUIT_BORDER, text_col=_QUIT_TEXT,
        )
        self._buttons = [self._start_btn, self._opts_btn, self._info_btn, self._quit_btn]

        # Overlay panels — centred on screen
        PW, PH = 620, 460
        px = (settings.SCREEN_WIDTH  - PW) // 2
        py = (settings.SCREEN_HEIGHT - PH) // 2
        self._panel_rect  = pygame.Rect(px, py, PW, PH)
        self._panel_close = pygame.Rect(px + PW - 42, py + 10, 30, 30)

        # Reset button inside options panel
        self._reset_rect = pygame.Rect(cx - 100, py + 195, 200, 44)

    # ----------------------------------------------------------
    #  Event handling
    # ----------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        overlay_open = self._show_instructions or self._show_options

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if overlay_open:
                self._show_instructions = False
                self._show_options      = False
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if overlay_open:
                if self._panel_close.collidepoint(event.pos):
                    self._show_instructions = False
                    self._show_options      = False
                elif self._show_options and self._reset_rect.collidepoint(event.pos):
                    save_manager.reset()
                return None

            for btn in self._buttons:
                val = btn.handle_click(event.pos)
                if val == "start":
                    return "start"
                if val == "quit":
                    return "quit"
                if val == "options":
                    self._show_options      = True
                    self._show_instructions = False
                if val == "instructions":
                    self._show_instructions = True
                    self._show_options      = False

        if event.type == pygame.MOUSEBUTTONUP:
            for btn in self._buttons:
                btn.handle_release()

        return None

    # ----------------------------------------------------------
    #  Drawing
    # ----------------------------------------------------------

    def draw(self) -> None:
        self._ensure_fonts()
        mouse = pygame.mouse.get_pos()

        # Background — use depth_select art if available, else HUD + dark overlay
        self.screen.fill(settings.DARK_BLUE)
        if asset_loader.has_image(settings.DEPTH_SELECT_BG, settings.IMAGES_DIR):
            bg = asset_loader.load_image(
                settings.DEPTH_SELECT_BG,
                size=(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT),
                base_dir=settings.IMAGES_DIR,
            )
            self.screen.blit(bg, (0, 0))
        else:
            self.screen.blit(self.hud_image, (0, 0))

        overlay = pygame.Surface(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 20, 210))
        self.screen.blit(overlay, (0, 0))

        cx = settings.SCREEN_WIDTH // 2

        # Title
        shadow = self._font_title.render("DEEP  DIVE", True, (0, 0, 0))
        title  = self._font_title.render("DEEP  DIVE", True, settings.HUD_GREEN)
        self.screen.blit(shadow, shadow.get_rect(center=(cx + 2, 187)))
        self.screen.blit(title,  title.get_rect(center=(cx, 185)))

        # Tagline
        sub = self._font_sub.render(
            "Descend. Collect. Survive.", True, (60, 140, 100)
        )
        self.screen.blit(sub, sub.get_rect(center=(cx, 255)))

        # Buttons (hidden while an overlay is open)
        if not self._show_instructions and not self._show_options:
            for btn in self._buttons:
                btn.draw(self.screen, self._font_btn, mouse)

        # Overlays
        if self._show_instructions:
            self._draw_instructions_overlay(mouse)
        elif self._show_options:
            self._draw_options_overlay(mouse)

    # ----------------------------------------------------------
    #  Instructions overlay
    # ----------------------------------------------------------

    def _draw_instructions_overlay(self, mouse: tuple[int, int]) -> None:
        p = self._panel_rect
        self._draw_panel_base(p, "HOW TO PLAY", mouse)

        lx = p.left + 36
        y  = p.top + 72

        sections = [
            ("Movement", [
                ("W  /  ↑",    "Move forward"),
                ("A  /  ←",    "Turn left"),
                ("D  /  →",    "Turn right"),
            ]),
            ("Actions", [
                ("Click tile",  "Collect treasure when in view"),
                ("EXTRACT",     "Surface at spawn tile to bank score"),
                ("SCAN",        "Reveal a 5×5 radar for 3 moves"),
            ]),
            ("Items", [
                ("Harpoon",     "Strike a fish from range"),
                ("EMP",         "Stun fish + extend mine timers in 3×3"),
                ("Romo's Rescue", "Instantly extract from anywhere"),
            ]),
            ("Tips", [
                ("Escape",      "Return to menu mid-run"),
                ("Energy",      "Every action costs 1 energy"),
                ("Depth",       "Higher depths = tougher + more rewards"),
            ]),
        ]

        for heading, rows in sections:
            h_surf = self._font_body.render(heading.upper(), True, settings.HUD_GREEN)
            self.screen.blit(h_surf, (lx, y))
            y += 26
            for key, desc in rows:
                line = self._font_sm.render(f"  {key:<18}  {desc}", True, (140, 210, 175))
                self.screen.blit(line, (lx, y))
                y += 20
            y += 8

    # ----------------------------------------------------------
    #  Options overlay
    # ----------------------------------------------------------

    def _draw_options_overlay(self, mouse: tuple[int, int]) -> None:
        p  = self._panel_rect
        cx = p.centerx
        self._draw_panel_base(p, "OPTIONS", mouse)

        sv   = save_manager.load()
        info = self._font_sm.render(
            f"Score: {sv['total_score']}   "
            f"Runs: {sv['runs_completed']}   "
            f"Shuckles: {sv.get('shuckles', 0)}",
            True, (100, 170, 130),
        )
        self.screen.blit(info, info.get_rect(center=(cx, p.top + 105)))

        label = self._font_body.render("Save Data", True, (140, 210, 175))
        self.screen.blit(label, label.get_rect(center=(cx, p.top + 148)))

        # Reset button
        hov  = self._reset_rect.collidepoint(mouse)
        fill = _RESET_HOVER if hov else _RESET_FILL
        pygame.draw.rect(self.screen, fill,          self._reset_rect, border_radius=8)
        pygame.draw.rect(self.screen, _RESET_BORDER, self._reset_rect, width=2, border_radius=8)
        btn_txt = self._font_btn.render("✕  Reset Save Data", True, _RESET_TEXT)
        self.screen.blit(btn_txt, btn_txt.get_rect(center=self._reset_rect.center))

        hint = self._font_sm.render(
            "This permanently deletes your score and shuckles.",
            True, (100, 80, 80),
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, self._reset_rect.bottom + 16)))

    # ----------------------------------------------------------
    #  Shared panel background + close button
    # ----------------------------------------------------------

    def _draw_panel_base(self, p: pygame.Rect,
                         title: str, mouse: tuple[int, int]) -> None:
        dim = pygame.Surface(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA
        )
        dim.fill((0, 0, 0, 160))
        self.screen.blit(dim, (0, 0))

        pygame.draw.rect(self.screen, _PANEL_BG,     p, border_radius=12)
        pygame.draw.rect(self.screen, _PANEL_BORDER, p, width=2, border_radius=12)

        t = self._font_btn.render(title, True, settings.HUD_GREEN)
        self.screen.blit(t, t.get_rect(center=(p.centerx, p.top + 28)))

        pygame.draw.line(self.screen, (0, 90, 55),
                         (p.left + 20, p.top + 52), (p.right - 20, p.top + 52))

        # Close (✕) button
        hov = self._panel_close.collidepoint(mouse)
        pygame.draw.rect(self.screen,
                         (130, 25, 25) if hov else (80, 10, 10),
                         self._panel_close, border_radius=6)
        pygame.draw.rect(self.screen, (200, 60, 60),
                         self._panel_close, width=1, border_radius=6)
        x_surf = self._font_btn.render("✕", True, (255, 110, 110))
        self.screen.blit(x_surf, x_surf.get_rect(center=self._panel_close.center))

    # ----------------------------------------------------------
    #  Lazy font initialisation
    # ----------------------------------------------------------

    def _ensure_fonts(self) -> None:
        if self._font_title is None:
            self._font_title = pygame.font.SysFont("monospace", 58, bold=True)
            self._font_btn   = pygame.font.SysFont("monospace", 20, bold=True)
            self._font_sub   = pygame.font.SysFont("monospace", 17)
            self._font_body  = pygame.font.SysFont("monospace", 15, bold=True)
            self._font_sm    = pygame.font.SysFont("monospace", 13, bold=True)
