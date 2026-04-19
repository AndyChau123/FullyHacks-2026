# =============================================================
#  cutscene.py  —  Pre-game visual-novel style dialog
#
#  Two-character conversation between Uncle Romo and Cyndi
#  shown once at the start of a fresh game.
#
#  Click / Space / Enter  — advance one line
#  SKIP button / Escape   — jump straight to the game
#
#  Drop romo.png and cyndi.png into assets/images/ to replace
#  the placeholder silhouettes automatically.
# =============================================================

import pygame
import settings
import asset_loader

# ----- Dialog script ------------------------------------------
_DIALOG = [
    ("Uncle Romo", "Cyndi, please don't go, it's too dangerous. "
                   "The ocean will eat you alive, haven't my stories "
                   "convinced you enough."),
    ("Cyndi",      "You know I have to do this\u2026"),
    ("Cyndi",      "Doctor said your condition is getting worse and the "
                   "treatment isn't cheap. This is the only way."),
    ("Uncle Romo", "I told you I can figure it out. A man of my age can "
                   "take care of himself. I can't lose another one, your "
                   "father wouldn't even want this."),
    ("Cyndi",      "I'm sorry Uncle I have to go\u2026"),
    ("Uncle Romo", "\u2026"),
    ("Uncle Romo", "Haha\u2026 you always were like your father. "
                   "I guess there's no stopping you."),
    ("Uncle Romo", "Before you go, let me give you some tips\u2026"),
]

# ----- Character asset filenames (assets/images/) -------------
_ROMO_ASSET  = "romo.png"
_CYNDI_ASSET = "cyndi.png"

# ----- Colour palette -----------------------------------------
_ROMO_COL    = (100, 200, 255)
_CYNDI_COL   = (255, 160, 200)
_NAME_COLS   = {"Uncle Romo": _ROMO_COL, "Cyndi": _CYNDI_COL}

_PANEL_BG     = (  4,  18,  36)
_PANEL_BORDER = (  0, 200, 100)
_TEXT_COL     = (220, 230, 240)
_SKIP_FILL    = ( 25,  25,  45)
_SKIP_HOVER   = ( 45,  45,  75)
_SKIP_BORDER  = ( 80,  80, 120)
_SKIP_TEXT    = (160, 160, 210)

_PANEL_H   = 210   # dialog box height
_PANEL_PAD = 28    # inner horizontal padding
_CHAR_W    = 240   # character silhouette width
_CHAR_H    = 400   # character silhouette height


