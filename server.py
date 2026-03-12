"""FastAPI server for the local ImgTagPlus web UI.

The server keeps a single background tagging job alive at a time and mirrors
logs/progress to the browser via Server-Sent Events so the frontend can stay
simple and stateless.
"""

import argparse
import asyncio
import json
import logging
import os
import queue
import threading
from pathlib import Path

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


def _is_processing() -> bool:
    """Return whether the single worker slot is currently busy."""
    return _job_lock.locked()


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
async def browse_directory(path: str = ""):
    """List visible directories for the file picker within the allowed root."""
    if not path:
        current_path = Path.home() if FFSA_ENABLED else SANDBOX_ROOT
    else:
        current_path = Path(path)

    if not current_path.exists() or not current_path.is_dir():
        return {"error": "Directory does not exist"}

    if not FFSA_ENABLED:
        try:
            current_path.resolve().relative_to(SANDBOX_ROOT.resolve())
        except ValueError:
            return {"error": "Access denied: Path is outside the sandbox"}

    items = []
    if current_path != (Path.home() if FFSA_ENABLED else SANDBOX_ROOT) and current_path != Path(current_path.root):
        items.append({"name": "..", "path": str(current_path.parent), "is_dir": True})

    try:
        for item in sorted(current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if not item.name.startswith("."):
                if item.is_dir():
                    items.append({"name": item.name, "path": str(item), "is_dir": True})
    except PermissionError:
        return {"error": "Permission denied reading directory"}

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
    return {"is_processing": _is_processing()}


@app.get("/health")
async def health_check():
    """Return a simple readiness response for local process management."""
    return {"status": "ok"}

@app.post("/api/tag")
async def start_tagging(request: Request):
    """Validate a tag request and launch the single background worker."""
    if not _job_lock.acquire(blocking=False):
        return {"error": "A tagging job is already in progress"}

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
        return {"error": "Invalid or non-existent path: None"}

    input_path = Path(input_path_raw)
    if not input_path.exists():
        return {"error": f"Invalid or non-existent path: {input_path}"}

    _assert_sandbox(input_path)
    _assert_sandbox(output_dir)

    _drain_queue(log_queue)
    _drain_queue(progress_queue)

    def progress_callback(current, total, filename):
        _enqueue_latest(
            progress_queue,
            {"type": "progress", "current": current, "total": total, "filename": filename},
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
                overwrite=overwrite
            )
            _enqueue_latest(
                progress_queue,
                {"type": "progress", "current": 0, "total": 0, "filename": "Scanning files..."},
            )
            app_run(args, progress_callback=progress_callback)
        except Exception as e:
            _enqueue_latest(
                log_queue,
                {"type": "log", "level": "ERROR", "message": f"Worker crashed: {e}"},
            )
        finally:
            if _job_lock.locked():
                _job_lock.release()
            _enqueue_latest(progress_queue, {"type": "done"})

    thread = threading.Thread(target=run_worker, daemon=True)
    thread.start()
    return {"status": "started"}

@app.get("/api/stream")
async def sse_stream():
    """Stream batched log/progress updates and idle heartbeats to the browser."""

    async def event_generator():
        try:
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
                try:
                    while True:
                        prog = progress_queue.get_nowait()
                        is_done = prog.get('type') == 'done'
                        event_data = json.dumps({
                            "type": "progress",
                            "current": prog.get('current', 0),
                            "total": prog.get('total', 0),
                            "filename": prog.get('filename', ''),
                            "done": is_done
                        })
                        yield f"data: {event_data}\n\n"
                        await asyncio.sleep(0.01)
                except queue.Empty:
                    pass

                if not _is_processing() and log_queue.empty() and progress_queue.empty():
                    yield "data: {\"type\": \"idle\"}\n\n"

                await asyncio.sleep(0.1)
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
