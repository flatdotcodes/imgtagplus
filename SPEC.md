# ImgTagPlus Specification

## Purpose

ImgTagPlus is a local-first image-tagging tool that scans images on disk, runs an AI tagging backend, and writes keywords to XMP sidecar files for DAM workflows.

## Supported execution modes

- Headless CLI runs against a file or directory.
- Local web UI runs on `127.0.0.1:5000`.
- The web UI defaults to sandboxed browsing unless full file system access is explicitly enabled.

## Input behavior

- Supported image extensions are `.jpg`, `.jpeg`, `.png`, `.webp`, `.tiff`, `.tif`, `.bmp`, and `.gif`.
- A single image path processes one file.
- A directory path scans either one level or recursively depending on `--recursive`.
- Missing paths are rejected before processing starts.
- In sandbox mode, server-side browse and tag requests must stay within the configured sandbox root.

## Tagging behavior

- `clip` performs zero-shot tagging against the built-in tag vocabulary.
- `florence-2-base` performs caption-driven keyword extraction.
- `florence-2-large` performs the same caption-driven extraction with a larger model.
- `threshold` applies to CLIP-style scoring and is clamped to the inclusive range `0.0..1.0`.
- Florence backends ignore the `threshold` parameter; all extracted keywords are returned.
- `max_tags` is clamped to the inclusive range `1..200`.

## XMP behavior

- XMP sidecars are written alongside the image by default unless `--output-dir` is provided.
- Existing XMP tags are merged by default.
- `--overwrite` replaces existing ImgTagPlus tags instead of merging.
- Malformed existing XMP is treated as unreadable input and ignored with a warning rather than crashing the run.
- XML-special characters in tags must be escaped correctly.

## Error handling

- Headless CLI returns a non-zero exit code when scanning or model loading fails.
- Per-image processing failures can continue or abort depending on CLI flags and interactive choices.
- The web server returns explicit error responses for invalid paths or sandbox violations.

## Operational behavior

- The server exposes `/health` for readiness checks.
- Only one tagging job may run at a time in the current server architecture.
- Log files are written to the process log directory and can be downloaded from the web UI.

## Non-goals

- Multi-user scheduling
- Remote/multi-host deployment
- Database-backed job orchestration