def _wrap(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
    """Word-wrap text to fit within max_w pixels."""
    words, lines, current = text.split(), [], ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# =============================================================

class Cutscene:
    """
    Visual-novel style pre-game dialog screen.

    handle_event() returns:
      "done"  — dialog finished or skipped; caller should start the game
      None    — still running
    """

    def __init__(self, screen: pygame.Surface, hud_image: pygame.Surface):
        self.screen    = screen
        self.hud_image = hud_image

        self._index = 0
        self._tick  = 0   # for blinking indicator

        self._font_name = None
        self._font_text = None
        self._font_hint = None
        self._font_skip = None
        self._font_char = None

        # Skip button — top right
        self._skip_rect = pygame.Rect(
            settings.SCREEN_WIDTH - 120, 14, 106, 34
        )

        # Dialog panel — bottom strip
        px = 30
        pw = settings.SCREEN_WIDTH - 60
        py = settings.SCREEN_HEIGHT - _PANEL_H - 18
        self._panel_rect = pygame.Rect(px, py, pw, _PANEL_H)

        # Character placement: Romo left, Cyndi right
        char_y = py - _CHAR_H - 10
        self._romo_rect  = pygame.Rect(
            100, char_y, _CHAR_W, _CHAR_H
        )
        self._cyndi_rect = pygame.Rect(
            settings.SCREEN_WIDTH - 100 - _CHAR_W, char_y, _CHAR_W, _CHAR_H
        )

    # ----------------------------------------------------------
    #  Event handling
    # ----------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._skip_rect.collidepoint(event.pos):
                return "done"
            return self._advance()

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                return self._advance()
            if event.key == pygame.K_ESCAPE:
                return "done"

        return None

    def _advance(self):
        self._index += 1
        if self._index >= len(_DIALOG):
            return "done"
        return None

    # ----------------------------------------------------------
    #  Drawing
    # ----------------------------------------------------------

    def draw(self) -> None:
        self._ensure_fonts()
        self._tick += 1
        mouse  = pygame.mouse.get_pos()
        speaker, _ = _DIALOG[self._index]

        # Background
        self.screen.fill(settings.DARK_BLUE)
        overlay = pygame.Surface(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 10, 210))
        self.screen.blit(overlay, (0, 0))

        # Characters
        self._draw_character(
            self._romo_rect,  "Uncle Romo", _ROMO_ASSET,
            active=(speaker == "Uncle Romo"),
        )
        self._draw_character(
            self._cyndi_rect, "Cyndi",      _CYNDI_ASSET,
            active=(speaker == "Cyndi"),
        )

        # Dialog panel
        self._draw_panel(speaker)

        # Skip button
        self._draw_skip(mouse)

    # ----------------------------------------------------------
    #  Character
    # ----------------------------------------------------------

    def _draw_character(self, rect: pygame.Rect, name: str,
                        asset: str, active: bool) -> None:
        col = _NAME_COLS[name]

        if asset_loader.has_image(asset, settings.IMAGES_DIR):
            surf = asset_loader.load_image_fit(
                asset, rect.width, rect.height,
                base_dir=settings.IMAGES_DIR,
            )
            self.screen.blit(surf, surf.get_rect(midbottom=rect.midbottom))
        else:
            # Placeholder silhouette — head + body
            hx, hy, hr = rect.centerx, rect.top + 65, 46
            pygame.draw.circle(self.screen, (18, 28, 48), (hx, hy), hr)
            pygame.draw.circle(self.screen, col,          (hx, hy), hr, width=2)

            body = pygame.Rect(rect.centerx - 52, rect.top + 104,
                               104, rect.height - 120)
            pygame.draw.rect(self.screen, (18, 28, 48), body, border_radius=20)
            pygame.draw.rect(self.screen, col,          body, width=2, border_radius=20)

            lbl = self._font_char.render(name, True, col)
            self.screen.blit(lbl, lbl.get_rect(center=(rect.centerx, rect.top + 30)))

        # Dim inactive speaker
        if not active:
            dim = pygame.Surface(rect.size, pygame.SRCALPHA)
            dim.fill((0, 0, 0, 165))
            self.screen.blit(dim, rect.topleft)

    # ----------------------------------------------------------
    #  Dialog panel
    # ----------------------------------------------------------

    def _draw_panel(self, speaker: str) -> None:
        p   = self._panel_rect
        col = _NAME_COLS.get(speaker, _TEXT_COL)

        pygame.draw.rect(self.screen, _PANEL_BG,     p, border_radius=12)
        pygame.draw.rect(self.screen, _PANEL_BORDER, p, width=2, border_radius=12)

        # Speaker name badge (sits above the panel)
        name_surf = self._font_name.render(speaker, True, col)
        badge_w   = name_surf.get_width() + 24
        badge_h   = name_surf.get_height() + 10
        badge     = pygame.Rect(p.left + _PANEL_PAD,
                                p.top - badge_h + 6, badge_w, badge_h)
        pygame.draw.rect(self.screen, _PANEL_BG, badge, border_radius=6)
        pygame.draw.rect(self.screen, col,        badge, width=2, border_radius=6)
        self.screen.blit(name_surf, name_surf.get_rect(center=badge.center))

        # Word-wrapped dialog text
        text   = _DIALOG[self._index][1]
        max_w  = p.width - _PANEL_PAD * 2
        lines  = _wrap(text, self._font_text, max_w)
        text_y = p.top + _PANEL_PAD + 6
        for line in lines:
            s = self._font_text.render(line, True, _TEXT_COL)
            self.screen.blit(s, (p.left + _PANEL_PAD, text_y))
            text_y += s.get_height() + 5

        # Blinking ▶ continue prompt
        if (self._tick // 28) % 2 == 0:
            hint = self._font_hint.render("▶  click to continue", True, (70, 110, 90))
            self.screen.blit(hint, hint.get_rect(
                bottomright=(p.right - _PANEL_PAD, p.bottom - 10)
            ))

        # Line counter
        prog = self._font_hint.render(
            f"{self._index + 1} / {len(_DIALOG)}", True, (55, 85, 65)
        )
        self.screen.blit(prog, prog.get_rect(
            bottomleft=(p.left + _PANEL_PAD, p.bottom - 10)
        ))

    # ----------------------------------------------------------
    #  Skip button
    # ----------------------------------------------------------

    def _draw_skip(self, mouse: tuple[int, int]) -> None:
        hov  = self._skip_rect.collidepoint(mouse)
        fill = _SKIP_HOVER if hov else _SKIP_FILL
        pygame.draw.rect(self.screen, fill,        self._skip_rect, border_radius=8)
        pygame.draw.rect(self.screen, _SKIP_BORDER, self._skip_rect, width=1, border_radius=8)
        txt = self._font_skip.render("SKIP  ▶▶", True, _SKIP_TEXT)
        self.screen.blit(txt, txt.get_rect(center=self._skip_rect.center))

    # ----------------------------------------------------------
    #  Lazy font init
    # ----------------------------------------------------------

    def _ensure_fonts(self) -> None:
        if self._font_name is None:
            self._font_name = pygame.font.SysFont("monospace", 20, bold=True)
            self._font_text = pygame.font.SysFont("monospace", 16)
            self._font_hint = pygame.font.SysFont("monospace", 12)
            self._font_skip = pygame.font.SysFont("monospace", 13, bold=True)
            self._font_char = pygame.font.SysFont("monospace", 14, bold=True)
