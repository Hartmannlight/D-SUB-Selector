#!/usr/bin/env python3
"""
Build the static site into dist/ for GitHub Pages.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from generate_svgs import generate_all


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
DIST_DIR = PROJECT_ROOT / "dist"
SVG_OUT_DIR = DIST_DIR / "assets" / "svg"


def main() -> int:
    if not SRC_DIR.exists():
        raise SystemExit(f"Missing src directory: {SRC_DIR}")

    target_dir = DIST_DIR
    if DIST_DIR.exists():
        try:
            shutil.rmtree(DIST_DIR)
        except PermissionError:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_dir = PROJECT_ROOT / f"dist__old_{timestamp}"
            try:
                shutil.move(str(DIST_DIR), str(backup_dir))
            except PermissionError:
                target_dir = PROJECT_ROOT / "dist_build"
                if target_dir.exists():
                    shutil.rmtree(target_dir)

    if target_dir != DIST_DIR:
        print(f"Warning: dist is locked. Building into {target_dir} instead.")

    shutil.copytree(SRC_DIR, target_dir)
    written = generate_all(target_dir / "assets" / "svg", include_caption=True)

    print(f"Built site to {target_dir}")
    print(f"Generated {written} SVGs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
