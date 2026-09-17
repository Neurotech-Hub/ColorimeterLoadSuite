"""Load bundled DSEG digital fonts for the force readout."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtGui import QFont, QFontDatabase

_FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
_BUNDLED_FILES = (
    "DSEG7Classic-Bold.ttf",
    "DSEG7Classic-Regular.ttf",
)

_registered_family: Optional[str] = None
_did_register = False


def register_bundled_fonts() -> Optional[str]:
    """Register package TTF files with Qt. Returns family name if loaded."""
    global _registered_family, _did_register
    if _did_register:
        return _registered_family
    _did_register = True

    family: Optional[str] = None
    for name in _BUNDLED_FILES:
        path = _FONT_DIR / name
        if not path.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families and family is None:
            family = families[0]
    _registered_family = family
    return family


def digital_font(point_size: int, bold: bool = True) -> QFont:
    """7-segment face from bundled DSEG, else system digital / monospace."""
    family = register_bundled_fonts()
    if family:
        font = QFont(family, point_size)
        font.setBold(bold)
        return font

    for name in (
        "DSEG7 Classic",
        "Digital-7",
        "DS-Digital",
    ):
        if name in QFontDatabase.families():
            font = QFont(name, point_size)
            font.setBold(bold)
            return font

    font = QFont("Menlo", point_size)
    if not font.exactMatch():
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(point_size)
    font.setBold(bold)
    font.setStyleHint(QFont.Monospace)
    font.setFixedPitch(True)
    return font
