import asyncio
import json
import logging
import queue
import argparse
import sys
import threading
from pathlib import Path
from logging.handlers import QueueHandler
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from imgtagplus.profiler import get_model_recommendations, get_profiler_summary
from imgtagplus.app import run as app_run

# Ensure static folder exists
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

app = FastAPI(title="ImgTagPlus Web UI")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Global state for SSE streaming
log_queue = queue.Queue()
progress_queue = queue.Queue()
is_processing = False

class SSEQueueHandler(logging.Handler):
    """Intercepts python logs to send them to the SSE stream."""
    def emit(self, record):
        try:
            msg = self.format(record)
            log_queue.put({"type": "log", "level": record.levelname, "message": msg})
        except Exception:
            self.handleError(record)

# Attach handler to imgtagplus logger
sse_handler = SSEQueueHandler()
sse_handler.setFormatter(logging.Formatter('%(message)s'))
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

@app.get("/api/browse")
async def browse_directory(path: str = ""):
    """Returns directory contents for the file picker."""
    if not path:
        current_path = Path.home() if FFSA_ENABLED else SANDBOX_ROOT
    else:
        current_path = Path(path)
        
    if not current_path.exists() or not current_path.is_dir():
        return {"error": "Directory does not exist"}
        
    # Security: check if path is within sandbox
    if not FFSA_ENABLED:
        try:
            current_path.resolve().relative_to(SANDBOX_ROOT.resolve())
        except ValueError:
            return {"error": "Access denied: Path is outside the sandbox"}
            
    items = []
    # Up directory if not at root/sandbox root
    if current_path != (Path.home() if FFSA_ENABLED else SANDBOX_ROOT) and current_path != Path(current_path.root):
        items.append({"name": "..", "path": str(current_path.parent), "is_dir": True})
        
    try:
        for item in sorted(current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if not item.name.startswith("."): # hide hidden files
                if item.is_dir():
                    items.append({"name": item.name, "path": str(item), "is_dir": True})
    except PermissionError:
        return {"error": "Permission denied reading directory"}
        
    return {
        "current_path": str(current_path),
        "items": items,
        "sandbox": not FFSA_ENABLED
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
    return {"is_processing": is_processing}

@app.post("/api/tag")
async def start_tagging(request: Request):
    """Starts the imgtagplus tagging job in a background thread."""
    global is_processing
    if is_processing:
        return {"error": "A tagging job is already in progress"}
    
    data = await request.json()
    input_path = data.get("input")
    model_id = data.get("model_id", "clip")
    threshold = float(data.get("threshold", 0.25))
    max_tags = int(data.get("max_tags", 20))
    recursive = bool(data.get("recursive", False))
    output_dir_str = data.get("output_dir")
    output_dir = Path(output_dir_str) if output_dir_str else None
    accelerator = data.get("accelerator")
    
    if not input_path or not os.path.exists(input_path):
        return {"error": f"Invalid or non-existent path: {input_path}"}
        
    # Clear queues before starting
    while not log_queue.empty(): log_queue.get()
    while not progress_queue.empty(): progress_queue.get()
        
    def progress_callback(current, total, filename):
        progress_queue.put({"type": "progress", "current": current, "total": total, "filename": filename})

    def run_worker():
        global is_processing
        is_processing = True
        try:
            args = argparse.Namespace(
                input=Path(input_path),
                recursive=recursive,
                threshold=threshold,
                max_tags=max_tags,
                silent=True,
                continue_on_error=True,
                log_file=None, # use default
                model_dir=None, # use default
                model_id=model_id,
                output_dir=output_dir,
                accelerator=accelerator
            )
            progress_queue.put({"type": "progress", "current": 0, "total": 0, "filename": "Scanning files..."})
            app_run(args, progress_callback=progress_callback)
        except Exception as e:
            log_queue.put({"type": "log", "level": "ERROR", "message": f"Worker crashed: {e}"})
        finally:
            is_processing = False
            progress_queue.put({"type": "done"})

    thread = threading.Thread(target=run_worker, daemon=True)
    thread.start()
    return {"status": "started"}

@app.get("/api/stream")
async def sse_stream():
    """Server-Sent Events mechanism for streaming logs and progress."""
    async def event_generator():
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
                    
            if not is_processing and log_queue.empty() and progress_queue.empty():
                yield "data: {\"type\": \"idle\"}\n\n"
                
            await asyncio.sleep(0.1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/logs/download")
async def download_log():
    """Returns the most recent log file."""
    log_files = list(Path.cwd().glob("imgtagplus_*.log"))
    if not log_files:
        return HTMLResponse("No log files found.", status_code=404)
    # Sort by modification time to get the latest
    latest_log = sorted(log_files, key=lambda p: p.stat().st_mtime)[-1]
    return FileResponse(path=latest_log, filename=latest_log.name)

def start_server(host="127.0.0.1", port=5000):
    """Entry point for CLI to spin up the server."""
    logging.info(f"Starting Web UI on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")

if __name__ == "__main__":
    start_server()
