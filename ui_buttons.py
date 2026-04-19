# =============================================================
#  ui_buttons.py  —  On-screen directional control buttons
#
#  Draws four buttons at the bottom of the HUD:
#      [ ↺ Turn Left ]   [ ▲ Forward ]   [ ↻ Turn Right ]
#
#  Call draw(screen) every frame.
#  Call handle_click(pos) on MOUSEBUTTONDOWN events — returns
#  an action string or None.
# =============================================================

import pygame
import settings


# ------ Layout constants -------------------------------------
# Button sizes and positions (bottom-centre of screen)
BTN_W        = 130
BTN_H        = 48
BTN_GAP      = 12
BTN_Y        = settings.SCREEN_HEIGHT - BTN_H - settings.SCAN_BTN_H - settings.SCAN_BTN_BOTTOM_PAD - 12

# Centre the three buttons horizontally
_TOTAL_W     = BTN_W * 3 + BTN_GAP * 2
_START_X     = (settings.SCREEN_WIDTH - _TOTAL_W) // 2

# ------ Colours ----------------------------------------------
COL_NORMAL   = (10,  40,  70)
COL_HOVER    = (20,  70,  110)
COL_PRESSED  = (5,   25,  45)
COL_BORDER   = (0,   150, 200)
COL_TEXT     = (180, 230, 255)
COL_DISABLED = (30,  40,  50)


# ------ Action identifiers -----------------------------------
ACTION_LEFT    = "rotate_left"
ACTION_FORWARD = "move_forward"
ACTION_RIGHT   = "rotate_right"


class _Button:
    def __init__(self, x: int, y: int, w: int, h: int,
                 label: str, action: str):
        self.rect   = pygame.Rect(x, y, w, h)
        self.label  = label
        self.action = action
        self._pressed = False

    def draw(self, surface: pygame.Surface,
             font: pygame.font.Font,
             mouse_pos: tuple[int, int],
             disabled: bool = False) -> None:

        hovered = self.rect.collidepoint(mouse_pos) and not disabled

        if disabled:
            fill = COL_DISABLED
        elif self._pressed:
            fill = COL_PRESSED
        elif hovered:
            fill = COL_HOVER
        else:
            fill = COL_NORMAL

        pygame.draw.rect(surface, fill,        self.rect, border_radius=8)
        pygame.draw.rect(surface, COL_BORDER,  self.rect, width=1, border_radius=8)

        col   = COL_DISABLED if disabled else COL_TEXT
        text  = font.render(self.label, True, col)
        trect = text.get_rect(center=self.rect.center)
        surface.blit(text, trect)

    def contains(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


class DirectionButtons:
    """
    The three on-screen movement buttons.

    Usage (inside Game)
    -------------------
        self.buttons = DirectionButtons()

        # in _handle_events:
        if event.type == pygame.MOUSEBUTTONDOWN:
            action = self.buttons.handle_click(event.pos)
            if action == ACTION_LEFT:    player.rotate(-1)
            if action == ACTION_FORWARD: player.move_forward(grid)
            if action == ACTION_RIGHT:   player.rotate(1)

        if event.type == pygame.MOUSEBUTTONUP:
            self.buttons.handle_release()

        # in _draw:
        self.buttons.draw(screen)
    """

    def __init__(self):
        self._font = None   # initialised lazily after pygame.init()

        x = _START_X
        self._buttons = [
            _Button(x,                       BTN_Y, BTN_W, BTN_H,
                    "< Turn Left",  ACTION_LEFT),
            _Button(x + BTN_W + BTN_GAP,     BTN_Y, BTN_W, BTN_H,
                    "^ Forward",    ACTION_FORWARD),
            _Button(x + (BTN_W + BTN_GAP)*2, BTN_Y, BTN_W, BTN_H,
                    "Turn Right >", ACTION_RIGHT),
        ]

    # ----------------------------------------------------------

    def handle_click(self, pos: tuple[int, int]) -> str | None:
        """
        Call on MOUSEBUTTONDOWN.
        Returns an ACTION_* string if a button was hit, else None.
        """
        for btn in self._buttons:
            if btn.contains(pos):
                btn._pressed = True
                return btn.action
        return None

    def handle_release(self) -> None:
        """Call on MOUSEBUTTONUP to clear pressed state."""
        for btn in self._buttons:
            btn._pressed = False

    def draw(self, surface: pygame.Surface,
             mouse_pos: tuple[int, int] | None = None) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 16, bold=True)
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()
        for btn in self._buttons:
            btn.draw(surface, self._font, mouse_pos)