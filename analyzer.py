import numpy as np
from PIL import Image
from config import CrosshairConfig

def rgb_to_hex(r, g, b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}".upper()

def analyze_crosshair_image(image_path: str) -> tuple[CrosshairConfig, dict]:
    """
    Analyzes an uploaded screenshot or cropped crosshair image,
    detects the crosshair features, and returns a CrosshairConfig
    along with detection metrics.
    """
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    # If image is a full screenshot (>300px), crop the central 160x160 region
    cx, cy = w // 2, h // 2
    crop_size = min(160, min(w, h))
    half_crop = crop_size // 2
    
    crop_box = (
        max(0, cx - half_crop),
        max(0, cy - half_crop),
        min(w, cx + half_crop),
        min(h, cy + half_crop)
    )
    cropped = img.crop(crop_box)
    arr = np.array(cropped)  # Shape (H, W, 4)
    H, W, _ = arr.shape
    mid_y, mid_x = H // 2, W // 2

    rgb = arr[:, :, :3].astype(np.float32)

    # Background estimation: samples around the border of the crop
    border_pixels = np.concatenate([
        rgb[0, :, :], rgb[-1, :, :],
        rgb[:, 0, :], rgb[:, -1, :]
    ], axis=0)
    bg_color = np.median(border_pixels, axis=0)

    # Color difference from background
    color_diff = np.linalg.norm(rgb - bg_color, axis=2)
    threshold = max(25.0, np.percentile(color_diff, 80))
    fg_mask = color_diff > threshold

    # If too few or too many foreground pixels, fallback
    total_fg = np.sum(fg_mask)
    if total_fg < 4:
        # Default fallback
        config = CrosshairConfig(style="cross", size=8, thickness=2, gap=4, color="#00FF00")
        return config, {"status": "warning", "message": "Nishon aniqlanmadi, standart nishon tanlandi."}

    # Identify dominant crosshair color (high saturation / bright non-background pixels)
    fg_colors = rgb[fg_mask]
    
    # Exclude near-black/dark pixels if looking for primary crosshair color (to separate outline)
    brightness = np.mean(fg_colors, axis=1)
    bright_fg = fg_colors[brightness > 45]
    if len(bright_fg) > 0:
        dom_color = np.median(bright_fg, axis=0)
    else:
        dom_color = np.median(fg_colors, axis=0)

    hex_color = rgb_to_hex(dom_color[0], dom_color[1], dom_color[2])

    # Check for outline: dark pixels (brightness < 45) right next to bright crosshair pixels
    dark_mask = (brightness <= 45)
    has_outline = np.sum(dark_mask) > (total_fg * 0.15)

    # Check center pixel
    center_roi = fg_mask[mid_y - 2:mid_y + 3, mid_x - 2:mid_x + 3]
    has_center_dot = np.sum(center_roi) >= 3

    # Scan horizontal and vertical axes around center
    h_line = fg_mask[mid_y, :]
    v_line = fg_mask[:, mid_x]

    # Measure horizontal arm distances
    left_side = np.where(h_line[:mid_x])[0]
    right_side = np.where(h_line[mid_x + 1:])[0]
    up_side = np.where(v_line[:mid_y])[0]
    down_side = np.where(v_line[mid_y + 1:])[0]

    gap = 0
    size = 8
    thickness = 2
    style = "cross"

    # Measure gap
    gap_candidates = []
    if len(left_side) > 0:
        gap_candidates.append(mid_x - left_side[-1])
    if len(right_side) > 0:
        gap_candidates.append(right_side[0] + 1)
    if gap_candidates:
        detected_gap = int(np.min(gap_candidates))
        gap = max(0, min(25, detected_gap - (2 if has_center_dot else 0)))

    # Measure arm length
    size_candidates = []
    if len(left_side) > 0:
        size_candidates.append(left_side[-1] - left_side[0] + 1)
    if len(right_side) > 0:
        size_candidates.append(right_side[-1] - right_side[0] + 1)
    if size_candidates:
        size = int(np.clip(np.median(size_candidates), 3, 60))

    # Measure thickness (arm width) along the horizontal axis; only genuinely
    # vertical runs are arm thickness, so outline rows above/below are ignored.
    if len(right_side) > 0:
        sample_x = mid_x + 1 + right_side[len(right_side) // 2]
        col_slice = fg_mask[:, sample_x]
        y_indices = np.where(col_slice)[0]
        if len(y_indices) > 0:
            # longest consecutive run == the arm itself (excludes isolated
            # outline/dot pixels elsewhere in the column)
            runs, cur = [], 1
            for a, b in zip(y_indices, y_indices[1:]):
                if b == a + 1:
                    cur += 1
                else:
                    runs.append(cur)
                    cur = 1
            runs.append(cur)
            thickness = int(np.clip(max(runs), 1, 10))

    # Detect style
    if len(left_side) == 0 and len(right_side) == 0 and len(up_side) == 0 and len(down_side) == 0:
        if has_center_dot:
            style = "dot"
            size = 0
            gap = 0
    elif len(up_side) == 0 and len(down_side) > 0 and len(left_side) > 0 and len(right_side) > 0:
        style = "t_shape"
    elif has_center_dot:
        style = "cross_dot"
    else:
        style = "cross"

    detected_config = CrosshairConfig(
        enabled=True,
        style=style,
        size=size,
        thickness=thickness,
        gap=gap,
        dot_size=max(2, thickness) if has_center_dot else 2,
        color=hex_color,
        opacity=1.0,
        outline=has_outline,
        outline_thickness=1 if has_outline else 0,
        outline_color="#000000"
    )

    metrics = {
        "status": "success",
        "detected_color": hex_color,
        "detected_style": style,
        "detected_size": size,
        "detected_thickness": thickness,
        "detected_gap": gap,
        "has_outline": has_outline,
        "has_dot": has_center_dot,
        "crop_area": f"{crop_size}x{crop_size} px"
    }

    return detected_config, metrics
