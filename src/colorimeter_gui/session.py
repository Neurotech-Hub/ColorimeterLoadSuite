"""Session CSV recording (Datetime + Force in grams)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO


def session_filename(when: Optional[datetime] = None) -> str:
    """Return load_YYYYMMDD-HHMMSS.csv (unique per second)."""
    when = when or datetime.now()
    return when.strftime("load_%Y%m%d-%H%M%S.csv")


def format_datetime_ms(when: Optional[datetime] = None) -> str:
    """Local datetime with millisecond precision."""
    when = when or datetime.now()
    return when.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class SessionRecorder:
    """Append Force samples to a CSV under a chosen directory."""

    def __init__(self) -> None:
        self._file: Optional[TextIO] = None
        self._path: Optional[Path] = None

    @property
    def active(self) -> bool:
        return self._file is not None

    @property
    def path(self) -> Optional[Path]:
        return self._path

    def start(self, directory: Path) -> Path:
        if self.active:
            raise RuntimeError("Session already recording")
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / session_filename()
        # Avoid clobber if started twice in the same second.
        if path.exists():
            stem = path.stem
            n = 1
            while True:
                candidate = directory / f"{stem}_{n}.csv"
                if not candidate.exists():
                    path = candidate
                    break
                n += 1
        fh = open(path, "w", encoding="utf-8", newline="")
        fh.write("Datetime,Force\n")
        fh.flush()
        self._file = fh
        self._path = path
        return path

    def write_force(self, force_g: float, when: Optional[datetime] = None) -> None:
        if self._file is None:
            return
        force_i = int(round(force_g))
        self._file.write(f"{format_datetime_ms(when)},{force_i}\n")
        self._file.flush()

    def stop(self) -> Optional[Path]:
        path = self._path
        if self._file is not None:
            try:
                self._file.close()
            except Exception:
                pass
        self._file = None
        self._path = None
        return path
