# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Pytest-based test suite for scanner, metadata, profiler, and server validation.
- CI workflow with Ruff and pytest checks.
- `/health` endpoint for local readiness checks.
- Development dependency and install split for CLIP-only vs full environments.
- Project docs: `SPEC.md`, `CONTRIBUTING.md`, and this changelog.

### Changed

- `/api/tag` now enforces sandbox restrictions and clamps `threshold`/`max_tags`.
- Florence remote-code loading is pinned to a reviewed revision.
- Server job management now uses queue bounds, deterministic log lookup, and HTTP security headers.
- `setup.sh` now builds frontend CSS when npm is available.

## [1.0.0]

### Added

- Initial ImgTagPlus release.
