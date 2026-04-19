# =============================================================
#  shop.py  —  Shop screen
#
#  Two sections:
#    ITEMS    — consumable / limited items (SHOP_ITEMS in settings)
#    UPGRADES — persistent upgrades (SHOP_UPGRADES in settings)
#
#  Drop PNGs into assets/ui/ matching each item/upgrade "asset"
#  key and they load automatically.
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

_UPG_FILL     = (  8,  22,  12)
_UPG_HOVER    = ( 12,  38,  20)
_UPG_BORDER   = (  0, 120,  60)
_UPG_HOV_BDR  = (  0, 210, 100)

_BUY_FILL     = ( 10,  40,  80)
_BUY_HOVER    = ( 20,  70, 120)
_BUY_BORDER   = (  0, 150, 200)
_BUY_TEXT     = (180, 230, 255)
_UPG_BTN_FILL = ( 10,  50,  25)
_UPG_BTN_HOV  = ( 20,  90,  40)
_UPG_BTN_BDR  = (  0, 180,  80)
_UPG_BTN_TEXT = (150, 255, 160)
_DIS_FILL     = ( 25,  25,  35)
_DIS_BORDER   = ( 55,  55,  70)
_DIS_TEXT     = ( 75,  75,  90)

_TITLE_COL    = (255, 215,   0)
_PRICE_COL    = (255, 215,   0)
_STOCK_OK     = ( 80, 210, 110)
_STOCK_FULL   = (210,  70,  70)
_SEC_LABEL    = (100, 170, 130)


