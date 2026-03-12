"""Hardware profiling and model recommendation helpers.

These helpers stay intentionally lightweight so both the CLI and web UI can
quickly decide which tagging backends are reasonable on the current machine.
"""

import logging
import platform

import psutil
import torch

log = logging.getLogger(__name__)

# Model definitions and their estimated minimum memory requirements (in GB)
AVAILABLE_MODELS = {
    "clip": {
        "id": "clip",
        "name": "CLIP (Zero-Shot)",
        "description": "Fast tagger using predefined categories. Uses ~1GB RAM.",
        "min_ram_gb": 1.0,
        "type": "tagger",
        "recommended": True
    },
    "florence-2-base": {
        "id": "microsoft/Florence-2-base",
        "name": "Florence-2 Base",
        "description": "Rich OCR and object captioning. Uses ~2-3GB VRAM/RAM.",
        "min_ram_gb": 3.0,
        "type": "vlm",
        "recommended": True
    },
    "florence-2-large": {
        "id": "microsoft/Florence-2-large",
        "name": "Florence-2 Large",
        "description": "High-quality rich captioning. Uses ~4-6GB VRAM/RAM.",
        "min_ram_gb": 6.0,
        "type": "vlm",
        "recommended": False
    }
}

def get_system_specs() -> dict:
    """Return RAM, accelerator, and coarse VRAM data used for model gating."""

    vm = psutil.virtual_memory()
    total_ram_gb = vm.total / (1024 ** 3)
    available_ram_gb = vm.available / (1024 ** 3)

    vram_gb = 0.0
    device_type = "cpu"
    if torch.cuda.is_available():
        device_type = "cuda"
        try:
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        except Exception:
            pass
    elif platform.system() == "Darwin" and platform.machine() == "arm64":
        device_type = "mps"
        # Apple Silicon uses unified memory, so VRAM headroom tracks total RAM.
        vram_gb = total_ram_gb

    return {
        "os": platform.system(),
        "arch": platform.machine(),
        "total_ram_gb": round(total_ram_gb, 2),
        "available_ram_gb": round(available_ram_gb, 2),
        "vram_gb": round(vram_gb, 2),
        "accelerator": device_type
    }

def get_model_recommendations() -> list[dict]:
    """Annotate each known model with support and memory warnings for this host."""
    specs = get_system_specs()
    effective_memory = specs["vram_gb"] if specs["accelerator"] in ["cuda", "mps"] else specs["available_ram_gb"]

    results = []
    for model_id, info in AVAILABLE_MODELS.items():
        supported = effective_memory >= info["min_ram_gb"]

        warning = ""
        if not supported:
            if specs["accelerator"] == "cpu":
                warning = f"Requires at least {info['min_ram_gb']}GB free RAM."
            else:
                warning = f"Requires at least {info['min_ram_gb']}GB VRAM."

        results.append({
            **info,
            "key": model_id,
            "supported": supported,
            "warning": warning,
        })

    return results

def get_profiler_summary() -> dict:
    """Combine hardware data, model support, and a coarse UI-facing rating."""
    specs = get_system_specs()
    models = get_model_recommendations()

    # The rating is intentionally simple; it is only used for UX copy.
    if specs["accelerator"] in ["cuda", "mps"] and specs["vram_gb"] > 8:
        performance_rating = "Excellent"
    elif specs["total_ram_gb"] >= 16:
        performance_rating = "Good"
    else:
        performance_rating = "Poor"
    
    return {
        "hardware": specs,
        "models": list(models),
        "performance_rating": performance_rating,
    }
