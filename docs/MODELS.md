# Models

This guide describes the currently supported model backends, how runtime selection works, and where caches live.

## Supported backends

ImgTagPlus currently exposes three model selections through `imgtagplus.profiler.AVAILABLE_MODELS`:

- `clip`
- `florence-2-base`
- `florence-2-large`

Internally, the Florence selections resolve to:

- `microsoft/Florence-2-base`
- `microsoft/Florence-2-large`

## CLIP vs. Florence

### CLIP

Implementation: `imgtagplus/tagger.py`

Characteristics:

- zero-shot classifier over the curated `imgtagplus.tags.TAGS` vocabulary
- uses ONNX Runtime sessions for the CLIP text and vision models
- returns scored `(tag, score)` pairs
- honors both `threshold` and `max_tags`
- precomputes and caches text embeddings for the tag list

Pipeline summary:

1. download or reuse the ONNX model assets and tokenizer
2. tokenize prompts of the form `"a photo of <tag>"`
3. compute normalized text embeddings
4. compute a normalized image embedding
5. rank by similarity and convert to softmax-like scores
6. keep the first result even when confidence is weak, then stop once later scores fall below the threshold

Practical implication:

- CLIP is deterministic against a fixed vocabulary and is the only backend whose threshold meaningfully filters results today

### Florence-2

Implementation: `imgtagplus/vlm.py`

Characteristics:

- caption-first vision-language model
- generates a detailed caption using the prompt `<DETAILED_CAPTION>`
- extracts ordered keywords from the generated caption
- returns `(keyword, 1.0)` pairs because the app does not derive real per-keyword confidence scores
- ignores the CLI/web threshold during tagging

Pipeline summary:

1. load the processor and model
2. generate a detailed caption for the image
3. post-process the generated text
4. strip punctuation, remove simple stopwords, and deduplicate keywords
5. cap the resulting keywords to `max_tags`

Practical implication:

- Florence can emit richer free-form concepts and OCR-adjacent language, but its output is heuristic keyword extraction rather than vocabulary scoring
- the threshold slider remains part of the shared UI payload, but Florence does not use it

## Model selection and resolution

Selection happens in `imgtagplus/app.py`.

Behavior:

- the app first looks up the supplied `model_id` in `AVAILABLE_MODELS`
- if that fails, it tries to match the raw Hugging Face ID stored in each model definition
- if nothing matches, it logs a warning and falls back to `clip`

This fallback protects older frontend state or manual callers that pass a full Florence model ID.

## Hardware and profile selection

Hardware detection lives in `imgtagplus/profiler.py`.

The profiler reports:

- total RAM
- available RAM
- coarse VRAM estimate
- accelerator type: `cuda`, `mps`, or `cpu`

### Accelerator detection

- `cuda` when `torch.cuda.is_available()` is true
- `mps` on Apple Silicon when running on Darwin `arm64`
- otherwise `cpu`

### Memory gating

The UI-facing recommendation logic uses:

- VRAM for `cuda` and `mps`
- available system RAM for `cpu`

Each model has a minimum memory threshold:

| Model | Minimum memory heuristic | Type |
| --- | --- | --- |
| `clip` | 1 GB | `tagger` |
| `florence-2-base` | 3 GB | `vlm` |
| `florence-2-large` | 6 GB | `vlm` |

These checks only drive `supported`/`warning` fields for the UI. They are recommendations, not hard enforcement.

## Manual accelerator overrides

The web UI can optionally post an `accelerator` override. The CLI can also pass one through the shared arguments namespace.

### CLIP runtime providers

`imgtagplus/tagger.py` selects ONNX Runtime providers as follows:

- default: `CPUExecutionProvider`
- `cuda`: `["CUDAExecutionProvider", "CPUExecutionProvider"]`
- `mps`: `["CoreMLExecutionProvider", "CPUExecutionProvider"]`

### Florence runtime device and dtype

`imgtagplus/vlm.py` selects:

- `cuda` -> device `cuda`, dtype `float16`
- `mps` -> device `mps`, dtype `float32`
- otherwise `cpu`, dtype `float32`

If no explicit accelerator is provided, Florence auto-detects in that order.

## CPU vs. GPU behavior for Florence

Florence has distinct runtime paths:

### CPU path

When the chosen device is `cpu`, the loader first attempts an ONNX-optimized path via Optimum:

- processor from `onnx-community/<model-name>-ft`
- `ORTModelForConditionalGeneration`

If Optimum is unavailable, the code falls back to native PyTorch CPU inference with:

- `attn_implementation="eager"`
- `trust_remote_code=True`
- the model-specific pinned Florence revision when the selected variant has a reviewed pin

### GPU path

For `cuda` and `mps`, Florence loads the native PyTorch model and processor with:

- `attn_implementation="eager"`
- `trust_remote_code=True`
- the model-specific pinned Florence revision when the selected variant has a reviewed pin
- `device_map=None`

The model is then moved onto the selected device.

## Cache and model directories

### Default cache location

Both model backends default to:

```text
~/.cache/imgtagplus
```

unless an explicit `--model-dir` is provided.

### CLIP cache contents

Under the model directory, CLIP stores:

- downloaded ONNX model files and tokenizer via `huggingface_hub`
- tag embedding cache files named like:

```text
clip_tag_embeddings_<digest>.npy
```

The digest is derived from the exact ordered tag vocabulary, so cache reuse depends on the current tag list.

### Florence cache contents

Florence also uses the model directory for Hugging Face downloads and sets:

```text
HF_HOME=<model_dir>
```

This keeps model and processor downloads under the same writable root.

If the default home-cache location is not writable, `imgtagplus/vlm.py` falls back to:

```text
<repo>/.cache/imgtagplus
```

The Florence loader explicitly creates and tests this directory before using it.

## Trust and pinning for Florence

Florence currently requires `trust_remote_code=True`.

That increases the importance of pinning and review, so the code includes two safeguards:

1. `FLORENCE_MODEL_REVISIONS` pins reviewed commit hashes per supported Florence variant.
2. The source comments state that the compatibility patches should be re-validated before changing that pin or upgrading the surrounding stack.

Current pins:

```text
microsoft/Florence-2-base  -> 5ca5edf5bd017b9919c05d08aebef5e4c7ac3bac
microsoft/Florence-2-large -> 21a599d414c4d928c9032694c424fb94458e3594
```

## Compatibility patches

`imgtagplus/vlm.py` applies a narrow set of runtime patches for the current Florence/transformers combination:

- adds `additional_special_tokens` when missing on `TokenizersBackend`
- returns `None` for missing `forced_bos_token_id`
- returns `False` for `_supports_sdpa` and `_supports_flash_attn_2` when Florence remote code touches them too early

These are not general-purpose compatibility helpers. They are part of the current pinned Florence integration and should be treated as version-coupled behavior.

## What the profiler does not guarantee

The profiler is intentionally lightweight. It does **not**:

- benchmark throughput
- guarantee that a "supported" model will fit every workload comfortably
- account for other processes competing for RAM/VRAM
- prove that a specific accelerator provider is installed correctly

Use the profiler output as guidance for defaults and UX warnings, not as a capacity promise.
