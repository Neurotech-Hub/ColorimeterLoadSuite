#!/usr/bin/env python3
"""Download DSEG7 Classic into the package fonts/ directory (OFL license)."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

DSEG_ZIP_URL = (
    "https://github.com/keshikan/DSEG/releases/download/v0.46/fonts-DSEG_v046.zip"
)

# Paths inside the zip → filenames to keep under fonts/
WANTED = {
    "fonts-DSEG_v046/DSEG7-Classic/DSEG7Classic-Bold.ttf": "DSEG7Classic-Bold.ttf",
    "fonts-DSEG_v046/DSEG7-Classic/DSEG7Classic-Regular.ttf": "DSEG7Classic-Regular.ttf",
    "fonts-DSEG_v046/DSEG-LICENSE.txt": "DSEG-LICENSE.txt",
}


def fonts_dir() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "src" / "colorimeter_gui" / "assets" / "fonts"


def main() -> int:
    dest = fonts_dir()
    dest.mkdir(parents=True, exist_ok=True)

    bold = dest / "DSEG7Classic-Bold.ttf"
    if bold.is_file() and bold.stat().st_size > 0:
        print(f"Already installed: {bold}")
        return 0

    print(f"Downloading DSEG fonts from\n  {DSEG_ZIP_URL}")
    zip_path = dest / "_dseg_download.zip"
    try:
        urlretrieve(DSEG_ZIP_URL, zip_path)
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())
            for src, out_name in WANTED.items():
                if src not in names:
                    print(f"Missing in zip: {src}", file=sys.stderr)
                    return 1
                target = dest / out_name
                target.write_bytes(zf.read(src))
                print(f"Wrote {target}")
    finally:
        if zip_path.exists():
            zip_path.unlink()

    print("Done. Restart the GUI to use DSEG7 Classic.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
