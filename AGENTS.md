# AGENTS.md — Coding Guidelines for ImgTagPlus

ImgTagPlus is a Python CLI/Web tool for AI-powered image tagging using CLIP/Florence models via ONNX Runtime. Tags are saved as XMP sidecar files for DAM compatibility.

---

## Build / Lint / Test Commands

### Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Run all tests
```bash
pytest
```

### Run a single test file
```bash
pytest tests/test_cli.py
```

### Run a single test function
```bash
pytest tests/test_cli.py::test_start_server_daemon_does_not_restart_when_mode_matches -v
```

### Lint / format code
```bash
ruff check .          # Check for lint errors
ruff check --fix .    # Auto-fix lint errors
ruff format .         # Format code
```

### Build frontend CSS
```bash
npm install
npm run build:css     # Compiles Tailwind CSS
```

### Pre-download models for development
```bash
python -m imgtagplus -i ./test_image.jpg --model-id clip --silent --output-dir /tmp/imgtagplus-model-warmup
```

---

## Code Style Guidelines

### Python Version
- Requires Python >= 3.10
- Use modern type hints (e.g., `str | None`, `list[int]`)

### Imports
- Always use `from __future__ import annotations` at the top
- Group imports: stdlib → third-party → local (imgtagplus)
- Use absolute imports for local modules: `from imgtagplus.tagger import ...`

### Formatting
- Line length: 120 characters (configured in pyproject.toml)
- Use Ruff for linting and formatting
- Trailing commas in multi-line structures

### Type Hints
- Use type hints on all function parameters and return values
- Prefer modern union syntax: `str | None` over `Optional[str]`
- Use `from __future__ import annotations` to enable forward references

### Naming Conventions
- `snake_case` for functions, variables, methods
- `PascalCase` for classes
- `UPPER_CASE` for module-level constants and enums
- Private functions/vars: `_leading_underscore`
- Internal constants: `_UPPER_CASE` with leading underscore

### Error Handling
- Catch specific exceptions, avoid bare `except:`
- Use `log = logging.getLogger(__name__)` for module logging
- Handle timeouts and network errors gracefully
- Provide informative error messages to users

### Documentation
- Module-level docstrings explaining purpose
- Function docstrings for public APIs
- Comments for complex algorithms or non-obvious code

---

## Testing Guidelines

### Test Organization
- Tests live in `tests/` directory
- Test files named `test_*.py`
- Test functions named `test_*`
- Use `conftest.py` for shared fixtures

### Writing Tests
- Use pytest fixtures (e.g., `tmp_path`, `monkeypatch`)
- Mock external dependencies (filesystem, network, processes)
- Test both success and error paths
- Keep tests isolated and deterministic

### Running Tests
- Use `-v` for verbose output
- Use `-k pattern` to filter tests by name

---

## Project Structure

```
imgtagplus/
  __init__.py       # Package version
  cli.py            # CLI entry points and argument parsing
  app.py            # Main orchestrator for tagging runs
  tagger.py         # CLIP-based image tagging
  vlm.py            # Florence-2 VLM integration
  server.py         # FastAPI web server
  scanner.py        # Image file discovery
  metadata.py       # XMP sidecar writing
  monitor.py        # Progress monitoring
  profiler.py       # Model management
  tags.py           # Tag vocabulary
  tui.py            # Textual TUI interface
  logger.py         # Logging setup

 tests/             # Test suite
 docs/              # Documentation
 website/           # Project website
```

---

## CI / Automation

GitHub Actions runs on push/PR:
- Tests across Python 3.10, 3.11, 3.12
- Ruff linting
- Full test suite with pytest

---

## Key Patterns

### Lazy Imports
Keep CLI fast by deferring heavy imports:
```python
def run(args):
    from imgtagplus.app import run  # noqa: E402
    sys.exit(run(args))
```

### Model Caching
Models cache to `~/.cache/imgtagplus` or repo-local `.cache/imgtagplus`.
Never commit model files to Git.

### Server Lifecycle
- PID file: `/tmp/imgtagplus_server_{uid}.pid`
- State file: `/tmp/imgtagplus_server_{uid}.json`
- Health endpoint: `http://127.0.0.1:5000/health`

---

## Contributing Notes

See `CONTRIBUTING.md` for detailed guidelines.

Before PR:
1. Run `ruff check .`
2. Run `pytest`
3. Update `CHANGELOG.md` for user-visible changes
4. Keep sandbox/local-only safety behavior intact
