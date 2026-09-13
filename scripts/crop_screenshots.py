# -*- coding: utf-8 -*-
"""
crop_screenshots.py — experiment-report skill

Batch-crop full-page screenshots into report-ready figures.

Modes
-----
- terminal : auto-trim + align left text edge across the batch (for terminal
             sequences where every prompt should sit at the same x).
- panel    : auto-trim + uniform outer pad only (for browser / GUI shots).

Usage
-----
    python crop_screenshots.py --input <dir> --output <dir> --mode terminal
    python crop_screenshots.py --input <dir> --output <dir> --mode panel
    python crop_screenshots.py --help

Outputs (per run)
-----------------
    <output>/001_<stem>.png, 002_<stem>.png, ...
    <output>/preview.html
    <output>/crop_log.json

Dependencies
------------
    Pillow (pip install pillow)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "Pillow is required:  pip install pillow\n"
    )
    raise


SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Batch-crop screenshots into report-ready figures."
    )
    p.add_argument("--input", required=True, help="Directory with source screenshots.")
    p.add_argument("--output", required=True, help="Directory to write cropped PNGs.")
    p.add_argument(
        "--mode",
        choices=("terminal", "panel"),
        default="terminal",
        help="terminal = align left text edge across batch; panel = uniform padding only.",
    )
    p.add_argument("--pad", type=int, default=16, help="Outer padding in pixels (default 16).")
    p.add_argument(
        "--bg",
        default=None,
        help='Reference background colour "#RRGGBB". If omitted, auto-detected from corner pixels.',
    )
    p.add_argument("--max-width", type=int, default=1200, help="Max width in panel mode.")
    p.add_argument(
        "--threshold",
        type=int,
        default=12,
        help="Per-channel colour distance from background considered 'still background' (0-255).",
    )
    return p.parse_args()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def list_images(input_dir: Path) -> List[Path]:
    paths = sorted(
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    )
    if not paths:
        sys.stderr.write(f"No images found in {input_dir}\n")
    return paths


def load_rgb(path: Path) -> Image.Image:
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def detect_bg_color(img: Image.Image, sample: int = 8) -> Tuple[int, int, int]:
    """Average corner pixel colour as background reference."""
    w, h = img.size
    s = max(1, min(sample, w // 4, h // 4))
    pixels = []
    for x0, y0 in ((0, 0), (w - s, 0), (0, h - s), (w - s, h - s)):
        crop = img.crop((x0, y0, x0 + s, y0 + s))
        pixels.extend(list(crop.getdata()))
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    return (r, g, b)


def is_bg(px: Tuple[int, int, int], bg: Tuple[int, int, int], thr: int) -> bool:
    return all(abs(a - b) <= thr for a, b in zip(px, bg))


def trim_bbox(
    img: Image.Image, bg: Tuple[int, int, int], thr: int
) -> Tuple[int, int, int, int] | None:
    """Bounding box (l, t, r, b) of non-background content. None if all bg."""
    w, h = img.size
    px = img.load()

    def col_has_content(x: int) -> bool:
        for y in range(h):
            if not is_bg(px[x, y], bg, thr):
                return True
        return False

    def row_has_content(y: int) -> bool:
        for x in range(w):
            if not is_bg(px[x, y], bg, thr):
                return True
        return False

    # left
    l = 0
    while l < w and not col_has_content(l):
        l += 1
    if l == w:
        return None  # entirely background
    r = w - 1
    while r > l and not col_has_content(r):
        r -= 1
    t = 0
    while t < h and not row_has_content(t):
        t += 1
    b = h - 1
    while b > t and not row_has_content(b):
        b -= 1
    return (l, t, r + 1, b + 1)


def find_left_text_column(
    img: Image.Image, bg: Tuple[int, int, int], thr: int, min_rows: int = 3
) -> int:
    """x-coordinate of the first column that has non-bg pixels on >=min_rows distinct rows."""
    w, h = img.size
    px = img.load()
    for x in range(w):
        rows_hit = 0
        for y in range(h):
            if not is_bg(px[x, y], bg, thr):
                rows_hit += 1
                if rows_hit >= min_rows:
                    return x
        # continue
    return 0


def median(values: Iterable[int]) -> int:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) // 2


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    args = parse_args()
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    if not input_dir.is_dir():
        sys.stderr.write(f"Input directory does not exist: {input_dir}\n")
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = list_images(input_dir)
    if not paths:
        return 1

    # ---- Pass 1: load, detect bg, trim, record text-origin per image ----- #
    records: List[dict] = []
    loaded: List[Tuple[Path, Image.Image, dict]] = []
    for path in paths:
        img = load_rgb(path)
        if args.bg:
            bg = tuple(int(args.bg[i : i + 2], 16) for i in (1, 3, 5))
        else:
            bg = detect_bg_color(img)
        bbox = trim_bbox(img, bg, args.threshold)
        if bbox is None:
            sys.stderr.write(f"Skipping (no content): {path.name}\n")
            continue
        l, t, r, b = bbox
        # add outer pad to bbox
        pad = max(0, args.pad)
        l2 = max(0, l - pad)
        t2 = max(0, t - pad)
        r2 = min(img.size[0], r + pad)
        b2 = min(img.size[1], b + pad)
        cropped = img.crop((l2, t2, r2, b2))
        text_origin = find_left_text_column(cropped, bg, args.threshold)
        rec = {
            "src": str(path),
            "bg": list(bg),
            "bbox_trimmed": [l, t, r, b],
            "bbox_padded": [l2, t2, r2, b2],
            "text_origin": text_origin,
            "cropped_size": list(cropped.size),
        }
        records.append({"src": path.name, **rec})
        loaded.append((path, cropped, rec))

    if not loaded:
        sys.stderr.write("Nothing to write.\n")
        return 1

    # ---- Pass 2: alignment (terminal mode) ------------------------------ #
    if args.mode == "terminal":
        origins = [r["text_origin"] for _, _, r in loaded]
        target_origin = median(origins)
        max_w = max(r["cropped_size"][0] for _, _, r in loaded)
        # round up to multiple of 4 for niceness
        max_w = ((max_w + 3) // 4) * 4
        aligned: List[Tuple[Path, Image.Image, dict]] = []
        for path, cropped, rec in loaded:
            cur_w, cur_h = cropped.size
            new_w = max(cur_w, max_w)
            new_img = Image.new("RGB", (new_w, cur_h), tuple(rec["bg"]))
            # place cropped at x = (target_origin - rec["text_origin"])
            offset_x = target_origin - rec["text_origin"]
            new_img.paste(cropped, (offset_x, 0))
            rec["aligned_offset_x"] = offset_x
            rec["final_size"] = list(new_img.size)
            aligned.append((path, new_img, rec))
        loaded = aligned

    elif args.mode == "panel":
        # optional downscale to max-width
        for path, cropped, rec in loaded:
            w, h = cropped.size
            if w > args.max_width:
                scale = args.max_width / w
                new_size = (args.max_width, max(1, int(h * scale)))
                rec["scaled_from"] = [w, h]
                rec["final_size"] = list(new_size)
                loaded[loaded.index((path, cropped, rec))] = (
                    path,
                    cropped.resize(new_size, Image.LANCZOS),
                    rec,
                )
            else:
                rec["final_size"] = list(cropped.size)

    # ---- Pass 3: write PNGs + preview + log ----------------------------- #
    n = len(loaded)
    pad_w = max(3, len(str(n)))
    log_entries: List[dict] = []
    for idx, (path, out_img, rec) in enumerate(loaded, start=1):
        stem = path.stem
        out_name = f"{str(idx).zfill(pad_w)}_{stem}.png"
        out_path = output_dir / out_name
        out_img.save(out_path, "PNG")
        log_entries.append({
            "index": idx,
            "src": rec["src"],
            "out": str(out_path),
            "bbox_trimmed": rec["bbox_trimmed"],
            "bbox_padded": rec["bbox_padded"],
            "text_origin": rec["text_origin"],
            "final_size": rec["final_size"],
        })
        sys.stdout.write(f"  [{idx:0{pad_w}}/{n}] {path.name} -> {out_name}\n")

    # preview.html
    preview_lines = [
        "<!doctype html>",
        '<meta charset="utf-8">',
        "<title>Screenshot preview</title>",
        "<style>",
        "body{margin:0;background:#f4f4f4;font-family:sans-serif;}",
        ".wrap{max-width:1100px;margin:24px auto;padding:0 16px;}",
        "figure{margin:0 0 18px;background:#fff;padding:12px;border:1px solid #ddd;}",
        "figcaption{font-size:12px;color:#666;margin-bottom:8px;}",
        "img{display:block;max-width:100%;height:auto;}",
        "</style>",
        "<div class=wrap>",
    ]
    for e in log_entries:
        preview_lines.append("<figure>")
        preview_lines.append(
            f"<figcaption>[{e['index']:0{pad_w}}] {Path(e['src']).name} &mdash; "
            f"{e['final_size'][0]}x{e['final_size'][1]}</figcaption>"
        )
        rel = Path(e["out"]).name
        preview_lines.append(f'<img src="{rel}" alt="">')
        preview_lines.append("</figure>")
    preview_lines.append("</div>")
    (output_dir / "preview.html").write_text("\n".join(preview_lines), encoding="utf-8")

    # crop_log.json
    (output_dir / "crop_log.json").write_text(
        json.dumps({"mode": args.mode, "pad": args.pad, "items": log_entries}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    sys.stdout.write(
        f"\nDone. {n} image(s) -> {output_dir}\n"
        f"Open {output_dir / 'preview.html'} to verify alignment.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())