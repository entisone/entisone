#!/usr/bin/env python3
"""Prep a photo for ASCII conversion.

Three steps, in order:
  1. Remove the background with rembg so the subject is isolated.
  2. Boost local contrast with OpenCV CLAHE — this is what gives a flatly-lit
     face real highlights and shadows instead of one dark blob.
  3. Composite onto pure white so the background maps to the blank end of the
     ASCII ramp (white -> spaces).

Run once per photo:  python scripts/prep_photo.py source-photo.jpg
Writes source-prepped.png next to it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "source-prepped.png"

# CLAHE strength. Higher clip = punchier local contrast, but more grain.
CLAHE_CLIP = 2.6
CLAHE_GRID = (8, 8)


def remove_background(img: Image.Image) -> Image.Image:
    """Cut the subject out. Falls back to the original if rembg isn't installed."""
    try:
        from rembg import remove
    except ImportError:
        print(
            "  ! rembg not installed — skipping background removal.\n"
            "    pip install -r scripts/requirements-portrait.txt for the full pipeline.",
            file=sys.stderr,
        )
        return img.convert("RGBA")
    print("  - removing background (rembg)")
    return remove(img).convert("RGBA")


def flatten_onto_white(img: Image.Image) -> Image.Image:
    """Composite RGBA onto pure white, so cut-out areas become the blank glyph."""
    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
    return Image.alpha_composite(white, img).convert("RGB")


def boost_contrast(img: Image.Image) -> Image.Image:
    """CLAHE on the L channel of LAB — local contrast without blowing out color."""
    print("  - boosting local contrast (CLAHE)")
    bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_GRID).apply(l)
    merged = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    return Image.fromarray(cv2.cvtColor(merged, cv2.COLOR_BGR2RGB))


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "source-photo.jpg"
    if not src.exists():
        print(f"error: no such photo: {src}", file=sys.stderr)
        print("usage: python scripts/prep_photo.py <photo.jpg>", file=sys.stderr)
        return 1

    print(f"prep_photo: {src.name}")
    img = Image.open(src)

    cut = remove_background(img)
    flat = flatten_onto_white(cut)
    boosted = boost_contrast(flat)

    # Grayscale is all the ASCII ramp ever looks at.
    boosted.convert("L").save(OUT)
    print(f"  -> {OUT.relative_to(ROOT)}  ({boosted.size[0]}x{boosted.size[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
