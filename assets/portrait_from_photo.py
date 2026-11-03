#!/usr/bin/env python3
"""Turns a photo into the ASCII portrait used by the hero (assets/portrait.txt).

    python3 assets/portrait_from_photo.py photo.jpg > assets/portrait.txt
    python3 assets/generate.py

CROP and SILHOUETTE are hand-tuned for the original 1200x1600 selfie: the crop frames
head and shoulders, and the polygon traces hair, face, beard and shoulders so the wall,
ring light and chair stay out. Re-trace them for a different photo.
"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

COLS = 80                 # characters per row
ASPECT = 0.5              # character width / line height in the hero
GAMMA = 1.15              # >1 keeps skin light so features stand out
FEATURE = 0.6             # weight of local contrast (glasses, eyes, mustache)
RAMP = " .:-=+*#%@"       # light -> dark
CROP = (440, 340, 1000, 1000)
SILHOUETTE = [(250, 28), (335, 38), (420, 88), (472, 170), (472, 262), (436, 330), (428, 420),
              (404, 500), (392, 530), (440, 560), (560, 596), (560, 720), (0, 720), (0, 650),
              (100, 575), (150, 540), (132, 455), (116, 385), (92, 300), (86, 222), (116, 132),
              (178, 62)]
SHIRT_Y = 560             # below this (crop px) the shirt is faded so the face leads


def to_ascii(path):
    im = Image.open(path).convert("RGB").crop(CROP)
    W, H = im.size
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(SILHOUETTE, fill=255)
    m = np.asarray(mask.filter(ImageFilter.GaussianBlur(5)), dtype=float) / 255

    g = np.asarray(ImageOps.grayscale(im).filter(ImageFilter.GaussianBlur(1.0)), dtype=float) / 255
    lo, hi = np.percentile(g[m > .5], 2), np.percentile(g[m > .5], 97)
    tone = np.clip((g - lo) / (hi - lo), 0, 1)              # stretched within the silhouette
    blur = np.asarray(Image.fromarray((tone * 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(14)), dtype=float) / 255
    local = np.clip(blur - tone, 0, 1)                       # darker than its surroundings
    local = np.clip(local / np.percentile(local[m > .5], 99), 0, 1)
    dark = np.clip((1 - tone) * 0.78 + local * FEATURE, 0, 1)

    rows = int(round(COLS * H / W * ASPECT))
    def shrink(a):
        return np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((COLS, rows), Image.BOX),
                          dtype=float) / 255
    D, M = shrink(dark), shrink(m)
    y = np.linspace(0, H, rows)[:, None]
    D = np.where(y > SHIRT_Y, D * 0.62, D)
    D = (np.clip((D - 0.10) / 0.85, 0, 1) ** GAMMA) * M

    lines = []
    for r in range(rows):
        lines.append("".join(
            " " if M[r, c] < .5 or D[r, c] < .05 else RAMP[min(len(RAMP) - 1, 1 + int(D[r, c] * (len(RAMP) - 1)))]
            for c in range(COLS)).rstrip())
    return "\n".join(lines)


if __name__ == "__main__":
    print(to_ascii(sys.argv[1]))
