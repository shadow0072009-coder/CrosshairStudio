"""Single source of truth for crosshair drawing.

Both the on-screen overlay and the in-app preview render through this module,
so they can never drift apart. Rendering is done with PIL at 4x resolution and
downscaled (supersampling), which gives smooth anti-aliased edges.
"""
from PIL import Image, ImageDraw

_SUPERSAMPLE = 4


def render_crosshair(cfg, canvas: int = 200, bg=None) -> Image.Image:
    """Render the crosshair centered on a `canvas` x `canvas` RGBA image.

    cfg      -- CrosshairConfig
    canvas   -- output size in px
    bg       -- None for a transparent background (overlay), or an RGBA tuple
                to composite the crosshair over (preview)
    """
    s = _SUPERSAMPLE
    w = canvas * s
    img = Image.new("RGBA", (w, w), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = w / 2.0

    size = max(0, cfg.size) * s
    thick = max(1, cfg.thickness) * s
    gap = max(0, cfg.gap) * s
    dot = max(1, cfg.dot_size) * s
    half = thick / 2.0
    out_t = (max(1, cfg.outline_thickness) * s) if cfg.outline else 0
    color = cfg.color
    out_col = cfg.outline_color

    def rect(x1, y1, x2, y2, fill):
        d.rectangle([x1, y1, x2, y2], fill=fill)

    if cfg.enabled:
        # 1. Cross / T arms
        if cfg.style in ("cross", "cross_dot", "t_shape"):
            arms = [
                (cx - gap - size, cy - half, cx - gap, cy + half),          # left
                (cx + gap, cy - half, cx + gap + size, cy + half),          # right
                (cx - half, cy + gap, cx + half, cy + gap + size),          # bottom
            ]
            if cfg.style != "t_shape":
                arms.append((cx - half, cy - gap - size, cx + half, cy - gap))  # top
            if out_t:
                for x1, y1, x2, y2 in arms:
                    rect(x1 - out_t, y1 - out_t, x2 + out_t, y2 + out_t, out_col)
            for x1, y1, x2, y2 in arms:
                rect(x1, y1, x2, y2, color)

        # 2. Circle
        elif cfg.style == "circle":
            r = size
            if out_t:
                d.ellipse([cx - r - out_t, cy - r - out_t, cx + r + out_t, cy + r + out_t],
                          outline=out_col, width=thick + 2 * out_t)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=thick)

        # 3. Center dot
        if cfg.style in ("dot", "cross_dot") or (cfg.style == "circle" and cfg.dot_size > 0):
            dd = dot / 2.0
            if out_t:
                d.ellipse([cx - dd - out_t, cy - dd - out_t, cx + dd + out_t, cy + dd + out_t],
                          fill=out_col)
            d.ellipse([cx - dd, cy - dd, cx + dd, cy + dd], fill=color)

    # Opacity (per-pixel alpha scaling)
    if cfg.opacity < 0.999:
        alpha = img.getchannel("A").point(lambda v: int(v * cfg.opacity))
        img.putalpha(alpha)

    # Downscale = anti-aliasing
    img = img.resize((canvas, canvas), Image.LANCZOS)

    if bg is not None:
        base = Image.new("RGBA", (canvas, canvas), bg)
        img = Image.alpha_composite(base, img)

    return img
