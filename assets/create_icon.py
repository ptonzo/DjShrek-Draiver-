from PIL import Image, ImageDraw, ImageFilter

size = 512
im = Image.new("RGBA", (size, size), (8, 12, 31, 255))
draw = ImageDraw.Draw(im)
draw.rounded_rectangle((12, 12, 500, 500), radius=105, fill=(13, 17, 43, 255), outline=(83, 75, 255, 255), width=14)
glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
g = ImageDraw.Draw(glow)
g.arc((90, 65, 422, 397), 180, 360, fill=(0, 210, 255, 230), width=32)
g.rounded_rectangle((75, 215, 160, 390), radius=38, outline=(0, 220, 255, 255), width=22)
g.rounded_rectangle((352, 215, 437, 390), radius=38, outline=(255, 45, 210, 255), width=22)
im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(15)))
draw = ImageDraw.Draw(im)
draw.arc((90, 65, 422, 397), 180, 360, fill=(0, 225, 255, 255), width=22)
draw.rounded_rectangle((75, 215, 160, 390), radius=38, outline=(0, 225, 255, 255), width=20)
draw.rounded_rectangle((352, 215, 437, 390), radius=38, outline=(235, 75, 255, 255), width=20)
draw.line([(175, 286), (200, 286), (218, 246), (242, 334), (268, 218), (292, 286), (333, 286)], fill=(235, 250, 255, 255), width=15, joint="curve")
for x, h in [(145, 35), (190, 54), (235, 82), (280, 54), (325, 35)]:
    draw.rounded_rectangle((x, 410-h, x+25, 410), radius=6, fill=(0, 210, 255, 255))
draw.polygon([(256, 340), (221, 380), (244, 380), (244, 421), (268, 421), (268, 380), (291, 380)], fill=(0, 220, 255, 255))
im.save("assets/DjShrek-Draiver.ico", format="ICO", sizes=[(16,16), (24,24), (32,32), (48,48), (64,64), (128,128), (256,256)])
