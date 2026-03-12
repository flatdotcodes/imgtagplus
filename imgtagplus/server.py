"""FastAPI server for the local ImgTagPlus web UI.

The server keeps a single background tagging job alive at a time and mirrors
logs/progress to the browser via Server-Sent Events so the frontend can stay
simple and stateless.
"""

import argparse
import asyncio
import collections
import json
import logging
import os
import queue
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from imgtagplus.app import run as app_run
from imgtagplus.logger import DEFAULT_LOG_DIR
from imgtagplus.profiler import get_model_recommendations, get_profiler_summary

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

app = FastAPI(title="ImgTagPlus Web UI")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

QUEUE_MAXSIZE = 1000
log_queue = queue.Queue(maxsize=QUEUE_MAXSIZE)
progress_queue = queue.Queue(maxsize=QUEUE_MAXSIZE)
_job_lock = threading.Lock()
_job_state_lock = threading.Lock()
_job_started_at: datetime | None = None
_job_started_monotonic: float | None = None
_last_job_runtime_seconds: int | None = None
_sse_semaphore = asyncio.Semaphore(5)

_rate_limits: dict[str, collections.deque] = {}
_RATE_LIMIT_WINDOW = 10  # seconds


def _check_rate_limit(client_ip: str, limit: int) -> bool:
    """Return True if the request should be allowed."""
    now = time.monotonic()
    if client_ip not in _rate_limits:
        _rate_limits[client_ip] = collections.deque()
    timestamps = _rate_limits[client_ip]
    while timestamps and now - timestamps[0] > _RATE_LIMIT_WINDOW:
        timestamps.popleft()
    if len(timestamps) >= limit:
        return False
    timestamps.append(now)
    return True


def _is_processing() -> bool:
    """Return whether the single worker slot is currently busy."""
    return _job_lock.locked()


def _mark_job_started() -> str:
    """Record the start of the active job and return an ISO timestamp."""
    started_at = datetime.now().astimezone()
    with _job_state_lock:
        global _job_started_at, _job_started_monotonic, _last_job_runtime_seconds
        _job_started_at = started_at
        _job_started_monotonic = time.monotonic()
        _last_job_runtime_seconds = None
    return started_at.isoformat()


def _current_runtime_seconds() -> int | None:
    """Return the active job runtime in whole seconds, if available."""
    with _job_state_lock:
        if _job_started_monotonic is None:
            return None
        return max(0, int(time.monotonic() - _job_started_monotonic))


def _mark_job_finished() -> int | None:
    """Finalize job timing state and return the total runtime in seconds."""
    with _job_state_lock:
        global _job_started_at, _job_started_monotonic, _last_job_runtime_seconds
        runtime_seconds = None
        if _job_started_monotonic is not None:
            runtime_seconds = max(0, int(time.monotonic() - _job_started_monotonic))
        _last_job_runtime_seconds = runtime_seconds
        _job_started_at = None
        _job_started_monotonic = None
        return runtime_seconds


def _job_status_payload() -> dict[str, object]:
    """Return the frontend-facing snapshot of the current job state."""
    with _job_state_lock:
        started_at = _job_started_at.isoformat() if _job_started_at is not None else None
        last_runtime = _last_job_runtime_seconds

    runtime_seconds = _current_runtime_seconds() if _is_processing() else last_runtime
    return {
        "is_processing": _is_processing(),
        "started_at": started_at,
        "runtime_seconds": runtime_seconds,
    }


def _enqueue_latest(target_queue: queue.Queue, item: dict) -> None:
    """Queue an SSE payload, dropping the oldest entry if the buffer is full."""
    try:
        target_queue.put_nowait(item)
    except queue.Full:
        # Prefer fresh UI state over preserving a stale backlog.
        try:
            target_queue.get_nowait()
        except queue.Empty:
            pass
        target_queue.put_nowait(item)


def _drain_queue(target_queue: queue.Queue) -> None:
    """Discard queued SSE events so a new job starts with a clean stream."""
    while True:
        try:
            target_queue.get_nowait()
        except queue.Empty:
            break


