"""Render `python demo.py` output to demo.png (+ demo.gif). Needs Pillow (dev only)."""
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
SIZE, PAD, LH = 30, 56, 44
BG, FG = (13, 17, 23), (230, 237, 243)
COLORS = {"31": (255, 107, 107), "32": (87, 227, 137), "33": (250, 204, 21), "34": (121, 192, 255),
          "35": (210, 168, 255), "36": (86, 214, 230), "90": (125, 133, 144)}

regular = ImageFont.truetype(FONT_DIR + "DejaVuSansMono.ttf", SIZE)
bold = ImageFont.truetype(FONT_DIR + "DejaVuSansMono-Bold.ttf", SIZE)
CW = regular.getlength("M")


def parse(line):
    """ANSI line -> [(text, color, bold, dim)]."""
    spans, color, b, d = [], FG, False, False
    for part in re.split(r"(\033\[[\d;]*m)", line):
        m = re.fullmatch(r"\033\[([\d;]*)m", part)
        if not m:
            if part:
                spans.append((part, color, b, d))
            continue
        for code in (m.group(1) or "0").split(";"):
            if code == "0":
                color, b, d = FG, False, False
            elif code == "1":
                b = True
            elif code == "2":
                d = True
            elif code in COLORS:
                color = COLORS[code]
    return spans


def frame(lines, width_cols, total_rows):
    w = int(PAD * 2 + CW * width_cols)
    h = PAD * 2 + 50 + LH * total_rows
    img = Image.new("RGB", (w, h), BG)
    dr = ImageDraw.Draw(img)
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        dr.ellipse((PAD + i * 36, 30, PAD + i * 36 + 20, 50), fill=col)
    y = PAD + 50
    for line in lines:
        x = PAD
        for text, color, b, d in parse(line):
            if d:
                color = tuple(int(v * 0.7 + bg * 0.3) for v, bg in zip(color, BG))
            dr.text((x, y), text, font=bold if b else regular, fill=color)
            x += CW * len(text)
        y += LH
    return img


def main():
    env = {k: v for k, v in os.environ.items() if k != "NO_COLOR"}
    env["FORCE_COLOR"] = "1"
    out = subprocess.run([sys.executable, "demo.py"], cwd=ROOT, env=env, capture_output=True, text=True, check=True).stdout
    lines = ["\033[32m$\033[0m python demo.py"] + out.rstrip("\n").split("\n")
    cols = max(len(re.sub(r"\033\[[\d;]*m", "", ln)) for ln in lines) + 1
    frame(lines, cols, len(lines)).save(ROOT / "demo.png")
    # GIF: reveal line by line, hold on the final frame
    frames = [frame(lines[:k], cols, len(lines)).resize((int(CW * cols + PAD * 2) // 2, (PAD * 2 + 50 + LH * len(lines)) // 2))
              for k in range(1, len(lines) + 1)]
    durations = [90] * (len(frames) - 1) + [4000]
    frames[0].save(ROOT / "demo.gif", save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    print("wrote demo.png and demo.gif")


if __name__ == "__main__":
    main()
