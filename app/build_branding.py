from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import math

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)
S = 512
im = Image.new("RGBA", (S, S), (8, 8, 24, 255))
px = im.load()
for y in range(S):
    for x in range(S):
        dx, dy = x-S/2, y-S/2
        glow = max(0, 1-math.sqrt(dx*dx+dy*dy)/(S*.72))
        px[x,y] = (int(10+20*glow), int(8+8*glow), int(28+48*glow), 255)
d = ImageDraw.Draw(im)
# luminous rounded neon frame
d.rounded_rectangle((18,18,494,494), radius=104, outline=(37,225,255,255), width=12)
d.rounded_rectangle((34,34,478,478), radius=90, outline=(239,48,203,230), width=7)
# equalizer bars
for i,h in enumerate([74,120,165,105,205,145,95]):
    x=92+i*48
    d.rounded_rectangle((x,390-h,x+24,390), radius=10, fill=(38,218,255,235))
# headphone band and earcups
d.arc((105,75,407,385), 190, 350, fill=(45,225,255,255), width=34)
d.rounded_rectangle((92,205,160,345), radius=28, fill=(23,26,67,255), outline=(242,48,204,255), width=10)
d.rounded_rectangle((352,205,420,345), radius=28, fill=(23,26,67,255), outline=(45,225,255,255), width=10)
d.rounded_rectangle((108,220,145,330), radius=18, fill=(65,43,116,255))
d.rounded_rectangle((367,220,404,330), radius=18, fill=(65,43,116,255))
# center DJ badge and waveform
d.ellipse((164,154,348,338), fill=(19,16,47,255), outline=(241,55,203,255), width=9)
d.text((195,183),"DJ", fill=(255,255,255,255), stroke_width=1, stroke_fill=(30,220,255,255))
wave=[]
for i in range(13):
    x=190+i*10
    h=[8,16,26,38,25,15,34,23,40,22,13,25,8][i]
    wave.append((x,266-h))
    wave.append((x,266+h))
d.line(wave, fill=(45,231,255,255), width=5)
# glow pass
glow=im.filter(ImageFilter.GaussianBlur(18))
im=Image.alpha_composite(glow,im)
png=ASSETS/"DjShrek-Draiver.png"
im.save(png)
im.save(ASSETS/"DjShrek-Draiver.ico", format="ICO", sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
im.save(ASSETS/"DjShrek-Setup.ico", format="ICO", sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
print("Generated Cyber Club PNG and multi-resolution ICO assets.")
