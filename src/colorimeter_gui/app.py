"""Main window: serial toolbar, donut, force readout, time-series plot."""

from __future__ import annotations

import sys
import time
from collections import deque
from pathlib import Path
from typing import Deque, Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from colorimeter_gui.donut_widget import DonutWidget, SECTOR_HUES
from colorimeter_gui.fonts import digital_font
from colorimeter_gui.serial_worker import Sample, SerialWorker, list_serial_ports
from colorimeter_gui.session import SessionRecorder


WINDOW_SEC = 20.0
PLOT_Y_MAX = 6000.0
PLOT_COLORS = (
    QColor.fromHsv(SECTOR_HUES[0], 200, 230),
    QColor.fromHsv(SECTOR_HUES[1], 200, 230),
    QColor.fromHsv(SECTOR_HUES[2], 200, 230),
    QColor(220, 220, 230),  # total force
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Load Cell Control Panel")
        self.resize(960, 720)

        self._worker: Optional[SerialWorker] = None
        self._t0_millis: Optional[int] = None
        self._last_hz_time = time.monotonic()
        self._hz_count = 0
        self._rate_hz = 0.0
        self._session = SessionRecorder()

        self._t: Deque[float] = deque()
        self._d1: Deque[float] = deque()
        self._d2: Deque[float] = deque()
        self._d3: Deque[float] = deque()
        self._force: Deque[float] = deque()

        self._build_ui()
        self._scan_ports()

    def _default_session_dir(self) -> Path:
        return Path.home() / "Documents" / "ColorimeterGUI"

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(280)
        self.port_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bar.addWidget(self.port_combo, stretch=1)

        self.scan_btn = QPushButton("Scan")
        self.scan_btn.clicked.connect(self._scan_ports)
        bar.addWidget(self.scan_btn)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._toggle_connect)
        bar.addWidget(self.connect_btn)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #666; font-size: 16px;")
        bar.addWidget(self.status_dot)

        self.status_label = QLabel("Disconnected")
        bar.addWidget(self.status_label)
        layout.addLayout(bar)

        mid = QHBoxLayout()
        mid.setSpacing(16)

        self.donut = DonutWidget()
        self.donut.setMinimumSize(280, 280)
        mid.addWidget(self.donut, stretch=1)

        readout = QVBoxLayout()
        readout.setAlignment(Qt.AlignCenter)

        title = QLabel("TOTAL FORCE")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #aaa; letter-spacing: 2px;")
        readout.addWidget(title)

        self.force_label = QLabel("—")
        self.force_label.setAlignment(Qt.AlignCenter)
        self.force_label.setFont(digital_font(56))
        self.force_label.setStyleSheet("color: #ffffff;")
        readout.addWidget(self.force_label)

        unit = QLabel("grams")
        unit.setAlignment(Qt.AlignCenter)
        unit.setStyleSheet("color: #888; letter-spacing: 1px;")
        readout.addWidget(unit)

        sectors = QHBoxLayout()
        sectors.setSpacing(24)
        self.sector_labels = []
        for i, name in enumerate(("S1", "S2", "S3")):
            col = QVBoxLayout()
            name_lbl = QLabel(name)
            name_lbl.setAlignment(Qt.AlignCenter)
            c = QColor.fromHsv(SECTOR_HUES[i], 180, 220)
            name_lbl.setStyleSheet(f"color: {c.name()}; font-weight: bold;")
            val_lbl = QLabel("—")
            val_lbl.setAlignment(Qt.AlignCenter)
            val_lbl.setFont(digital_font(22))
            val_lbl.setStyleSheet(f"color: {c.name()};")
            col.addWidget(name_lbl)
            col.addWidget(val_lbl)
            sectors.addLayout(col)
            self.sector_labels.append(val_lbl)
        readout.addSpacing(16)
        readout.addLayout(sectors)
        readout.addStretch()

        mid.addLayout(readout, stretch=1)
        layout.addLayout(mid, stretch=2)

        pg.setConfigOptions(antialias=True, foreground="d", background="#1c1c20")
        self.plot = pg.PlotWidget()
        self.plot.setLabel("left", "Load", units="g")
        self.plot.setLabel("bottom", "Time", units="s")
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.addLegend(offset=(10, 10))
        self.plot.setYRange(0, PLOT_Y_MAX, padding=0)
        self.plot.enableAutoRange(axis="y", enable=False)
        self.plot.setXRange(0, WINDOW_SEC)

        self.curve_d1 = self.plot.plot(pen=pg.mkPen(PLOT_COLORS[0], width=2), name="S1")
        self.curve_d2 = self.plot.plot(pen=pg.mkPen(PLOT_COLORS[1], width=2), name="S2")
        self.curve_d3 = self.plot.plot(pen=pg.mkPen(PLOT_COLORS[2], width=2), name="S3")
        self.curve_force = self.plot.plot(
            pen=pg.mkPen(PLOT_COLORS[3], width=3.5), name="Force"
        )
        self.curve_d1.setZValue(1)
        self.curve_d2.setZValue(1)
        self.curve_d3.setZValue(1)
        self.curve_force.setZValue(10)
        layout.addWidget(self.plot, stretch=3)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        footer.addWidget(QLabel("Save to:"))
        self.session_dir_edit = QLineEdit(str(self._default_session_dir()))
        self.session_dir_edit.setPlaceholderText("Session folder…")
        footer.addWidget(self.session_dir_edit, stretch=1)

        self.browse_btn = QPushButton("Browse…")
        self.browse_btn.clicked.connect(self._browse_session_dir)
        footer.addWidget(self.browse_btn)

        self.start_session_btn = QPushButton("Start Session")
        self.start_session_btn.clicked.connect(self._start_session)
        footer.addWidget(self.start_session_btn)

        self.stop_session_btn = QPushButton("Stop Session")
        self.stop_session_btn.setEnabled(False)
        self.stop_session_btn.clicked.connect(self._stop_session)
        footer.addWidget(self.stop_session_btn)

        self.session_status = QLabel("Idle")
        self.session_status.setStyleSheet("color: #888;")
        footer.addWidget(self.session_status)
        layout.addLayout(footer)

        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #1c1c20;
                color: #e8e8ec;
            }
            QComboBox, QPushButton, QLineEdit {
                background-color: #2a2a30;
                border: 1px solid #444;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #35353c; }
            QPushButton:disabled { color: #666; }
            QComboBox::drop-down { border: none; }
            """
        )

    def _browse_session_dir(self) -> None:
        start = self.session_dir_edit.text().strip() or str(self._default_session_dir())
        chosen = QFileDialog.getExistingDirectory(self, "Session save folder", start)
        if chosen:
            self.session_dir_edit.setText(chosen)

    def _start_session(self) -> None:
        if self._session.active:
            return
        directory = Path(
            self.session_dir_edit.text().strip() or self._default_session_dir()
        )
        try:
            path = self._session.start(directory)
        except OSError as exc:
            self.session_status.setText(f"Error: {exc}")
            self.session_status.setStyleSheet("color: #c44;")
            return
        self.start_session_btn.setEnabled(False)
        self.stop_session_btn.setEnabled(True)
        self.browse_btn.setEnabled(False)
        self.session_dir_edit.setEnabled(False)
        self.session_status.setText(f"Recording · {path.name}")
        self.session_status.setStyleSheet("color: #3c9;")

    def _stop_session(self) -> None:
        path = self._session.stop()
        self.start_session_btn.setEnabled(True)
        self.stop_session_btn.setEnabled(False)
        self.browse_btn.setEnabled(True)
        self.session_dir_edit.setEnabled(True)
        if path is not None:
            self.session_status.setText(f"Saved · {path.name}")
        else:
            self.session_status.setText("Idle")
        self.session_status.setStyleSheet("color: #888;")

    def _scan_ports(self) -> None:
        current = self.port_combo.currentData()
        self.port_combo.clear()
        ports = list_serial_ports()
        if not ports:
            self.port_combo.addItem("(no ports found)", None)
            self.connect_btn.setEnabled(False)
            return
        for device, label in ports:
            self.port_combo.addItem(label, device)
        if current:
            idx = self.port_combo.findData(current)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)
        self.connect_btn.setEnabled(self._worker is None)

    def _toggle_connect(self) -> None:
        if self._worker is not None:
            self._disconnect()
        else:
            self._connect()

    def _connect(self) -> None:
        device = self.port_combo.currentData()
        if not device:
            self.status_label.setText("No port selected")
            return

        self._clear_buffers()
        self._worker = SerialWorker(device)
        self._worker.sample.connect(self._on_sample)
        self._worker.status.connect(self._on_status)
        self._worker.error.connect(self._on_error)
        self._worker.finished_clean.connect(self._on_worker_finished)
        self._worker.start()

        self.connect_btn.setText("Disconnect")
        self.scan_btn.setEnabled(False)
        self.port_combo.setEnabled(False)
        self._set_dot("#3c9")

    def _disconnect(self) -> None:
        if self._worker is None:
            return
        if self._session.active:
            self._stop_session()
        self._worker.stop()
        self.connect_btn.setEnabled(False)
        self.status_label.setText("Disconnecting…")

    def _on_worker_finished(self) -> None:
        self._worker = None
        self.connect_btn.setText("Connect")
        self.connect_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.port_combo.setEnabled(True)
        self._set_dot("#666")
        text = self.status_label.text()
        if text.startswith("Disconnecting") or text.startswith("Connected"):
            self.status_label.setText("Disconnected")

    def _on_status(self, msg: str) -> None:
        rate = f"  ·  {self._rate_hz:.0f} Hz" if self._rate_hz > 0 else ""
        if msg == "Streaming":
            self.status_label.setText(f"Connected{rate}")
        else:
            self.status_label.setText(msg)

    def _on_error(self, msg: str) -> None:
        self.status_label.setText(msg)
        self._set_dot("#c44")

    def _set_dot(self, color: str) -> None:
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 16px;")

    def _clear_buffers(self) -> None:
        self._t0_millis = None
        self._t.clear()
        self._d1.clear()
        self._d2.clear()
        self._d3.clear()
        self._force.clear()
        self._hz_count = 0
        self._rate_hz = 0.0
        self._last_hz_time = time.monotonic()
        self.curve_d1.setData([], [])
        self.curve_d2.setData([], [])
        self.curve_d3.setData([], [])
        self.curve_force.setData([], [])
        self.force_label.setText("—")
        for lbl in self.sector_labels:
            lbl.setText("—")
        self.donut.set_values(0, 0, 0)

    def _on_sample(self, sample: Sample) -> None:
        if self._t0_millis is None:
            self._t0_millis = sample.millis
        t_rel = (sample.millis - self._t0_millis) / 1000.0

        d1 = float(sample.d1)
        d2 = float(sample.d2)
        d3 = float(sample.d3)
        force = float(sample.force)

        if self._session.active:
            self._session.write_force(force)

        self._t.append(t_rel)
        self._d1.append(d1)
        self._d2.append(d2)
        self._d3.append(d3)
        self._force.append(force)

        while self._t and (t_rel - self._t[0]) > WINDOW_SEC:
            self._t.popleft()
            self._d1.popleft()
            self._d2.popleft()
            self._d3.popleft()
            self._force.popleft()

        self.force_label.setText(str(int(round(force))))
        self.sector_labels[0].setText(str(int(round(d1))))
        self.sector_labels[1].setText(str(int(round(d2))))
        self.sector_labels[2].setText(str(int(round(d3))))
        self.donut.set_values(int(round(d1)), int(round(d2)), int(round(d3)))

        t = np.fromiter(self._t, dtype=np.float64)
        self.curve_d1.setData(t, np.fromiter(self._d1, dtype=np.float64))
        self.curve_d2.setData(t, np.fromiter(self._d2, dtype=np.float64))
        self.curve_d3.setData(t, np.fromiter(self._d3, dtype=np.float64))
        self.curve_force.setData(t, np.fromiter(self._force, dtype=np.float64))
        if t_rel > WINDOW_SEC:
            self.plot.setXRange(t_rel - WINDOW_SEC, t_rel, padding=0)
        else:
            self.plot.setXRange(0, WINDOW_SEC, padding=0)

        self._hz_count += 1
        now = time.monotonic()
        dt = now - self._last_hz_time
        if dt >= 1.0:
            self._rate_hz = self._hz_count / dt
            self._hz_count = 0
            self._last_hz_time = now
            self.status_label.setText(f"Connected  ·  {self._rate_hz:.0f} Hz")

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._session.active:
            self._stop_session()
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait(2000)
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("ColorimeterGUI")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
