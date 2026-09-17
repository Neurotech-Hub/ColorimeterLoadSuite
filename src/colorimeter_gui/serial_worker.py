"""Background serial reader for the load-cell CSV stream."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import serial
import serial.tools.list_ports
from PySide6.QtCore import QMutex, QThread, Signal


BAUD = 115200
# Full-scale load (grams) for donut colormap.
LOAD_MAX = 3000


@dataclass(frozen=True)
class Sample:
    millis: int
    d1: int
    d2: int
    d3: int
    force: int


def list_serial_ports() -> List[Tuple[str, str]]:
    """Return (device, description) pairs for available serial ports."""
    ports = []
    for info in serial.tools.list_ports.comports():
        desc = info.description or "Serial"
        ports.append((info.device, f"{info.device} — {desc}"))
    return ports


def parse_sample_line(line: str) -> Optional[Sample]:
    """Parse ``millis,d1,d2,d3,force``; return None if not a data row."""
    line = line.strip()
    if not line or line.startswith("millis,"):
        return None
    parts = line.split(",")
    if len(parts) != 5:
        return None
    try:
        millis, d1, d2, d3, force = map(int, parts)
    except ValueError:
        return None
    return Sample(millis, d1, d2, d3, force)


class SerialWorker(QThread):
    """Read CSV samples off the UI thread.

    No header sync — any newline-terminated line with five integers is a
    sample. Invalid / partial lines are skipped.
    """

    sample = Signal(object)  # Sample
    status = Signal(str)
    error = Signal(str)
    finished_clean = Signal()

    def __init__(self, port: str, baud: int = BAUD, parent=None) -> None:
        super().__init__(parent)
        self._port_name = port
        self._baud = baud
        self._stop = False
        self._mutex = QMutex()
        self._ser: Optional[serial.Serial] = None

    def stop(self) -> None:
        self._mutex.lock()
        self._stop = True
        self._mutex.unlock()

    def _should_stop(self) -> bool:
        self._mutex.lock()
        flag = self._stop
        self._mutex.unlock()
        return flag

    def run(self) -> None:
        try:
            self._ser = serial.Serial(
                self._port_name,
                self._baud,
                timeout=0.2,
            )
        except serial.SerialException as exc:
            self.error.emit(f"Open failed: {exc}")
            self.finished_clean.emit()
            return

        self.status.emit("Streaming")
        try:
            self._read_loop()
        finally:
            self._close()
            self.finished_clean.emit()

    def _read_loop(self) -> None:
        while not self._should_stop():
            try:
                raw = self._ser.readline()
            except serial.SerialException as exc:
                self.error.emit(f"Device disconnected: {exc}")
                return
            if not raw:
                continue
            try:
                line = raw.decode("utf-8", errors="replace")
            except Exception:
                continue
            sample = parse_sample_line(line)
            if sample is not None:
                self.sample.emit(sample)

    def _close(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
