---
name: experiment-report
description: This skill should be used when a user provides raw full-page screenshots (terminal windows, browser pages, IDE windows, application dialogs) and needs them transformed into neatly arranged figures suitable for an experiment / lab report. Typical triggers include "把这几张截图整理一下", "截图左边距对齐", "终端截图统一排版", "把截图整理进实验报告". Core capability: batch-crop images to consistent margins and align left edges so that vertically-stacked screenshots (especially terminal sequences) form a tidy column with prompts flush on the same x-coordinate.
agent_created: true
---

# Experiment Report — Screenshot Layout

## Overview

Transforms raw full-screen screenshots into report-ready figures: removes browser chrome / taskbar / title bar whitespace, normalizes outer padding, and—critically for terminal sequences—aligns the left text edge so every screenshot's command prompt lands on the same x-coordinate. Produces a directory of cropped PNGs and an HTML preview that shows how the batch will look stacked in the final document.

## When to use

- User drops a folder of full-page screenshots and asks to "整理一下" / "排版一下" / "裁一下" / "留白统一一下".
- User pastes screenshots inline and asks them to be cropped, padded, or arranged.
- Building / editing an experiment / homework / lab report (DOCX, Markdown, PDF) where multiple terminal screenshots appear sequentially and need consistent left alignment.
- User explicitly complains that "终端左边的间距不齐" or "截图宽度不统一".

## Quick start

1. Put all source screenshots into one directory (PNG / JPG / JPEG / BMP / WEBP).
2. Decide the layout mode:
   - `terminal` — left text edges aligned across the batch (default for command-line sequences).
   - `panel` — only normalize outer padding; no left-edge alignment (default for mixed / browser / GUI shots).
3. Run the cropper:
   ```bash
   python <skill-dir>/scripts/crop_screenshots.py \
       --input "<dir with screenshots>" \
       --output "<empty dir for cropped images>" \
       --mode terminal   # or panel
   ```
   (`<skill-dir>` is the directory containing this SKILL.md; runnable examples
   with input/output pairs live in `examples/`.)
4. Open the generated `preview.html` in the output directory to verify alignment and ordering.
5. Rename files into the order you want (the script numbers them `001_xxx.png`, `002_xxx.png` … by source filename sort order; reorder before pasting if needed).
6. Paste into the report. For DOCX, prefer inserting one figure per row with a centered caption.

## Workflow Decision Tree

```
User provides screenshots
  ├─ Single screenshot, "裁一下就行"          → just run --mode panel
  ├─ Multiple screenshots, terminal commands → run --mode terminal (default for terminal flows)
  ├─ Multiple screenshots, browser / GUI     → run --mode panel
  └─ Mixed terminal + browser                → run both passes separately; user pastes them
                                              into different report sections
```

## Cropping Rules

### `terminal` mode (key feature)

Goal: every screenshot's command prompt sits at the same x-coordinate when the images are stacked vertically in the report.

Heuristic the script uses:

1. Auto-trim outer whitespace per image using a non-background-pixel bounding box.
2. Add a uniform outer pad (default 16 px).
3. Find the leftmost text column in the trimmed image by scanning from the left for the first column that contains ≥1 non-background pixel on ≥3 different rows (avoids catching isolated noise / underlines).
4. That x-coordinate becomes the "text origin".
5. After all images in the batch are trimmed, compute the **median** text-origin across the batch (robust to one mis-cropped outlier).
6. Re-pad each cropped image horizontally on the left so its text origin equals the batch median. Add a matching 16 px right pad.
7. Scale all images to the same width (default = max trimmed width in the batch, rounded up to a multiple of 4) by adding transparent padding on the right—not by resizing content—so terminal text stays pixel-sharp.

When this works well:

- All terminal shots were taken in the same shell window size with the same font.
- No huge preceding log lines / banners that would push the text origin much further right than typical prompts.

When to fall back to `panel` mode:

- Screenshots were taken at different zoom levels.
- Some images are real terminal windows; others are screenshots of articles / diagrams.

### `panel` mode

Goal: clean, consistent outer padding; no left-edge alignment.

1. Auto-trim outer whitespace using a non-background-pixel bounding box.
2. Add a uniform outer pad (default 16 px).
3. Cap width at 1200 px (downscale only if larger, preserving aspect ratio).
4. No horizontal alignment pass.

### Background detection

Per row, scan inward from each edge; a column is "background" if all sampled pixels are within ε of the dominant corner color (default ε = 12 / 255). Works for typical white-on-black or black-on-white terminals and for light-mode browser windows. For unusual backgrounds (e.g., dark mode + custom wallpaper), pass `--bg "#1e1e1e"` to set the reference background explicitly.

### Why not just resize to a fixed width?

Resizing blurs / distorts text and breaks monospace alignment. Padding is preferred for terminal content. Resize-thumbnail is allowed in `panel` mode only.

## Bundled Resources

### scripts/

- `crop_screenshots.py` — Pillow-based batch cropper. See CLI usage above.
  Supports: `--input`, `--output`, `--mode {terminal,panel}`, `--pad N`, `--bg "#RRGGBB"`, `--max-width N`, `--threshold N`. Run with `--help` for full list.

### references/

- `crop_rules.md` — deeper rationale, edge cases, when to switch modes.

### assets/

- `example_asset.txt` — sample invocation log and config snippets; not loaded by Claude but kept as a quick reference for the user.

## Output contract

Each invocation writes:

- `<output>/NNN_<original-stem>.png` — one cropped PNG per input, zero-padded number prefix so lexical sort matches visual order.
- `<output>/preview.html` — single-file HTML preview that stacks all cropped PNGs vertically with a thin separator; no external CSS / JS.
- `<output>/crop_log.json` — machine-readable log: per image, original path, crop box, pad, text origin, final size.

Always check `preview.html` before pasting into the report. If alignment looks off, re-run with `--mode panel` (looser rules) or set `--bg` explicitly.

## Gotchas

- Screenshots with semi-transparent taskbars / drop shadows at the bottom can fool the auto-trim; pass a manual `--pad` or trim the source image first.
- If the terminal font changes between shots, even pixel-aligned images will look misaligned vertically — the script can't fix font drift, only x-alignment.
- For very long sessions, the script trims whitespace but does NOT crop to a content "highlight" region. If the user wants only specific commands highlighted, do that in a separate pass (e.g., annotate in Word / draw rectangles) after the alignment pass.