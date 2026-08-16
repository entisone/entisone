#!/usr/bin/env python3
"""Prep a photo for ASCII conversion.

  1. Isolate the subject — rembg if it's installed, otherwise a chroma key off
     the corner pixels (which is plenty for a flat studio backdrop).
  2. Crop to the framing the character grid can actually resolve. A full-body
     shot at 100x53 gives you a face about four rows tall, so the default
     crops to head-and-shoulders using the detected subject box.
  3. Boost local contrast with CLAHE — this is what gives a flatly-lit face
     real highlights and shadows instead of one dark blob.
  4. Composite onto pure white so the background maps to the blank end of the
     ASCII ramp (white -> spaces).

    python scripts/prep_photo.py source-photo.jpg
    python scripts/prep_photo.py source-photo.jpg --frame full
    python scripts/prep_photo.py source-photo.jpg --frame head

Writes source-prepped.png.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "source-prepped.png"

CLAHE_CLIP = 2.6
CLAHE_GRID = (8, 8)

# The character cell is ~0.6 wide by ~1.06 tall, so a 100x53 grid wants a
# source image very slightly wider than square. Keep this in step with
# make_ascii_svg.py if you change the grid.
TARGET_ASPECT = (100 * 0.6) / (53 * 1.06)

# Crop height as a multiple of the subject's shoulder width. "head" is the
# default because the character grid can only resolve a face that fills a good
# share of the frame — a full-body shot gives you a head about four rows tall.
FRAMES = {"head": 0.80, "bust": 1.15, "full": None}

CHROMA_TOLERANCE = 46.0  # RGB distance from the sampled backdrop color


def isolate_subject(img: Image.Image) -> Image.Image:
    """Return RGBA with the background alpha'd out."""
    try:
        from rembg import remove
    except ImportError:
        print("  - rembg not installed; chroma-keying the backdrop instead")
        return chroma_key(img)
    print("  - removing background (rembg)")
    return remove(img).convert("RGBA")


def chroma_key(img: Image.Image) -> Image.Image:
    """Key out a flat backdrop sampled from the image corners."""
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    h, w = rgb.shape[:2]
    patch = max(8, min(h, w) // 60)
    corners = np.concatenate([
        rgb[:patch, :patch].reshape(-1, 3),
        rgb[:patch, -patch:].reshape(-1, 3),
        rgb[-patch:, :patch].reshape(-1, 3),
        rgb[-patch:, -patch:].reshape(-1, 3),
    ])
    backdrop = np.median(corners, axis=0)

    dist = np.linalg.norm(rgb - backdrop, axis=2)
    # Soft edge so hair doesn't get a hard jagged cut.
    alpha = np.clip((dist - CHROMA_TOLERANCE) / CHROMA_TOLERANCE, 0, 1)

    # Drop specks and fill pinholes inside the subject.
    mask = (alpha > 0.5).astype(np.uint8)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=4)

    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n > 1:  # keep only the largest blob — the person
        biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        mask = (labels == biggest).astype(np.uint8)

    alpha = alpha * mask
    out = np.dstack([np.asarray(img.convert("RGB")),
                     (alpha * 255).astype(np.uint8)])
    return Image.fromarray(out, mode="RGBA")


def subject_box(img: Image.Image) -> tuple[int, int, int, int]:
    alpha = np.asarray(img.split()[-1])
    ys, xs = np.where(alpha > 32)
    if len(xs) == 0:
        return 0, 0, img.width, img.height
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def frame_crop(img: Image.Image, scale: float | None) -> Image.Image:
    """Crop to TARGET_ASPECT around the subject, anchored at the top of the head."""
    x0, y0, x1, y1 = subject_box(img)
    sub_w, sub_h = x1 - x0, y1 - y0
    print(f"  - subject box: {sub_w}x{sub_h} at ({x0},{y0})")

    if scale is None:
        crop_h = sub_h + int(sub_h * 0.04)
        top = y0 - int(sub_h * 0.02)
    else:
        crop_h = int(sub_w * scale)
        top = y0 - int(crop_h * 0.06)  # a little headroom above the hair

    crop_w = int(crop_h * TARGET_ASPECT)
    cx = (x0 + x1) // 2
    left = cx - crop_w // 2

    # Clamp inside the image without changing the crop size.
    left = max(0, min(left, img.width - crop_w)) if crop_w <= img.width else 0
    top = max(0, min(top, img.height - crop_h)) if crop_h <= img.height else 0
    box = (left, top, min(left + crop_w, img.width), min(top + crop_h, img.height))
    print(f"  - cropping to {box[2] - box[0]}x{box[3] - box[1]}")
    return img.crop(box)


def flatten_onto_white(img: Image.Image) -> Image.Image:
    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
    return Image.alpha_composite(white, img).convert("RGB")


def boost_contrast(img: Image.Image) -> Image.Image:
    """CLAHE on the L channel of LAB — local contrast without wrecking color."""
    print("  - boosting local contrast (CLAHE)")
    bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_GRID).apply(l)
    merged = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    return Image.fromarray(cv2.cvtColor(merged, cv2.COLOR_BGR2RGB))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("photo", nargs="?", default=str(ROOT / "source-photo.jpg"))
    ap.add_argument("--frame", choices=list(FRAMES), default="head",
                    help="how tight to crop (default: head)")
    args = ap.parse_args()

    src = Path(args.photo)
    if not src.exists():
        ap.error(f"no such photo: {src}")

    print(f"prep_photo: {src.name} (frame={args.frame})")
    cut = isolate_subject(Image.open(src))
    framed = frame_crop(cut, FRAMES[args.frame])
    prepped = boost_contrast(flatten_onto_white(framed))

    prepped.convert("L").save(OUT)
    print(f"  -> {OUT.relative_to(ROOT)}  ({prepped.size[0]}x{prepped.size[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
