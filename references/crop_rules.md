# Crop Rules — Detailed Reference

This document explains the cropping rules the `experiment-report` skill uses.
Load it into context when the user pushes back on the default behavior or when
input screenshots are unusual.

## Why left-align terminal prompts

When a report contains several terminal screenshots stacked vertically, the
visual cue "the prompt is at the same x" makes the eye scan down a single
vertical rail. If each screenshot starts at a different x, the reader's eye
jumps horizontally on every cut and the sequence becomes harder to follow.

The `terminal` mode of `crop_screenshots.py` finds the leftmost text column in
each trimmed image, computes the **median** of those columns across the batch,
and pads each image horizontally on the left so its text origin matches the
median. Padding on the right brings every image to the same width. Content is
never resized — only padded — so monospace text stays pixel-sharp.

## When median, not mean

A single outlier (a banner image with a far-left logo, or a screenshot that
includes a wide sidebar) would pull the mean text origin off-center. Median is
robust against this. If the batch really is dominated by outliers, switch to
`panel` mode instead.

## Background detection details

`detect_bg_color` samples four corner regions (default 8×8 each) and averages
their RGB values to derive the reference background. This works for:

- White / near-white backgrounds (browser, IDE on light mode).
- Black / near-black backgrounds (terminal on dark mode).
- Single-colour desktop wallpapers where the screenshot covers most of the
  screen.

It fails on:

- Wallpapers with strong gradients (corners are different colours).
- Screenshots taken in windowed mode where the title bar and the body have
  different background colours but both bleed into the corners.

Pass `--bg "#RRGGBB"` to force a reference background when auto-detection
misbehaves.

## Threshold tuning

`--threshold N` is the per-channel distance from the reference background
that's still considered "background". Default 12 works for most terminal
screenshots because anti-aliased text edges land within ~10 channels of the
background. Increase to ~20 if you see thin fringes left in the trimmed image.
Decrease to ~4 if the trim cuts into actual content.

## What the script does NOT do

- No OCR — it does not know what's written in the screenshot.
- No resize of content — only padding. If two images were taken at different
  zoom levels, text size will differ. Align only x, not font size.
- No redaction — privacy info inside the screenshot is left as-is. Run a
  separate redaction step (e.g., blur / box over PII) before or after cropping.
- No content selection — it does not pick "the interesting part" out of a busy
  page. Use the page / section selector before screenshotting, or annotate in
  Word after pasting.

## Decision rules

| Input                                              | Recommended mode |
|----------------------------------------------------|------------------|
| Multiple terminal screenshots, same shell          | terminal         |
| Terminal + occasional `man` / browser shot         | terminal + panel mixed |
| Browser full-page screenshots, several tabs        | panel            |
| IDE / editor with side panel                       | panel            |
| Mixed: some terminal, some browser                 | run twice with different inputs |
| Single screenshot, user says "裁一下就行"           | panel            |

## After the script runs

1. Open `preview.html` in the output directory. The HTML is single-file and
   uses no external assets; double-click it on any machine.
2. Check vertical alignment of left edges. If they look off:
   - the source images were taken at different font sizes / zoom levels (not
     fixable by padding alone), or
   - the background colour differs between shots (re-run with `--bg` set).
3. Reorder files if needed: filenames are `001_…png, 002_…png` so lexical sort
   matches the order they were written. Rename by changing the prefix.
4. Paste into the report. In Word, insert each as "In line with text", set
   width to e.g. 14 cm, center it, and add a caption ("图3-1 ...") below.