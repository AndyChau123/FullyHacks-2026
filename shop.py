# =============================================================
#  shop.py  —  Shop screen
#
#  Item cards are drawn programmatically; drop a PNG into
#  assets/ui/ matching the item's "asset" key in settings.SHOP_ITEMS
#  and it will load automatically.
# =============================================================

import pygame
import settings
import asset_loader
import save_manager

# ----- Colour palette ----------------------------------------
_CARD_FILL    = (  5,  18,  36)
_CARD_HOVER   = (  8,  30,  55)
_CARD_BORDER  = (  0, 100, 150)
_CARD_HOV_BDR = (  0, 180, 220)

_BUY_FILL     = ( 10,  40,  80)
_BUY_HOVER    = ( 20,  70, 120)
_BUY_BORDER   = (  0, 150, 200)
_BUY_TEXT     = (180, 230, 255)
_DIS_FILL     = ( 25,  25,  35)
_DIS_BORDER   = ( 55,  55,  70)
_DIS_TEXT     = ( 75,  75,  90)

_TITLE_COL    = (255, 215,   0)
_PRICE_COL    = (255, 215,   0)
_STOCK_OK     = ( 80, 210, 110)
_STOCK_FULL   = (210,  70,  70)


class Shop:
    """
    Shop screen.  handle_event() returns "back" when the player
    clicks the back button or presses Escape.
    """

    # Card geometry
    _CARD_W = 220
    _CARD_H = 350

    def __init__(self, screen: pygame.Surface, hud_image: pygame.Surface):
        self.screen    = screen
        self.hud_image = hud_image
        self._save     = save_manager.load()
        self._fonts: dict = {}

        self._layout_cards()

        # Back button — top left
        self._back_rect = pygame.Rect(20, 15, 120, 38)

    # ----------------------------------------------------------
    #  Layout
    # ----------------------------------------------------------

    def _layout_cards(self) -> None:
        """Evenly space item cards horizontally across the screen."""
        n       = len(settings.SHOP_ITEMS)
        total_w = self._CARD_W * n
        gap     = (settings.SCREEN_WIDTH - total_w) // (n + 1)
        card_y  = (settings.SCREEN_HEIGHT - self._CARD_H) // 2

        self._cards = []
        for i, item in enumerate(settings.SHOP_ITEMS):
            x = gap + i * (self._CARD_W + gap)
            card_rect = pygame.Rect(x, card_y, self._CARD_W, self._CARD_H)
            buy_rect  = pygame.Rect(
                x + 20,
                card_y + self._CARD_H - 58,
                self._CARD_W - 40, 40,
            )
            self._cards.append({
                "item":     item,
                "rect":     card_rect,
                "buy_rect": buy_rect,
            })

    # ----------------------------------------------------------
    #  Public API
    # ----------------------------------------------------------

    def reload_save(self) -> None:
        self._save = save_manager.load()

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "back"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._back_rect.collidepoint(event.pos):
                return "back"
            for card in self._cards:
                if card["buy_rect"].collidepoint(event.pos):
                    self._try_buy(card["item"])

        return None

    # ----------------------------------------------------------
    #  Buy logic
    # ----------------------------------------------------------

    def _try_buy(self, item: dict) -> None:
        item_id   = item["id"]
        price     = item["price"]
        max_count = item["max_count"]
        current   = self._save.get(item_id, 0)
        shuckles  = self._save.get("shuckles", 0)

        if current >= max_count:
            print(f"[Shop] {item['name']} already at max ({max_count})")
            return
        if shuckles < price:
            print(f"[Shop] Not enough shuckles — need {price}, have {shuckles}")
            return

        self._save[item_id]   = current + 1
        self._save["shuckles"] -= price
        save_manager.save(self._save)
        print(f"[Shop] Bought {item['name']}!  "
              f"{self._save[item_id]}/{max_count} owned.  "
              f"Shuckles remaining: {self._save['shuckles']}")

    # ----------------------------------------------------------
    #  Drawing
    # ----------------------------------------------------------

    def draw(self) -> None:
        self._ensure_fonts()
        mouse = pygame.mouse.get_pos()

        # Background: HUD + overlay (image if available, else dark fill)
        self.screen.blit(self.hud_image, (0, 0))
        if asset_loader.has_image(settings.SHOP_BG_ASSET, settings.UI_DIR):
            bg = asset_loader.load_image(
                settings.SHOP_BG_ASSET,
                size=(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT),
                base_dir=settings.UI_DIR,
            )
            self.screen.blit(bg, (0, 0))
        else:
            overlay = pygame.Surface(
                (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA
            )
            overlay.fill((0, 0, 20, 192))
            self.screen.blit(overlay, (0, 0))

        cx = settings.SCREEN_WIDTH // 2

        # Title
        title = self._fonts["lg"].render("THE DEEP SHOP", True, _TITLE_COL)
        self.screen.blit(title, title.get_rect(center=(cx, 70)))

        # Shuckles balance
        bal = self._fonts["md"].render(
            f"SHUCKLES:  {self._save.get('shuckles', 0)}",
            True, settings.HUD_GREEN,
        )
        self.screen.blit(bal, bal.get_rect(center=(cx, 112)))

        # Back button
        hov_back = self._back_rect.collidepoint(mouse)
        pygame.draw.rect(self.screen,
                         (20, 60, 100) if hov_back else (10, 35, 65),
                         self._back_rect, border_radius=8)
        pygame.draw.rect(self.screen, _BUY_BORDER,
                         self._back_rect, width=1, border_radius=8)
        back_t = self._fonts["sm"].render("← BACK", True, _BUY_TEXT)
        self.screen.blit(back_t, back_t.get_rect(center=self._back_rect.center))

        # Item cards + tooltip
        hovered_desc = None
        for card in self._cards:
            desc = self._draw_card(card, mouse)
            if desc:
                hovered_desc = desc

        if hovered_desc:
            self._draw_tooltip(hovered_desc)

    def _draw_card(self, card: dict, mouse: tuple) -> str | None:
        item      = card["item"]
        rect      = card["rect"]
        buy_rect  = card["buy_rect"]
        hovered   = rect.collidepoint(mouse)

        if asset_loader.has_image(settings.SHOP_CARD_ASSET, settings.UI_DIR):
            card_img = asset_loader.load_image(
                settings.SHOP_CARD_ASSET,
                size=(rect.w, rect.h),
                base_dir=settings.UI_DIR,
            )
            self.screen.blit(card_img, rect.topleft)
            # Tint for hover state
            if hovered:
                tint = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                tint.fill((255, 255, 255, 25))
                self.screen.blit(tint, rect.topleft)
            # Border always drawn on top
            border = _CARD_HOV_BDR if hovered else _CARD_BORDER
            pygame.draw.rect(self.screen, border, rect, width=2, border_radius=12)
        else:
            fill   = _CARD_HOVER  if hovered else _CARD_FILL
            border = _CARD_HOV_BDR if hovered else _CARD_BORDER
            pygame.draw.rect(self.screen, fill,   rect, border_radius=12)
            pygame.draw.rect(self.screen, border, rect, width=2, border_radius=12)

        # Item image (placeholder until PNG is placed in assets/ui/)
        img_size = 150
        img_rect = pygame.Rect(
            rect.centerx - img_size // 2,
            rect.top + 18,
            img_size, img_size,
        )
        img_surf = asset_loader.load_image_fit(
            item["asset"], img_size, img_size, base_dir=settings.UI_DIR
        )
        self.screen.blit(img_surf, img_rect.topleft)

        # Item name
        name_s = self._fonts["md"].render(item["name"], True, (180, 230, 255))
        self.screen.blit(name_s, name_s.get_rect(
            center=(rect.centerx, rect.top + 18 + img_size + 18)
        ))

        # Price
        price_s = self._fonts["sm"].render(
            f"{item['price']} shuckles", True, _PRICE_COL
        )
        self.screen.blit(price_s, price_s.get_rect(
            center=(rect.centerx, rect.top + 18 + img_size + 42)
        ))

        # Stock
        current   = self._save.get(item["id"], 0)
        max_count = item["max_count"]
        stock_col = _STOCK_FULL if current >= max_count else _STOCK_OK
        stock_s   = self._fonts["sm"].render(
            f"Owned:  {current} / {max_count}", True, stock_col
        )
        self.screen.blit(stock_s, stock_s.get_rect(
            center=(rect.centerx, rect.top + 18 + img_size + 64)
        ))

        # Buy button
        can_buy  = (self._save.get("shuckles", 0) >= item["price"]
                    and current < max_count)
        hov_buy  = buy_rect.collidepoint(mouse)

        if current >= max_count:
            b_fill, b_bdr, b_col, b_lbl = _DIS_FILL, _DIS_BORDER, _DIS_TEXT, "MAX"
        elif not can_buy:
            b_fill, b_bdr, b_col, b_lbl = _DIS_FILL, _DIS_BORDER, _DIS_TEXT, "NO FUNDS"
        else:
            b_fill = _BUY_HOVER if hov_buy else _BUY_FILL
            b_bdr, b_col, b_lbl = _BUY_BORDER, _BUY_TEXT, "BUY"

        pygame.draw.rect(self.screen, b_fill,  buy_rect, border_radius=8)
        pygame.draw.rect(self.screen, b_bdr,   buy_rect, width=1, border_radius=8)
        btn_t = self._fonts["sm"].render(b_lbl, True, b_col)
        self.screen.blit(btn_t, btn_t.get_rect(center=buy_rect.center))

        return item["description"] if hovered else None

    def _draw_tooltip(self, description: str) -> None:
        pad = 14
        tip_rect = pygame.Rect(
            pad,
            settings.SCREEN_HEIGHT - 68,
            settings.SCREEN_WIDTH - pad * 2,
            52,
        )
        pygame.draw.rect(self.screen, (4, 15, 30),   tip_rect, border_radius=8)
        pygame.draw.rect(self.screen, (0, 100, 80),  tip_rect, width=1, border_radius=8)
        tip_t = self._fonts["tip"].render(description, True, (150, 220, 180))
        self.screen.blit(tip_t, tip_t.get_rect(
            midleft=(tip_rect.left + 16, tip_rect.centery)
        ))

    # ----------------------------------------------------------

    def _ensure_fonts(self) -> None:
        if not self._fonts:
            self._fonts = {
                "lg":  pygame.font.SysFont("monospace", 34, bold=True),
                "md":  pygame.font.SysFont("monospace", 18, bold=True),
                "sm":  pygame.font.SysFont("monospace", 14),
                "tip": pygame.font.SysFont("monospace", 13),
            }
