# -*- coding: utf-8 -*-
"""
make_demo_screenshots.py — generate synthetic "messy" raw screenshots
for the examples/ directory of the experiment-report skill.

Creates two batches:
  - terminal: dark terminal windows, command prompts at deliberately
    different x-offsets, uneven outer whitespace (window border noise).
  - panel: light browser-like windows with title bars and ragged margins.

These are the INPUT files for examples/*/; run crop_screenshots.py on them
to reproduce examples/*/output.  Usage:
    python make_demo_screenshots.py --out examples/terminal_demo/input
    python make_demo_screenshots.py --kind panel --out examples/panel_demo/input
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TERMINAL_LINES = [
    ["PS C:\\Users\\demo> ipconfig", "/all", ""],
    ["PS C:\\Users\\demo> ping", "www.example.com", ""],
    ["PS C:\\Users\\demo> tracert", "www.example.com", "1  192.168.1.1  1 ms",
     "2  10.0.0.1     5 ms"],
    ["PS C:\\Users\\demo> nslookup", "www.example.com", ""],
    ["PS C:\\Users\\demo> arp -a", ""],
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("consola.ttf", "Consolas", "lucon.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_terminal(out_dir: Path, seed: int = 7) -> None:
    rng = random.Random(seed)
    font = _font(20)
    bg, fg = (12, 12, 12), (204, 204, 204)
    for i, lines in enumerate(TERMINAL_LINES):
        # ragged outer whitespace: border strip on some edges
        left_noise = rng.choice([0, 0, 18, 40])
        top_noise = rng.choice([0, 10, 26])
        bottom_noise = rng.choice([0, 22])
        pad_l = 12 + rng.randrange(0, 60)   # prompt offset varies per shot
        w = 720 + rng.randrange(0, 80)
        h = top_noise + bottom_noise + 46 * len(lines) + 24
        img = Image.new("RGB", (w, h), bg)
        if left_noise:
            stripe = Image.new("RGB", (left_noise, h), (28, 28, 28))
            img.paste(stripe, (0, 0))
        d = ImageDraw.Draw(img)
        pad_l += left_noise  # prompt always sits right of the border stripe
        y = top_noise + 12
        for line in lines:
            if line:
                d.text((pad_l, y), line, font=font, fill=fg)
            y += 46
        out_dir.mkdir(parents=True, exist_ok=True)
        img.save(out_dir / f"terminal_{i:02d}.png")


PANEL_TITLES = ["Browser - Lab Tutorial", "Network Connections", "Adapter Settings"]


def make_panel(out_dir: Path, seed: int = 11) -> None:
    rng = random.Random(seed)
    font, title_font = _font(18), _font(16)
    chrome, page, text = (222, 225, 230), (250, 250, 250), (40, 40, 40)
    for i, title in enumerate(PANEL_TITLES):
        w = 560 + rng.randrange(0, 200)
        h = 300 + rng.randrange(0, 120)
        # canvas bigger than the window by ragged margins (simulates
        # screenshot tool including desktop background)
        cw, ch = w + rng.randrange(30, 120), h + rng.randrange(20, 90)
        ox, oy = rng.randrange(10, cw - w), rng.randrange(10, ch - h)
        canvas = Image.new("RGB", (cw, ch), (176, 184, 194))
        d = ImageDraw.Draw(canvas)
        d.rectangle([ox, oy, ox + w, oy + h], fill=page, outline=(120, 120, 120))
        d.rectangle([ox, oy, ox + w, oy + 34], fill=chrome)
        d.text((ox + 12, oy + 8), title, font=title_font, fill=text)
        y = oy + 58
        for _ in range((h - 60) // 34):
            line_w = rng.randrange(w // 4, w - 60)
            d.rectangle([ox + 24, y, ox + 24 + line_w, y + 12], fill=(70, 70, 70))
            y += 34
        out_dir.mkdir(parents=True, exist_ok=True)
        canvas.save(out_dir / f"panel_{i:02d}.png")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--kind", choices=("terminal", "panel"), default="terminal")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    out = Path(args.out)
    if args.kind == "terminal":
        make_terminal(out)
    else:
        make_panel(out)
    print(f"wrote demo {args.kind} screenshots -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
