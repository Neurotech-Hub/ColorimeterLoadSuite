"""Three-sector annular donut widget mapping load to color."""

from __future__ import annotations

import math
from typing import Tuple

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from colorimeter_gui.serial_worker import LOAD_MAX


# Distinct base hues for S1 / S2 / S3 (clockwise from 12 o'clock).
SECTOR_HUES = (210, 145, 25)  # blue, green, orange


def load_to_color(value: int, hue: int, load_max: int = LOAD_MAX) -> QColor:
    """Map load (grams) to a sequential fill: dark → vivid at full scale."""
    t = max(0.0, min(1.0, value / float(load_max)))
    sat = int(40 + 180 * t)
    val = int(35 + 200 * t)
    return QColor.fromHsv(hue, sat, val)


class DonutWidget(QWidget):
    """Paint three fixed 120° annular sectors (physical map, not a pie chart)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._values: Tuple[int, int, int] = (0, 0, 0)
        self.setMinimumSize(220, 220)

    def set_values(self, d1: int, d2: int, d3: int) -> None:
        self._values = (int(d1), int(d2), int(d3))
        self.update()

    def values(self) -> Tuple[int, int, int]:
        return self._values

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        side = min(self.width(), self.height())
        margin = 8
        outer = QRectF(
            (self.width() - side) / 2 + margin,
            (self.height() - side) / 2 + margin,
            side - 2 * margin,
            side - 2 * margin,
        )
        inner_ratio = 0.42
        inner = QRectF(
            outer.center().x() - outer.width() * inner_ratio / 2,
            outer.center().y() - outer.height() * inner_ratio / 2,
            outer.width() * inner_ratio,
            outer.height() * inner_ratio,
        )

        # Qt: 0° = 3 o'clock, positive = counter-clockwise.
        # Start at 12 o'clock (-90°) and go clockwise → negative span.
        start_angle_deg = -90.0
        span_deg = -120.0

        labels = ("S1", "S2", "S3")
        for i, (val, hue, label) in enumerate(
            zip(self._values, SECTOR_HUES, labels)
        ):
            start = start_angle_deg + i * span_deg

            path = QPainterPath()
            path.moveTo(outer.center())
            path.arcTo(outer, start, span_deg)
            path.closeSubpath()

            hole = QPainterPath()
            hole.addEllipse(inner)
            ring = path.subtracted(hole)

            painter.setPen(QPen(QColor(30, 30, 35), 1.5))
            painter.setBrush(load_to_color(val, hue))
            painter.drawPath(ring)

            mid_deg = start + span_deg / 2
            r = (outer.width() / 2 + inner.width() / 2) / 2
            cx = outer.center().x() + r * math.cos(math.radians(mid_deg))
            cy = outer.center().y() - r * math.sin(math.radians(mid_deg))
            painter.setPen(QColor(240, 240, 245))
            font = QFont(self.font())
            font.setBold(True)
            font.setPointSize(max(10, side // 22))
            painter.setFont(font)
            painter.drawText(
                QRectF(cx - 24, cy - 14, 48, 28),
                Qt.AlignCenter,
                label,
            )

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(28, 28, 32))
        painter.drawEllipse(inner)
