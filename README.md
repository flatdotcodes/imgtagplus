# ImgTagPlus

**Bulk AI image tagger** — automatically tags images using CLIP (ViT-B/32) via ONNX Runtime and saves tags as XMP sidecar files, compatible with all major digital asset management (DAM) systems.

## Features

- **AI-powered tagging** — Uses OpenAI's CLIP (fast, zero-shot) or Microsoft Florence-2 (rich VLM captioning and OCR)
- **Interactive Web UI** — Beautiful, local real-time monitoring of tagging jobs through a browser interface.
- **XMP sidecar files** — Non-destructive; tags saved in `.xmp` files recognised by Lightroom, Bridge, Darktable, digiKam, XnView, etc.
- **Bulk processing** — Tag a single image or an entire directory tree
- **Cross-platform** — Works on Linux, macOS, and Windows
- **Interactive CLI Manager** — Manage the local web server or execute headless tasks.
- **Detailed logging** — Full debug log written to file

## Quick Start

### Install

```bash
# Clone and install
cd imgtagplus
pip install -r requirements.txt

# Or install as a package
pip install .
```

```bash
# Display the interactive CLI manager
imgtagplus

# From the interactive menu, you can start the Web UI server
# and manage background tagging tasks visually.
```

### Headless CLI Tagging

```bash
# Tag a directory using the classic CLIP model
imgtagplus -i ./photos/ -r

# Or explicitly start the Web UI Server in the background
imgtagplus --start-server

# To stop the server
imgtagplus --stop-server
```

### Run as a Python module

```bash
python -m imgtagplus -i photo.jpg
```

## CLI Options

| Option | Short | Default | Description |
|---|---|---|---|
| `--start-server` |  |  | Starts the background Web UI Server |
| `--stop-server` |  |  | Stops the background Web UI Server |
| `--input` | `-i` | *(required for headless)* | Path to image or directory |
| `--recursive` | `-r` | `false` | Scan subdirectories |
| `--model-id` | | `clip` | Which AI to use (`clip` or `florence-2-base`) |
| `--threshold` | `-t` | `0.25` | Min confidence to keep a tag (CLIP only) |
| `--max-tags` | `-n` | `20` | Max tags per image |
| `--silent` | `-s` | `false` | Suppress interactive prompts |
| `--continue-on-error` | `-c` | `false` | Skip errors, keep going |
| `--output-dir` | `-o` | *(alongside image)* | Custom output directory for `.xmp` files |
| `--log-file` | `-l` | `imgtagplus_TIMESTAMP.log` | Custom log file path |
| `--model-dir` | | `~/.cache/imgtagplus` | Cache directory for model files |

## Output

After a run, you'll see a summary like:

```
============================================================
  ImgTagPlus — Run Summary
============================================================

Images processed : 42 / 42
Errors           : 0

Elapsed time  : 2m 15.3s
Avg CPU usage : 78.2%
Peak CPU usage: 95.1%
Avg RAM usage : 412.3 MB
Peak RAM usage: 523.7 MB

XMP output directories:
  /path/to/photos

Log file: /path/to/imgtagplus_20260210_190000.log
============================================================
```

## How It Works

1. **Scans** for images by extension (`.jpg`, `.jpeg`, `.png`, `.webp`, `.tiff`, `.bmp`, `.gif`)
2. **Downloads** the CLIP ViT-B/32 ONNX model on first run (~350 MB, cached)
3. **Pre-computes** text embeddings for ~600 curated tags
4. For each image:
   - Preprocesses (resize, centre crop, normalise)
   - Computes image embedding via ONNX Runtime
   - Calculates cosine similarity against all tag embeddings
   - Selects tags above the confidence threshold
5. **Writes** tags to XMP sidecar files (`dc:subject` keywords)

## Supported Image Formats

`.jpg` `.jpeg` `.png` `.webp` `.tiff` `.tif` `.bmp` `.gif`

## Dependencies

- Python 3.9+
- `fastapi` & `uvicorn` — Web Server framework
- `torch` & `transformers` — VLM inference via Florence-2
- `onnxruntime` — CLIP model inference via ONNX
- `Pillow` — Image loading and processing
- `psutil` — System resource profiling

## License

MIT
