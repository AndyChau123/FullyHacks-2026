# =============================================================
#  menu.py  —  Main menu screen
#
#  Background: depth_select.png (ocean cross-section with depth layers).
#  Depth buttons sit IN each blue layer band.
#  PLAY and SHOP are at the bottom centre.
# =============================================================

import pygame
import settings
import asset_loader
import save_manager

_SHOP_FILL   = ( 80,  55,   5)
_SHOP_HOVER  = (120,  85,  10)
_SHOP_BORDER = (220, 170,  40)
_SHOP_TEXT   = (255, 220,  80)


_NORMAL = ( 10,  40,  70)
_HOVER  = ( 20,  70, 110)
_BORDER = (  0, 150, 200)
_TEXT   = (180, 230, 255)
_SEL    = (  0,  70,  25)
_SEL_BDR = (  0, 200,  80)


class _MenuButton:
    """Generic menu button — uses PNG asset if available, else drawn programmatically."""

    def __init__(self, rect: pygame.Rect, label: str,
                 value=None, asset_name: str | None = None,
                 asset_hover: str | None = None,
                 fill=_NORMAL, hover=_HOVER, border=_BORDER, text_col=_TEXT):
        self.rect        = rect
        self.label       = label
        self.value       = value
        self.asset_name  = asset_name
        self.asset_hover = asset_hover
        self._fill       = fill
        self._hover      = hover
        self._border     = border
        self._text_col   = text_col
        self._pressed    = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font,
             mouse_pos: tuple[int, int], selected: bool = False) -> None:

        hovered = self.rect.collidepoint(mouse_pos)
        if self.asset_name and asset_loader.has_image(self.asset_name, settings.UI_DIR):
            # Use hover asset if available and mouse is over button
            fname = self.asset_name
            if hovered and self.asset_hover and asset_loader.has_image(self.asset_hover, settings.UI_DIR):
                fname = self.asset_hover
            surf = asset_loader.load_image_fit(
                fname, self.rect.w, self.rect.h,
                base_dir=settings.UI_DIR,
            )
            blit_pos = surf.get_rect(center=self.rect.center)
            surface.blit(surf, blit_pos)
            if selected:
                pygame.draw.rect(surface, _SEL_BDR,
                                 surf.get_rect(center=self.rect.center),
                                 width=3, border_radius=50)
            return

        hovered = self.rect.collidepoint(mouse_pos)
        if selected:
            fill, border = _SEL, _SEL_BDR
        elif hovered:
            fill, border = self._hover, self._border
        else:
            fill, border = self._fill, self._border

        pygame.draw.rect(surface, fill,   self.rect, border_radius=12)
        pygame.draw.rect(surface, border, self.rect, width=2, border_radius=12)
        text = font.render(self.label, True, self._text_col)
        surface.blit(text, text.get_rect(center=self.rect.center))

    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            self._pressed = True
            return self.value
        return None

    def handle_release(self):
        self._pressed = False


# =============================================================

# Depth button centres in the depth_select.png ocean layers.
# These positions place each circular button inside the matching
# blue depth band when the image is scaled to 1024×768.
# (x, y) = centre of the button.  Tune visually if needed.
_DEPTH_BTN_CENTERS = {
    "Depth 1": (590, 235),
    "Depth 2": (710, 360),
    "Depth 3": (840, 468),
    "Depth 4": (958, 572),
}
_DEPTH_BTN_SIZE = 84   # square bounding box for the circular asset


