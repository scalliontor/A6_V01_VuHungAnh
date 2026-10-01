"""Render the captured real console output as a readable report figure."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
lines = (ROOT / "demo/run.txt").read_text().splitlines()
selected = []
for line in lines:
    if line.startswith(("===", "TEXT:", "VOICE:", "type=", "Retrieval")):
        selected.append(line)
    elif line.strip().startswith(("1.", "2.", "3.")):
        selected.append(line)
    if line.startswith("ORDER:"):
        break

width = 2200
height = 110 + len(selected) * 39
image = Image.new("RGB", (width, height), "#101821")
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((12, 12, width - 12, height - 12), radius=18,
                       fill="#15212d", outline="#35495d", width=3)
draw.rectangle((14, 14, width - 14, 68), fill="#253545")
for i, color in enumerate(("#ed695f", "#f3bf4f", "#61c454")):
    draw.ellipse((35 + i * 28, 33, 48 + i * 28, 46), fill=color)
font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 24)
small = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 20)
draw.text((135, 28), "python main.py — captured output", fill="#dbe9f4", font=small)
for i, line in enumerate(selected):
    color = "#82d6c6" if line.startswith(("TEXT:", "VOICE:", "===")) else "#dfe9f1"
    draw.text((35, 90 + i * 39), line[:146], fill=color, font=font)
image.save(ROOT / "demo/console_capture.png")