class Shop:
    """
    Shop screen.  handle_event() returns "back" when the player
    clicks the back button or presses Escape.
    """

    # Item card geometry (upper section)
    _CARD_W = 220
    _CARD_H = 260

    # Upgrade card geometry (lower section)
    _UPGRADE_W = 300
    _UPGRADE_H = 175

    # Section y-positions
    _ITEM_CARD_Y = 138
    _UPG_CARD_Y  = 448

    def __init__(self, screen: pygame.Surface, hud_image: pygame.Surface):
        self.screen    = screen
        self.hud_image = hud_image
        self._save     = save_manager.load()
        self._fonts: dict = {}

        self._layout_cards()
        self._layout_upgrades()

        # Back button — top left
        self._back_rect = pygame.Rect(20, 15, 120, 38)

    # ----------------------------------------------------------
    #  Layout
    # ----------------------------------------------------------

    def _layout_cards(self) -> None:
        n       = len(settings.SHOP_ITEMS)
        total_w = self._CARD_W * n
        gap     = (settings.SCREEN_WIDTH - total_w) // (n + 1)
        card_y  = self._ITEM_CARD_Y

        self._cards = []
        for i, item in enumerate(settings.SHOP_ITEMS):
            x         = gap + i * (self._CARD_W + gap)
            card_rect = pygame.Rect(x, card_y, self._CARD_W, self._CARD_H)
            buy_rect  = pygame.Rect(
                x + 20,
                card_y + self._CARD_H - 46,
                self._CARD_W - 40, 34,
            )
            self._cards.append({"item": item, "rect": card_rect, "buy_rect": buy_rect})

    def _layout_upgrades(self) -> None:
        n       = len(settings.SHOP_UPGRADES)
        total_w = self._UPGRADE_W * n
        gap     = (settings.SCREEN_WIDTH - total_w) // (n + 1)
        upg_y   = self._UPG_CARD_Y

        self._upgrade_cards = []
        for i, upg in enumerate(settings.SHOP_UPGRADES):
            x        = gap + i * (self._UPGRADE_W + gap)
            rect     = pygame.Rect(x, upg_y, self._UPGRADE_W, self._UPGRADE_H)
            buy_rect = pygame.Rect(
                x + 20,
                upg_y + self._UPGRADE_H - 42,
                self._UPGRADE_W - 40, 32,
            )
            self._upgrade_cards.append({"upg": upg, "rect": rect, "buy_rect": buy_rect})

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
            for uc in self._upgrade_cards:
                if uc["buy_rect"].collidepoint(event.pos):
                    self._try_buy_upgrade(uc["upg"])

        return None

    # ----------------------------------------------------------
    #  Price / count helpers
    # ----------------------------------------------------------

    def _effective_price(self, item: dict) -> int:
        if item.get("dynamic_price"):
            bought = self._save.get("game_battery_bought", 0)
            return item["price"] + settings.BATTERY_PACK_PRICE_INCREMENT * bought
        return item["price"]

    def _effective_current(self, item: dict) -> int:
        if item.get("game_scoped_max"):
            return self._save.get("game_romo_bought", 0)
        if item.get("auto_refill_per_run"):
            return self._save.get("emp_ever_bought", 0)
        return self._save.get(item["id"], 0)

    # ----------------------------------------------------------
    #  Buy logic — items
    # ----------------------------------------------------------

    def _try_buy(self, item: dict) -> None:
        item_id   = item["id"]
        price     = self._effective_price(item)
        max_count = item["max_count"]
        current   = self._effective_current(item)
        shuckles  = self._save.get("shuckles", 0)

        if current >= max_count:
            print(f"[Shop] {item['name']} already at max ({max_count})")
            return
        if shuckles < price:
            print(f"[Shop] Not enough shuckles — need {price}, have {shuckles}")
            return

        self._save[item_id] = self._save.get(item_id, 0) + 1
        self._save["shuckles"] -= price

        if item.get("game_scoped_max"):
            self._save["game_romo_bought"] = 1
        if item.get("dynamic_price"):
            self._save["game_battery_bought"] = self._save.get("game_battery_bought", 0) + 1
        if item.get("auto_refill_per_run"):
            self._save["emp_ever_bought"] = 1

        save_manager.save(self._save)
        print(f"[Shop] Bought {item['name']}!  Shuckles remaining: {self._save['shuckles']}")

    # ----------------------------------------------------------
    #  Buy logic — upgrades
    # ----------------------------------------------------------

    def _try_buy_upgrade(self, upg: dict) -> None:
        shuckles = self._save.get("shuckles", 0)

        if upg["upgrade_type"] == "consumable_uses":
            uses = self._save.get("scanner_upgrade_uses", 0)
            if uses > 0:
                print(f"[Shop] Scanner Upgrade still has {uses} uses remaining.")
                return
            price = upg["price"]
            if shuckles < price:
                print(f"[Shop] Not enough shuckles — need {price}, have {shuckles}")
                return
            self._save["scanner_upgrade_uses"] = settings.SCAN_UPGRADE_USES
            self._save["shuckles"] -= price
            save_manager.save(self._save)
            print(f"[Shop] Scanner Upgrade purchased — "
                  f"{settings.SCAN_UPGRADE_USES} uses granted. "
                  f"Shuckles remaining: {self._save['shuckles']}")

        elif upg["upgrade_type"] == "tiered":
            current_tier = self._save.get("energy_upgrade_tier", 0)
            if current_tier >= len(settings.ENERGY_UPGRADE_TIERS):
                print("[Shop] Energy Upgrade already at max tier.")
                return
            tier_data = settings.ENERGY_UPGRADE_TIERS[current_tier]
            price = tier_data["price"]
            if shuckles < price:
                print(f"[Shop] Not enough shuckles — need {price}, have {shuckles}")
                return
            self._save["energy_upgrade_tier"] = current_tier + 1
            self._save["shuckles"] -= price
            save_manager.save(self._save)
            print(f"[Shop] Energy Upgrade → Tier {current_tier + 1} purchased! "
                  f"({int(tier_data['reduction']*100)}% reduction) "
                  f"Shuckles remaining: {self._save['shuckles']}")

    # ----------------------------------------------------------
    #  Drawing
    # ----------------------------------------------------------

    def draw(self) -> None:
        self._ensure_fonts()
        mouse = pygame.mouse.get_pos()

        # Background
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
        self.screen.blit(title, title.get_rect(center=(cx, 52)))

        # Shuckles balance
        bal = self._fonts["md"].render(
            f"SHUCKLES:  {self._save.get('shuckles', 0)}", True, settings.HUD_GREEN
        )
        self.screen.blit(bal, bal.get_rect(center=(cx, 88)))

        # Back button
        hov_back = self._back_rect.collidepoint(mouse)
        pygame.draw.rect(self.screen,
                         (20, 60, 100) if hov_back else (10, 35, 65),
                         self._back_rect, border_radius=8)
        pygame.draw.rect(self.screen, _BUY_BORDER,
                         self._back_rect, width=1, border_radius=8)
        back_t = self._fonts["sm"].render("← BACK", True, _BUY_TEXT)
        self.screen.blit(back_t, back_t.get_rect(center=self._back_rect.center))

        # ── ITEMS section ──
        sec_items = self._fonts["sm"].render("──  ITEMS  ──", True, _SEC_LABEL)
        self.screen.blit(sec_items, sec_items.get_rect(center=(cx, 118)))

        hovered_desc = None
        for card in self._cards:
            desc = self._draw_card(card, mouse)
            if desc:
                hovered_desc = desc

        # Divider between sections
        div_y = self._ITEM_CARD_Y + self._CARD_H + 14
        pygame.draw.line(self.screen, (0, 80, 50),
                         (40, div_y), (settings.SCREEN_WIDTH - 40, div_y))

        # ── UPGRADES section ──
        sec_upg = self._fonts["sm"].render("──  UPGRADES  ──", True, _SEC_LABEL)
        self.screen.blit(sec_upg, sec_upg.get_rect(center=(cx, div_y + 14)))

        for uc in self._upgrade_cards:
            desc = self._draw_upgrade_card(uc, mouse)
            if desc:
                hovered_desc = desc

        if hovered_desc:
            self._draw_tooltip(hovered_desc)

    # ----------------------------------------------------------
    #  Item card
    # ----------------------------------------------------------

    def _draw_card(self, card: dict, mouse: tuple) -> str | None:
        item     = card["item"]
        rect     = card["rect"]
        buy_rect = card["buy_rect"]
        hovered  = rect.collidepoint(mouse)

        if asset_loader.has_image(settings.SHOP_CARD_ASSET, settings.UI_DIR):
            card_img = asset_loader.load_image(
                settings.SHOP_CARD_ASSET, size=(rect.w, rect.h),
                base_dir=settings.UI_DIR,
            )
            self.screen.blit(card_img, rect.topleft)
            if hovered:
                tint = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                tint.fill((255, 255, 255, 25))
                self.screen.blit(tint, rect.topleft)
            border = _CARD_HOV_BDR if hovered else _CARD_BORDER
            pygame.draw.rect(self.screen, border, rect, width=2, border_radius=12)
        else:
            fill   = _CARD_HOVER  if hovered else _CARD_FILL
            border = _CARD_HOV_BDR if hovered else _CARD_BORDER
            pygame.draw.rect(self.screen, fill,   rect, border_radius=12)
            pygame.draw.rect(self.screen, border, rect, width=2, border_radius=12)

        img_size = 110
        img_surf = asset_loader.load_image_fit(
            item["asset"], img_size, img_size, base_dir=settings.UI_DIR
        )
        self.screen.blit(img_surf, img_surf.get_rect(
            centerx=rect.centerx, top=rect.top + 14
        ))

        # Name
        name_s = self._fonts["md"].render(item["name"], True, (180, 230, 255))
        self.screen.blit(name_s, name_s.get_rect(
            center=(rect.centerx, rect.top + 14 + img_size + 14)
        ))

        # Price
        price   = self._effective_price(item)
        price_s = self._fonts["sm"].render(f"{price} shuckles", True, _PRICE_COL)
        self.screen.blit(price_s, price_s.get_rect(
            center=(rect.centerx, rect.top + 14 + img_size + 32)
        ))

        # Stock / status
        current   = self._effective_current(item)
        max_count = item["max_count"]
        if item.get("resets_per_run"):
            stock_txt = "Resets each run"
            stock_col = (100, 180, 220)
        elif item.get("auto_refill_per_run"):
            if current >= max_count:
                stock_txt = "OWNED  —  refills each run"
                stock_col = _STOCK_FULL
            else:
                stock_txt = "Buy once — refills each run"
                stock_col = _STOCK_OK
        elif item.get("game_scoped_max"):
            stock_txt = f"Owned: {current} / {max_count}  (this game)"
            stock_col = _STOCK_FULL if current >= max_count else _STOCK_OK
        else:
            stock_txt = f"Owned:  {current} / {max_count}"
            stock_col = _STOCK_FULL if current >= max_count else _STOCK_OK
        stock_s = self._fonts["sm"].render(stock_txt, True, stock_col)
        self.screen.blit(stock_s, stock_s.get_rect(
            center=(rect.centerx, rect.top + 14 + img_size + 50)
        ))

        # Buy button
        can_buy = self._save.get("shuckles", 0) >= price and current < max_count
        hov_buy = buy_rect.collidepoint(mouse)
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

    # ----------------------------------------------------------
    #  Upgrade card
    # ----------------------------------------------------------

    def _draw_upgrade_card(self, uc: dict, mouse: tuple) -> str | None:
        upg      = uc["upg"]
        rect     = uc["rect"]
        buy_rect = uc["buy_rect"]
        hovered  = rect.collidepoint(mouse)

        fill   = _UPG_HOVER  if hovered else _UPG_FILL
        border = _UPG_HOV_BDR if hovered else _UPG_BORDER
        pygame.draw.rect(self.screen, fill,   rect, border_radius=12)
        pygame.draw.rect(self.screen, border, rect, width=2, border_radius=12)

        # Icon (left side, 70×70)
        icon_size = 68
        img_surf = asset_loader.load_image_fit(
            upg["asset"], icon_size, icon_size, base_dir=settings.UI_DIR
        )
        icon_rect = img_surf.get_rect(left=rect.left + 12, centery=rect.centery - 12)
        self.screen.blit(img_surf, icon_rect)

        # Text area (right of icon)
        tx = rect.left + icon_size + 24
        ty = rect.top + 14

        # Name
        name_s = self._fonts["md"].render(upg["name"], True, (160, 255, 180))
        self.screen.blit(name_s, (tx, ty))
        ty += 22

        if upg["upgrade_type"] == "consumable_uses":
            uses  = self._save.get("scanner_upgrade_uses", 0)
            price = upg["price"]

            uses_col = _STOCK_OK if uses > 0 else _STOCK_FULL
            uses_s   = self._fonts["sm"].render(
                f"Uses remaining: {uses} / {settings.SCAN_UPGRADE_USES}",
                True, uses_col,
            )
            self.screen.blit(uses_s, (tx, ty)); ty += 18

            detail_s = self._fonts["tip"].render(
                f"{settings.SCAN_UPGRADE_GRID}×{settings.SCAN_UPGRADE_GRID} grid  "
                f"·  {settings.SCAN_UPGRADE_DURATION} moves  "
                f"·  same energy cost",
                True, (120, 180, 140),
            )
            self.screen.blit(detail_s, (tx, ty)); ty += 16

            price_s = self._fonts["sm"].render(f"{price} shuckles", True, _PRICE_COL)
            self.screen.blit(price_s, (tx, ty))

            # Button
            can_buy = self._save.get("shuckles", 0) >= price and uses == 0
            hov_buy = buy_rect.collidepoint(mouse)
            if uses > 0:
                b_fill, b_bdr, b_col = _DIS_FILL, _DIS_BORDER, _DIS_TEXT
                b_lbl = f"{uses} USES LEFT"
            elif not can_buy:
                b_fill, b_bdr, b_col = _DIS_FILL, _DIS_BORDER, _DIS_TEXT
                b_lbl = "NO FUNDS"
            else:
                b_fill = _UPG_BTN_HOV if hov_buy else _UPG_BTN_FILL
                b_bdr, b_col = _UPG_BTN_BDR, _UPG_BTN_TEXT
                b_lbl = "PURCHASE"

        elif upg["upgrade_type"] == "tiered":
            tier   = self._save.get("energy_upgrade_tier", 0)
            tiers  = settings.ENERGY_UPGRADE_TIERS
            maxed  = tier >= len(tiers)

            # Tier dots
            dot_x = tx
            for t in range(len(tiers)):
                col = (0, 210, 100) if t < tier else (50, 60, 55)
                pygame.draw.circle(self.screen, col,
                                   (dot_x + 8, ty + 7), 7)
                dot_x += 20
            ty += 20

            if tier == 0:
                status_txt = "Not Upgraded"
                status_col = (100, 130, 110)
            else:
                pct = int(tiers[tier - 1]["reduction"] * 100)
                status_txt = f"Tier {tier} Active  (−{pct}% energy)"
                status_col = _STOCK_OK
            status_s = self._fonts["sm"].render(status_txt, True, status_col)
            self.screen.blit(status_s, (tx, ty)); ty += 18

            if maxed:
                detail_txt = "Fully upgraded!"
                price      = 0
            else:
                next_t  = tiers[tier]
                pct     = int(next_t["reduction"] * 100)
                price   = next_t["price"]
                detail_txt = f"Next: −{pct}%  ·  {price} shuckles"
            detail_s = self._fonts["sm"].render(detail_txt, True, _PRICE_COL)
            self.screen.blit(detail_s, (tx, ty))

            # Button
            can_buy = not maxed and self._save.get("shuckles", 0) >= price
            hov_buy = buy_rect.collidepoint(mouse)
            if maxed:
                b_fill, b_bdr, b_col, b_lbl = _DIS_FILL, _DIS_BORDER, _DIS_TEXT, "MAXED"
            elif not can_buy:
                b_fill, b_bdr, b_col, b_lbl = _DIS_FILL, _DIS_BORDER, _DIS_TEXT, "NO FUNDS"
            else:
                b_fill = _UPG_BTN_HOV if hov_buy else _UPG_BTN_FILL
                b_bdr, b_col = _UPG_BTN_BDR, _UPG_BTN_TEXT
                b_lbl = "UPGRADE"

        else:
            b_fill, b_bdr, b_col, b_lbl = _DIS_FILL, _DIS_BORDER, _DIS_TEXT, "???"

        pygame.draw.rect(self.screen, b_fill,  buy_rect, border_radius=8)
        pygame.draw.rect(self.screen, b_bdr,   buy_rect, width=1, border_radius=8)
        btn_t = self._fonts["sm"].render(b_lbl, True, b_col)
        self.screen.blit(btn_t, btn_t.get_rect(center=buy_rect.center))

        return upg["description"] if hovered else None

    # ----------------------------------------------------------

    def _draw_tooltip(self, description: str) -> None:
        pad = 14
        tip_rect = pygame.Rect(
            pad,
            settings.SCREEN_HEIGHT - 60,
            settings.SCREEN_WIDTH - pad * 2,
            46,
        )
        pygame.draw.rect(self.screen, (4, 15, 30),  tip_rect, border_radius=8)
        pygame.draw.rect(self.screen, (0, 100, 80), tip_rect, width=1, border_radius=8)
        tip_t = self._fonts["tip"].render(description, True, (150, 220, 180))
        self.screen.blit(tip_t, tip_t.get_rect(
            midleft=(tip_rect.left + 16, tip_rect.centery)
        ))

    def _ensure_fonts(self) -> None:
        if not self._fonts:
            self._fonts = {
                "lg":  pygame.font.SysFont("monospace", 32, bold=True),
                "md":  pygame.font.SysFont("monospace", 17, bold=True),
                "sm":  pygame.font.SysFont("monospace", 13),
                "tip": pygame.font.SysFont("monospace", 12),
            }
