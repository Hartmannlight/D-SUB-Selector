#!/usr/bin/env python3
"""
Build the static site into dist/ for GitHub Pages.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from generate_svgs import generate_all


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
DIST_DIR = PROJECT_ROOT / "dist"
SVG_OUT_DIR = DIST_DIR / "assets" / "svg"


def main() -> int:
    if not SRC_DIR.exists():
        raise SystemExit(f"Missing src directory: {SRC_DIR}")

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    shutil.copytree(SRC_DIR, DIST_DIR)
    written = generate_all(SVG_OUT_DIR, include_caption=True)

    print(f"Built site to {DIST_DIR}")
    print(f"Generated {written} SVGs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
