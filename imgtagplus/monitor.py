"""System resource monitor for ImgTagPlus.

Runs a lightweight background thread that samples CPU and RAM usage at
regular intervals.  Provides summary statistics when stopped.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field

import psutil


@dataclass
class Stats:
    """Resource-usage statistics collected over a run."""

    elapsed_seconds: float = 0.0
    cpu_samples: list[float] = field(default_factory=list)
    ram_samples: list[float] = field(default_factory=list)  # in MB

    # -- derived properties ---------------------------------------------------

    @property
    def avg_cpu(self) -> float:
        return sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0.0

    @property
    def peak_cpu(self) -> float:
        return max(self.cpu_samples) if self.cpu_samples else 0.0

    @property
    def avg_ram_mb(self) -> float:
        return sum(self.ram_samples) / len(self.ram_samples) if self.ram_samples else 0.0

    @property
    def peak_ram_mb(self) -> float:
        return max(self.ram_samples) if self.ram_samples else 0.0

    def summary(self) -> str:
        """Return a human-readable summary string."""
        minutes, seconds = divmod(self.elapsed_seconds, 60)
        hours, minutes = divmod(int(minutes), 60)
        if hours:
            elapsed = f"{hours}h {minutes}m {seconds:.1f}s"
        elif minutes:
            elapsed = f"{int(minutes)}m {seconds:.1f}s"
        else:
            elapsed = f"{seconds:.1f}s"

        return (
            f"Elapsed time  : {elapsed}\n"
            f"Avg CPU usage : {self.avg_cpu:.1f}%\n"
            f"Peak CPU usage: {self.peak_cpu:.1f}%\n"
            f"Avg RAM usage : {self.avg_ram_mb:.1f} MB\n"
            f"Peak RAM usage: {self.peak_ram_mb:.1f} MB"
        )


class Monitor:
    """Background resource monitor.

    Usage::

        mon = Monitor()
        mon.start()
        # … do work …
        stats = mon.stop()
        print(stats.summary())
    """

    def __init__(self, interval: float = 1.0) -> None:
        self._interval = interval
        self._process = psutil.Process()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._stats = Stats()
        self._start_time: float = 0.0

    # -- public API -----------------------------------------------------------

    def start(self) -> None:
        """Begin sampling in the background."""
        # Prime CPU measurement (first call returns 0.0)
        self._process.cpu_percent()
        self._start_time = time.monotonic()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> Stats:
        """Stop sampling and return the collected :class:`Stats`."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._stats.elapsed_seconds = time.monotonic() - self._start_time
        return self._stats

    # -- internals ------------------------------------------------------------

    def _run(self) -> None:
        cpu_count = os.cpu_count() or 1
        while not self._stop_event.is_set():
            try:
                cpu = self._process.cpu_percent() / cpu_count  # normalise to 0-100%
                mem = self._process.memory_info().rss / (1024 * 1024)  # bytes -> MB
                self._stats.cpu_samples.append(cpu)
                self._stats.ram_samples.append(mem)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            self._stop_event.wait(self._interval)