class Menu:
    """
    Main menu.  handle_event() returns "play" or "shop" or None.
    """

    def __init__(self, screen: pygame.Surface, hud_image: pygame.Surface):
        self.screen    = screen
        self.hud_image = hud_image
        self._save     = save_manager.load()

        self._font_title = None
        self._font_btn   = None
        self._font_sub   = None


        cx = settings.SCREEN_WIDTH  // 2
        cy = settings.SCREEN_HEIGHT // 2

        # ----- Depth selector buttons --------------------------------
        depths = list(settings.DEPTHS.items())
        self.grid_size   = depths[0][1]
        self.depth_label = depths[0][0]

        S = _DEPTH_BTN_SIZE
        self._grid_btns: list[_MenuButton] = []
        for label, size in depths:
            bcx, bcy = _DEPTH_BTN_CENTERS.get(label, (cx, cy))
            asset = settings.BTN_ASSET_DEPTH.get(label)
            self._grid_btns.append(_MenuButton(
                pygame.Rect(bcx - S // 2, bcy - S // 2, S, S),
                label, value=size, asset_name=asset,
            ))

        # ----- PLAY + SHOP buttons (bottom-centre) -------------------
        PBW, PBH = 160, 160   # play button — square to keep submarine proportions
        ABW, ABH = 200, 58    # shop button
        btn_y    = settings.SCREEN_HEIGHT - PBH - 18
        self._play_btn = _MenuButton(
            pygame.Rect(cx - PBW - 20, btn_y, PBW, PBH),
            "PLAY", value="play",
            asset_name=settings.BTN_ASSET_PLAY,
            asset_hover=settings.BTN_ASSET_PLAY_HOVER,
        )
        self._shop_btn = _MenuButton(
            pygame.Rect(cx + 20, btn_y + (PBH - ABH) // 2, ABW, ABH),
            "⚙  SHOP", value="shop", asset_name=None,
            fill=_SHOP_FILL, hover=_SHOP_HOVER,
            border=_SHOP_BORDER, text_col=_SHOP_TEXT,
        )


    # ----------------------------------------------------------

    def reload_save(self) -> None:
        self._save = save_manager.load()

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self._grid_btns:
                val = btn.handle_click(event.pos)
                if val:
                    self.grid_size   = val
                    self.depth_label = btn.label
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

        # 1. Ocean depth-select background (full screen)
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
            overlay.fill((0, 0, 20, 190))
            self.screen.blit(overlay, (0, 0))

        # 2. Title
        title = self._font_title.render("DEEP  DIVE", True, settings.HUD_GREEN)
        shadow = self._font_title.render("DEEP  DIVE", True, (0, 0, 0))
        self.screen.blit(shadow, shadow.get_rect(center=(settings.SCREEN_WIDTH // 2 + 2, 72)))
        self.screen.blit(title,  title.get_rect(center=(settings.SCREEN_WIDTH // 2, 70)))

        # 3. Depth buttons (in the blue layers)
        for btn in self._grid_btns:
            btn.draw(self.screen, self._font_btn, mouse,
                     selected=(btn.value == self.grid_size))
            # Label below each button
            lbl = self._font_sub.render(btn.label, True, (220, 240, 255))
            lbl_bg = pygame.Surface((lbl.get_width() + 10, lbl.get_height() + 4),
                                    pygame.SRCALPHA)
            lbl_bg.fill((0, 0, 0, 130))
            lbl_rect = lbl.get_rect(center=(btn.rect.centerx,
                                             btn.rect.bottom + 12))
            self.screen.blit(lbl_bg, (lbl_rect.x - 5, lbl_rect.y - 2))
            self.screen.blit(lbl, lbl_rect)

        # 4. PLAY + SHOP
        self._play_btn.draw(self.screen, self._font_btn, mouse)
        self._shop_btn.draw(self.screen, self._font_btn, mouse)

        # 5. Selected depth label
        sel_label = self._font_sub.render(
            f"Selected: {self.depth_label}   "
            f"{self.grid_size[0]}×{self.grid_size[1]} grid",
            True, (180, 230, 200),
        )
        sel_bg = pygame.Surface((sel_label.get_width() + 20, sel_label.get_height() + 8),
                                 pygame.SRCALPHA)
        sel_bg.fill((0, 0, 0, 160))
        sel_x = settings.SCREEN_WIDTH // 2 - sel_label.get_width() // 2
        sel_y = self._play_btn.rect.top - sel_label.get_height() - 14
        self.screen.blit(sel_bg, (sel_x - 10, sel_y - 4))
        self.screen.blit(sel_label, (sel_x, sel_y))


    def _ensure_fonts(self) -> None:
        if self._font_title is None:
            self._font_title = pygame.font.SysFont("monospace", 58, bold=True)
            self._font_btn   = pygame.font.SysFont("monospace", 20, bold=True)
            self._font_sub   = pygame.font.SysFont("monospace", 13, bold=True)
