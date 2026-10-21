"""Generate a crosshair icon (.ico) for the CrosshairStudio.exe build."""
from PIL import Image, ImageDraw

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
cx = cy = SIZE // 2

# Rounded dark background tile
d.rounded_rectangle([8, 8, SIZE - 8, SIZE - 8], radius=48, fill=(18, 24, 32, 255))
d.rounded_rectangle([8, 8, SIZE - 8, SIZE - 8], radius=48, outline=(34, 200, 120, 255), width=8)

GREEN = (0, 255, 102, 255)
BLACK = (0, 0, 0, 255)
arm, thick, gap = 78, 12, 22

def rect(x1, y1, x2, y2, fill):
    d.rounded_rectangle([x1, y1, x2, y2], radius=3, fill=fill)

# Outline layer
t = 5
rect(cx - gap - arm - t, cy - thick // 2 - t, cx - gap + t, cy + thick // 2 + t, BLACK)
rect(cx + gap - t, cy - thick // 2 - t, cx + gap + arm + t, cy + thick // 2 + t, BLACK)
rect(cx - thick // 2 - t, cy + gap - t, cx + thick // 2 + t, cy + gap + arm + t, BLACK)
rect(cx - thick // 2 - t, cy - gap - arm - t, cx + thick // 2 + t, cy - gap + t, BLACK)

# Main cross arms
rect(cx - gap - arm, cy - thick // 2, cx - gap, cy + thick // 2, GREEN)
rect(cx + gap, cy - thick // 2, cx + gap + arm, cy + thick // 2, GREEN)
rect(cx - thick // 2, cy + gap, cx + thick // 2, cy + gap + arm, GREEN)
rect(cx - thick // 2, cy - gap - arm, cx + thick // 2, cy - gap, GREEN)

# Center dot with outline
d.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], fill=BLACK)
d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=GREEN)

img.save("icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icon.ico saved:", img.size)