class SSEQueueHandler(logging.Handler):
    """Mirror application logs into the SSE stream consumed by the browser."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            _enqueue_latest(log_queue, {"type": "log", "level": record.levelname, "message": msg})
        except Exception:
            self.handleError(record)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Apply a restrictive CSP because the UI only serves local static assets."""
    if request.method in ("POST", "PUT", "DELETE"):
        origin = request.headers.get("origin")
        if origin:
            parsed = urlparse(origin)
            if parsed.hostname not in ("localhost", "127.0.0.1"):
                return HTMLResponse("Forbidden: cross-origin request", status_code=403)

    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self'"
    )
    return response

sse_handler = SSEQueueHandler()
sse_handler.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger("imgtagplus").addHandler(sse_handler)
logging.getLogger("imgtagplus").setLevel(logging.INFO)


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serves the main frontend UI."""
    index_file = static_dir / "index.html"
    if not index_file.exists():
        return HTMLResponse("Static file 'index.html' not found.", status_code=404)
    with open(index_file, "r") as f:
        return f.read()

FFSA_ENABLED = os.environ.get("IMGTAGPLUS_FFSA") == "1"
SANDBOX_ROOT = Path(os.environ.get("IMGTAGPLUS_SANDBOX_DIR", Path(__file__).parent / "sandbox"))
SANDBOX_ROOT.mkdir(exist_ok=True)


def _assert_sandbox(path: Path | None) -> None:
    """Reject paths outside the sandbox unless unrestricted browsing is enabled."""
    if path is None or FFSA_ENABLED:
        return

    try:
        path.resolve().relative_to(SANDBOX_ROOT.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Access denied: path outside sandbox") from exc

@app.get("/api/browse")
async def browse_directory(request: Request, path: str = ""):
    """List visible directories for the file picker within the allowed root."""
    client_ip = request.client.host if request and request.client else "unknown"
    if not _check_rate_limit(client_ip, 100):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    if not path:
        current_path = Path.home() if FFSA_ENABLED else SANDBOX_ROOT
    else:
        current_path = Path(path)

    if not current_path.exists() or not current_path.is_dir():
        raise HTTPException(status_code=404, detail="Directory does not exist")

    if not FFSA_ENABLED:
        try:
            current_path.resolve().relative_to(SANDBOX_ROOT.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: Path is outside the sandbox")

    items = []
    if current_path != (Path.home() if FFSA_ENABLED else SANDBOX_ROOT) and current_path != Path(current_path.root):
        items.append({"name": "..", "path": str(current_path.parent), "is_dir": True})

    try:
        for item in sorted(current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if not item.name.startswith("."):
                if item.is_dir():
                    items.append({"name": item.name, "path": str(item), "is_dir": True})
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied reading directory")

    return {
        "current_path": str(current_path),
        "items": items,
        "sandbox": not FFSA_ENABLED,
    }


@app.get("/api/models")
async def get_models():
    """Returns available models based on profiler specs."""
    return {"models": get_model_recommendations()}


@app.get("/api/system")
async def get_system():
    """Returns full system profile."""
    return get_profiler_summary()


@app.get("/api/status")
async def get_status():
    """Check if a tagging job is currently running."""
    return _job_status_payload()


@app.get("/health")
async def health_check():
    """Return a simple readiness response for local process management."""
    return {"status": "ok"}

@app.post("/api/tag")
async def start_tagging(request: Request):
    """Validate a tag request and launch the single background worker."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip, 10):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    data = await request.json()
    input_path_raw = data.get("input")
    model_id = data.get("model_id", "clip")
    threshold = max(0.0, min(1.0, float(data.get("threshold", 0.25))))
    max_tags = max(1, min(200, int(data.get("max_tags", 20))))
    recursive = bool(data.get("recursive", False))
    output_dir_str = data.get("output_dir")
    output_dir = Path(output_dir_str) if output_dir_str else None
    accelerator = data.get("accelerator")
    overwrite = bool(data.get("overwrite", False))

    if not input_path_raw:
        raise HTTPException(status_code=400, detail="Invalid or non-existent path")

    input_path = Path(input_path_raw)
    if not input_path.exists():
        raise HTTPException(status_code=400, detail=f"Invalid or non-existent path: {input_path}")

    _assert_sandbox(input_path)
    _assert_sandbox(output_dir)

    if not _job_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A tagging job is already in progress")

    _drain_queue(log_queue)
    _drain_queue(progress_queue)
    started_at = _mark_job_started()
    _last_progress = {"current": 0, "total": 0}

    def progress_callback(current, total, filename):
        _last_progress["current"] = current
        _last_progress["total"] = total
        _enqueue_latest(
            progress_queue,
            {
                "type": "progress",
                "current": current,
                "total": total,
                "filename": filename,
                "runtime_seconds": _current_runtime_seconds(),
            },
        )

    def run_worker():
        try:
            args = argparse.Namespace(
                input=input_path,
                recursive=recursive,
                threshold=threshold,
                max_tags=max_tags,
                silent=True,
                continue_on_error=True,
                log_file=None, # use default
                model_dir=None, # use default
                model_id=model_id,
                output_dir=output_dir,
                accelerator=accelerator,
                overwrite=overwrite,
                input_timeout=30,
            )
            _enqueue_latest(
                progress_queue,
                {
                    "type": "progress",
                    "current": 0,
                    "total": 0,
                    "filename": "Scanning files...",
                    "runtime_seconds": _current_runtime_seconds(),
                },
            )
            app_run(args, progress_callback=progress_callback)

            if _last_progress["total"] == 0:
                _enqueue_latest(
                    log_queue,
                    {"type": "log", "level": "WARNING",
                     "message": f"No images found at {input_path}. "
                                "Check that the path contains supported image files."},
                )
        except Exception as e:
            _enqueue_latest(
                log_queue,
                {"type": "log", "level": "ERROR", "message": f"Worker crashed: {e}"},
            )
        finally:
            runtime_seconds = _mark_job_finished()
            try:
                _job_lock.release()
            except RuntimeError:
                pass
            _enqueue_latest(progress_queue, {"type": "done", "runtime_seconds": runtime_seconds})

    thread = threading.Thread(target=run_worker, daemon=True)
    thread.start()
    return {"status": "started", "started_at": started_at}

