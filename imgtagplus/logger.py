"""Logging configuration for ImgTagPlus.

Sets up dual-output logging: detailed file log (DEBUG) and console log
(INFO, or suppressed in silent mode).
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_DIR = Path.cwd().resolve()


def setup_logging(
    log_file: Path | None = None,
    silent: bool = False,
) -> Path:
    """Configure the root logger and return the resolved log-file path.

    Parameters
    ----------
    log_file:
        Explicit path for the log file.  When *None* a timestamped file is
        created in the current working directory.
    silent:
        If ``True`` the console handler is set to WARNING so that only
        errors and warnings are printed.
    """
    if log_file is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = DEFAULT_LOG_DIR / f"imgtagplus_{ts}.log"

    log_file = log_file.resolve()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Remove any pre-existing handlers (safe for re-entry)
    root.handlers.clear()

    # ── File handler (DEBUG) ──────────────────────────────────────────────
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(fh)

    # ── Console handler ───────────────────────────────────────────────────
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.WARNING if silent else logging.INFO)
    ch.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(ch)

    return log_file
