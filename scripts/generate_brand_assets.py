from pathlib import Path
from PIL import Image
from io import BytesIO
import cairosvg

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)
svg = ASSETS / "DjShrek-Mark.svg"
png = ASSETS / "DjShrek-Mark.png"
icon = Image.open(BytesIO(cairosvg.svg2png(url=str(svg), output_width=512, output_height=512))).convert("RGBA")
icon.save(png)
icon.save(ASSETS / "DjShrek-Draiver.ico", format="ICO", sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
icon.save(ASSETS / "DjShrek-Setup.ico", format="ICO", sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
print("Generated DjShrek application and installer icons.")
