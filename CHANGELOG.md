# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- TUI: arrow key (↑/↓) navigation across dashboard action buttons; first button auto-focused on load so keyboard navigation is available without a Tab press.
- TUI: "Server detected" toast notification at startup when the web UI server is already running, showing the URL and access mode.
- TUI: `ExitConfirmScreen` modal when quitting with the server running — offers stop-and-exit, keep-running-and-exit, or cancel.

### Changed

- TUI: `q` binding delegates to `ImgTagPlusApp.action_quit()` so both `q` and Ctrl+C funnel through the same exit-confirmation path.
- TUI: command palette disabled (`ENABLE_COMMAND_PALETTE = False`) — Ctrl+P no longer opens the Textual command launcher.

- Pytest-based test suite for scanner, metadata, profiler, and server validation.
- Integration tests for `app.run()` pipeline (happy path, continue-on-error, progress callback, overwrite, zero-images).
- CI workflow with Ruff and pytest checks; Python 3.10/3.11/3.12 matrix; CSS build step.
- `/health` endpoint for local readiness checks.
- Development dependency and install split for CLIP-only vs full environments.
- Project docs: `SPEC.md`, `CONTRIBUTING.md`, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md`, and this changelog.
- `--input-timeout` CLI option (default 30 s) to auto-skip error prompts after a timeout.
- `--model-dir` CLI option for custom model cache directory.
- Rate limiting on `/api/browse` (100 req/10 s) and `/api/tag` (10 req/10 s) per client IP.
- CSRF origin validation on POST/PUT/DELETE — only localhost origins accepted.
- SSE connection limit (5 concurrent clients via semaphore).
- XSS protection: `escapeHtml()` applied to all server-provided strings in the frontend.
- Florence-2 compound keyword extraction from adjacent caption word pairs.
- Zero-images edge case handling: yellow "No Images Found" UI state, WARNING log, and progress callback signal.

### Changed

- **Breaking:** Minimum Python version is now 3.10 (was 3.9).
- `/api/tag` now enforces sandbox restrictions and clamps `threshold`/`max_tags`.
- Florence `trust_remote_code` is now guarded to only enable for model IDs in the pinned revision allowlist.
- Florence compatibility patches are version-gated to transformers 4.44–4.x.
- XMP reading scoped to `dc:subject` (ignores unrelated XMP namespaces).
- Server and static assets relocated into the `imgtagplus/` package.
- Server job management now uses queue bounds, deterministic log lookup, and HTTP security headers.
- `setup.sh` now checks Python ≥ 3.10 at startup, builds frontend CSS when npm is available, and supports `--dev` flag for dev dependencies.
- Removed duplicate "futuristic" entry from CLIP tag vocabulary.
- `.gitignore` now includes `.env*` patterns.

## [1.0.0]

### Added

- Initial ImgTagPlus release.
