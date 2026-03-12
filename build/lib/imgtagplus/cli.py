"""Command-line interface for ImgTagPlus."""

from __future__ import annotations

import argparse
import sys
import os
import signal
import subprocess
import time
from pathlib import Path

import tempfile
from imgtagplus import __version__

PID_FILE = Path(tempfile.gettempdir()) / "imgtagplus_server.pid"

def _get_server_pid() -> int | None:
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except ValueError:
            return None
    return None

def _is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True

def start_server_daemon(ffsa: bool = False, sandbox_dir: str | None = None) -> None:
    """Spawns the FastAPI server in the background."""
    pid = _get_server_pid()
    if pid and _is_process_running(pid):
        print(f"Server is already running (PID {pid}).")
        return
        
    print("Starting ImgTagPlus Web UI...")
    
    # We run the uvicorn server via our server.py entrypoint
    # For a robust daemon, we use subprocess.Popen
    server_script = Path(__file__).parent.parent / "server.py"
    
    # Ensure .imgtagplus directory exists
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Start process
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent)
    if ffsa:
        env["IMGTAGPLUS_FFSA"] = "1"
    if sandbox_dir:
        env["IMGTAGPLUS_SANDBOX_DIR"] = str(sandbox_dir)
    
    # We use python -m uvicorn or directly python server.py
    proc = subprocess.Popen(
        [sys.executable, str(server_script)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        start_new_session=True # Detach from terminal
    )
    
    PID_FILE.write_text(str(proc.pid))
    print(f"Server started on http://127.0.0.1:5000 (PID {proc.pid})")

def stop_server_daemon() -> None:
    """Stops the FastAPI server."""
    pid = _get_server_pid()
    if not pid or not _is_process_running(pid):
        print("Server is not currently running.")
        if PID_FILE.exists():
            PID_FILE.unlink()
        return

    print(f"Stopping Server (PID {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        # Wait a moment
        time.sleep(1)
        if _is_process_running(pid):
            os.kill(pid, signal.SIGKILL)
    except OSError as e:
        print(f"Error stopping process: {e}")
        
    if PID_FILE.exists():
        PID_FILE.unlink()
    print("Server stopped.")

def restart_server_daemon() -> None:
    stop_server_daemon()
    time.sleep(1)
    start_server_daemon()

def print_menu():
    print("\n" + "="*40)
    print("  ImgTagPlus Interactive Manager")
    print("="*40)
    
    pid = _get_server_pid()
    is_running = pid and _is_process_running(pid)
    
    status = "\033[92mRunning\033[0m" if is_running else "\033[91mStopped\033[0m"
    print(f"  Web UI Status: {status}")
    if is_running:
        print("  URL: http://127.0.0.1:5000")
        
    print("-" * 40)
    print("  [1] Start Web UI Server (Sandbox Access)")
    print("  [2] Start Web UI Server (Full File Access)")
    print("  [3] Stop Web UI Server")
    print("  [4] Restart Web UI Server")
    print("  [5] Run Tagging Task (Headless Prompt)")
    print("  [0] Exit")
    print("="*40)

def run_interactive_menu():
    """Interactive CLI menu loop."""
    while True:
        print_menu()
        choice = input("\nSelect an option: ").strip()
        
        if choice == '1':
            start_server_daemon(ffsa=False)
        elif choice == '2':
            start_server_daemon(ffsa=True)
        elif choice == '3':
            stop_server_daemon()
        elif choice == '4':
            restart_server_daemon()
        elif choice == '5':
            print("\n[Headless Tagging Task]")
            input_path = input("Enter directory path to scan: ").strip()
            if not input_path:
                print("Operation cancelled.")
                continue
                
            from imgtagplus.profiler import AVAILABLE_MODELS
            print("\nAvailable Models:")
            for m in AVAILABLE_MODELS.values():
                print(f" - {m['id']} ({m['name']})")
                
            model_id = input("\nEnter model ID (default 'clip'): ").strip()
            if not model_id:
                model_id = "clip"

            output_dir_str = input("\nOutput directory for XMP files (leave blank for alongside source): ").strip()
            output_dir = Path(output_dir_str) if output_dir_str else None
                
            # Create mock args and pass to app.py
            args = argparse.Namespace(
                input=Path(input_path),
                recursive=True,
                threshold=0.25,
                max_tags=20,
                silent=False,
                continue_on_error=True,
                log_file=None,
                model_dir=None,
                model_id=model_id,
                output_dir=output_dir
            )
            
            from imgtagplus.app import run
            run(args)
            input("\nPress Enter to return to menu...")
            
        elif choice == '0' or choice.lower() in ('q', 'quit', 'exit'):
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    p = argparse.ArgumentParser(
        prog="imgtagplus",
        description=(
            "ImgTagPlus — Local AI image tagger and Web UI Manager.\n\n"
            "Run without arguments for an interactive menu:\n"
            "  $ imgtagplus\n\n"
            "Manage Web server:\n"
            "  $ imgtagplus --start-server\n"
            "  $ imgtagplus --stop-server\n\n"
            "Or run headless tagging:\n"
            "  $ imgtagplus -i ./photos/ --model-id florence-2-base -r"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    p.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # ── Server Management ──────────────────────────────────────────────────
    p.add_argument("--start-server", action="store_true", help="Start the Web UI server in the background")
    p.add_argument("--stop-server", action="store_true", help="Stop the Web UI server")
    p.add_argument("--restart-server", action="store_true", help="Restart the Web UI server")
    p.add_argument("--full-file-system-access", "--ffsa", action="store_true", help="Allow Web UI file picker to access the entire file system")
    p.add_argument("--sandbox", action="store_true", default=True, help="Run Web UI in sandbox mode (default). File picker restricted to sandbox directory.")
    p.add_argument("--sandbox-dir", type=Path, default=None, help="Custom sandbox directory path (default: ./sandbox)")

    # ── Input / Output (Headless) ──────────────────────────────────────────
    p.add_argument(
        "-i", "--input",
        type=Path,
        default=None,
        help="Path to a single image or a directory of images.",
    )
    p.add_argument(
        "-r", "--recursive",
        action="store_true",
        default=False,
        help="Scan directories recursively.",
    )
    p.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=None,
        help="Directory for XMP sidecar files. Default: alongside each source image.",
    )

    # ── Model / Tagging ────────────────────────────────────────────────────
    p.add_argument(
        "--model-id",
        type=str,
        default="clip",
        help="Model ID to use (e.g., 'clip', 'florence-2-base'). Default: 'clip'.",
    )
    p.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.25,
        help="Minimum confidence score to keep a tag (default: 0.25).",
    )
    p.add_argument(
        "-n", "--max-tags",
        type=int,
        default=20,
        help="Maximum number of tags per image (default: 20).",
    )
    p.add_argument(
        "--model-dir",
        type=Path,
        default=None,
        help="Directory for cached model files (default: ~/.cache/imgtagplus).",
    )

    # ── Execution mode ─────────────────────────────────────────────────────
    p.add_argument(
        "-s", "--silent",
        action="store_true",
        default=False,
        help="Run without interactive prompts (only warnings/errors to console).",
    )
    p.add_argument(
        "-c", "--continue-on-error",
        action="store_true",
        default=False,
        help="Skip images that cause errors instead of stopping.",
    )
    p.add_argument(
        "--input-timeout",
        type=int,
        default=30,
        help="Seconds to wait before auto-continuing on error.",
    )

    # ── Logging ────────────────────────────────────────────────────────────
    p.add_argument(
        "-l", "--log-file",
        type=Path,
        default=None,
        help="Custom log file path (default: imgtagplus_TIMESTAMP.log).",
    )

    return p

def main(argv: list[str] | None = None) -> None:
    """Entry point — parse args and run the application."""
    # If no arguments are provided to the script, launch the interactive menu
    if (argv is None and len(sys.argv) == 1) or (argv is not None and len(argv) == 0):
        # We handle KeyboardInterrupt gracefully for the menu
        try:
            run_interactive_menu()
        except KeyboardInterrupt:
            print("\nExiting...")
        sys.exit(0)

    parser = build_parser()
    args = parser.parse_args(argv)

    # Handle Server Commands
    if args.start_server:
        start_server_daemon(
            ffsa=args.full_file_system_access,
            sandbox_dir=str(args.sandbox_dir) if args.sandbox_dir else None
        )
        sys.exit(0)
    elif args.stop_server:
        stop_server_daemon()
        sys.exit(0)
    elif args.restart_server:
        restart_server_daemon()
        sys.exit(0)

    # Handle Headless Tagging Request
    if args.input is None:
        parser.error("The -i/--input argument is required for headless tagging.")

    # Lazy import to keep CLI parsing fast.
    from imgtagplus.app import run  # noqa: E402
    sys.exit(run(args))
