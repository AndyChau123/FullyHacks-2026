# =============================================================
#  asset_loader.py  —  Image loading, scaling, and caching
# =============================================================

import os
import pygame
import settings

# Internal cache so each image is loaded from disk only once
_cache: dict[str, pygame.Surface] = {}


def load_image(
    filename: str,
    size: tuple[int, int] | None = None,
    convert_alpha: bool = True,
    base_dir: str | None = None,
) -> pygame.Surface:
    """
    Load an image by filename, optionally scale it, and cache the result.

    Parameters
    ----------
    filename    : file name (e.g. "hud.png") or a sub-path ("tiles/ocean.png")
    size        : (width, height) to scale to, or None to keep original size
    convert_alpha : True for PNGs with transparency, False for solid images
    base_dir    : folder to search in — defaults to settings.ASSETS_DIR

    Returns
    -------
    pygame.Surface ready to blit
    """
    if base_dir is None:
        base_dir = settings.ASSETS_DIR

    full_path = os.path.join(base_dir, filename)

    # Build a unique cache key that includes the requested size
    cache_key = f"{full_path}@{size}"

    if cache_key in _cache:
        return _cache[cache_key]

    # --- Load -------------------------------------------------
    if not os.path.exists(full_path):
        print(f"[AssetLoader] WARNING: '{full_path}' not found — using placeholder")
        surface = _make_placeholder(size or (256, 256), filename)
        _cache[cache_key] = surface
        return surface

    try:
        surface = pygame.image.load(full_path)
        surface = surface.convert_alpha() if convert_alpha else surface.convert()
    except pygame.error as e:
        print(f"[AssetLoader] ERROR loading '{full_path}': {e}")
        surface = _make_placeholder(size or (256, 256), filename)
        _cache[cache_key] = surface
        return surface

    # --- Scale ------------------------------------------------
    if size is not None:
        surface = pygame.transform.smoothscale(surface, size)

    _cache[cache_key] = surface
    return surface


def load_image_fit(
    filename: str,
    max_w: int,
    max_h: int,
    base_dir: str | None = None,
) -> pygame.Surface:
    """
    Load an image and scale it to fit within (max_w, max_h) while
    preserving its aspect ratio. The result may be smaller than the
    bounding box on one axis — it will never be stretched.
    """
    orig = load_image(filename, size=None, base_dir=base_dir)
    ow, oh = orig.get_size()
    scale  = min(max_w / ow, max_h / oh)
    fit_w  = max(1, int(ow * scale))
    fit_h  = max(1, int(oh * scale))
    return load_image(filename, size=(fit_w, fit_h), base_dir=base_dir)


def load_hud(size: tuple[int, int] | None = None) -> pygame.Surface:
    """Convenience wrapper — loads assets/images/hud.png"""
    return load_image("hud.png", size=size, base_dir=settings.IMAGES_DIR)


def load_tile(tile_name: str) -> pygame.Surface:
    """
    Convenience wrapper — loads a tile background image.

    tile_name : filename inside assets/tiles/, e.g. "ocean.png"
    The image is auto-scaled to fit the tile viewport dimensions.
    """
    size = (settings.TILE_VIEWPORT_WIDTH, settings.TILE_VIEWPORT_HEIGHT)
    return load_image(tile_name, size=size, base_dir=settings.TILES_DIR)


def load_ui(filename: str, size: tuple[int, int] | None = None) -> pygame.Surface:
    """Convenience wrapper — loads assets/ui/<filename>"""
    return load_image(filename, size=size, base_dir=settings.UI_DIR)


def has_image(filename: str, base_dir: str | None = None) -> bool:
    """Return True if the image file exists on disk (no loading)."""
    if base_dir is None:
        base_dir = settings.ASSETS_DIR
    return os.path.exists(os.path.join(base_dir, filename))


def clear_cache() -> None:
    """Free all cached surfaces from memory."""
    _cache.clear()


# ------------------------------------------------------------------
#  Internal helpers
# ------------------------------------------------------------------

def _make_placeholder(size: tuple[int, int], label: str) -> pygame.Surface:
    """
    Returns a coloured checkerboard surface with the filename printed on it.
    Used whenever a real asset is missing so the game still runs.
    """
    w, h = size
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill((20, 20, 60))

    # Checkerboard pattern so it's obviously a placeholder
    tile_sz = 32
    for row in range(h // tile_sz + 1):
        for col in range(w // tile_sz + 1):
            if (row + col) % 2 == 0:
                rect = pygame.Rect(col * tile_sz, row * tile_sz, tile_sz, tile_sz)
                pygame.draw.rect(surf, (30, 30, 80), rect)

    # Label
    font = pygame.font.SysFont("monospace", 14)
    name = os.path.basename(label)
    text_surf = font.render(f"MISSING: {name}", True, (255, 80, 80))
    text_rect = text_surf.get_rect(center=(w // 2, h // 2))
    surf.blit(text_surf, text_rect)

    return surf