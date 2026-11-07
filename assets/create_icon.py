from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

SIZE = 512
im = Image.new("RGBA", (SIZE, SIZE), (8, 9, 15, 255))

# Dark rounded metal badge with a warm orange illuminated rim.
rim = Image.new("RGBA", im.size, (0, 0, 0, 0))
rd = ImageDraw.Draw(rim)
rd.rounded_rectangle((12, 12, 500, 500), radius=104, fill=(8, 10, 16, 255), outline=(255, 112, 18, 255), width=18)
im = Image.alpha_composite(im, rim.filter(ImageFilter.GaussianBlur(13)))
d = ImageDraw.Draw(im)
d.rounded_rectangle((16, 16, 496, 496), radius=100, fill=(10, 12, 18, 255), outline=(255, 143, 34, 255), width=12)

# Subtle circuit traces.
for y in (112, 150, 190, 238, 278):
    d.line((34, y, 104, y, 128, y + 18), fill=(115, 55, 18, 255), width=4)
    d.line((478, y, 408, y, 384, y + 18), fill=(115, 55, 18, 255), width=4)

# Gear ring and teeth.
cx, cy = 256, 174
import math
pts = []
for i in range(64):
    a = -math.pi / 2 + i * 2 * math.pi / 64
    r = 116 if (i // 4) % 2 == 0 else 98
    pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
d.polygon(pts, fill=(172, 177, 185, 255), outline=(255, 171, 75, 255))
d.ellipse((cx-76, cy-76, cx+76, cy+76), fill=(20, 23, 29, 255), outline=(255, 130, 28, 255), width=10)
# Monitor / driver emblem.
d.rounded_rectangle((cx-54, cy-48, cx+54, cy+29), radius=10, fill=(14, 18, 25, 255), outline=(255, 167, 48, 255), width=7)
d.line((cx, cy+30, cx, cy+47), fill=(255, 167, 48, 255), width=8)
d.line((cx-28, cy+49, cx+28, cy+49), fill=(255, 167, 48, 255), width=8)
d.polygon([(cx, cy-34), (cx-21, cy-10), (cx-8, cy-10), (cx-8, cy+12), (cx+8, cy+12), (cx+8, cy-10), (cx+21, cy-10)], fill=(255, 155, 25, 255))

# Brand name, sized to remain legible in Windows icon previews.
font_path = "C:/Windows/Fonts/arialbd.ttf"
try:
    f1 = ImageFont.truetype(font_path, 58)
    f2 = ImageFont.truetype(font_path, 64)
except OSError:
    f1 = ImageFont.load_default()
    f2 = ImageFont.load_default()
d.text((256, 335), "DjShrek", font=f1, anchor="mm", fill=(245, 246, 249, 255), stroke_width=1, stroke_fill=(25, 25, 25, 255))
d.text((256, 405), "Draiver", font=f2, anchor="mm", fill=(255, 143, 28, 255), stroke_width=1, stroke_fill=(60, 26, 4, 255))

Path("assets").mkdir(exist_ok=True)
im.save("assets/DjShrek-Draiver.ico", format="ICO", sizes=[(16,16), (24,24), (32,32), (48,48), (64,64), (128,128), (256,256)])
im.save("assets/DjShrek-Draiver-icon.png")