@app.get("/api/stream")
async def sse_stream():
    """Stream batched log/progress updates and idle heartbeats to the browser."""
    if _sse_semaphore.locked():
        raise HTTPException(status_code=429, detail="Too many SSE connections")

    async def event_generator():
        async with _sse_semaphore:
            try:
                sleep_interval = 0.1
                while True:
                    # Send logs first to ensure errors reach the UI before a 'done' event closes the connection
                    chunks = []
                    try:
                        # Batch up to 50 log messages to prevent overwhelming the socket
                        for _ in range(50):
                            log = log_queue.get_nowait()
                            chunks.append(log)
                    except queue.Empty:
                        pass

                    if chunks:
                        for c in chunks:
                            yield f"data: {json.dumps(c)}\n\n"

                    # Send progress updates
                    progress_chunks = []
                    try:
                        while True:
                            prog = progress_queue.get_nowait()
                            progress_chunks.append(prog)
                            is_done = prog.get('type') == 'done'
                            event_data = json.dumps({
                                "type": "progress",
                                "current": prog.get('current', 0),
                                "total": prog.get('total', 0),
                                "filename": prog.get('filename', ''),
                                "done": is_done,
                                "runtime_seconds": prog.get('runtime_seconds'),
                            })
                            yield f"data: {event_data}\n\n"
                            await asyncio.sleep(0.01)
                    except queue.Empty:
                        pass

                    if not _is_processing() and log_queue.empty() and progress_queue.empty():
                        yield "data: {\"type\": \"idle\"}\n\n"

                    if chunks or progress_chunks:
                        sleep_interval = 0.1
                    else:
                        sleep_interval = min(sleep_interval * 1.5, 1.0)
                    await asyncio.sleep(sleep_interval)
            except asyncio.CancelledError:
                logging.getLogger(__name__).debug("SSE client disconnected.")
                return

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/logs/download")
async def download_log():
    """Download the newest CLI log file for the most recent run."""
    log_files = list(DEFAULT_LOG_DIR.glob("imgtagplus_*.log"))
    if not log_files:
        return HTMLResponse("No log files found.", status_code=404)
    # Sort by modification time to get the latest
    latest_log = sorted(log_files, key=lambda p: p.stat().st_mtime)[-1]
    return FileResponse(path=latest_log, filename=latest_log.name)


def start_server(host="127.0.0.1", port=5000):
    """Run the FastAPI app under uvicorn for the local web UI."""
    logging.info(f"Starting Web UI on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    start_server()
