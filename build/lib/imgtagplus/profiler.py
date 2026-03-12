import platform
import psutil
import torch
import logging

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
    """Profiles the system to determine RAM and VRAM availability."""
    
    # 1. Check total system RAM
    vm = psutil.virtual_memory()
    total_ram_gb = vm.total / (1024 ** 3)
    available_ram_gb = vm.available / (1024 ** 3)
    
    # 2. Check for CUDA (Nvidia GPUs)
    vram_gb = 0.0
    device_type = "cpu"
    if torch.cuda.is_available():
        device_type = "cuda"
        # Rough estimate: getting total VRAM of the first CUDA device
        try:
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        except Exception:
            pass
            
    # 3. Check for Apple Silicon (MPS / Metal)
    elif platform.system() == "Darwin" and platform.machine() == "arm64":
        device_type = "mps"
        # Unified memory means VRAM = RAM
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
    """Returns a list of models annotated with whether they are supported on this hardware."""
    specs = get_system_specs()
    # If the system has an accelerator, we prioritize VRAM limit. 
    # If CPU only, we fall back to checking available RAM.
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
            "warning": warning
        })
        
    return results

def get_profiler_summary() -> dict:
    """Returns the full hardware profile and model recommendations."""
    specs = get_system_specs()
    models = get_model_recommendations()
    
    # Excellent: Native Apple Silicon MPS or Dedicated Nvidia VRAM > 8GB
    if specs["accelerator"] in ["cuda", "mps"] and specs["vram_gb"] > 8:
        performance_rating = "Excellent"
    elif specs["total_ram_gb"] >= 16:
        performance_rating = "Good"
    else:
        performance_rating = "Poor"
    
    return {
        "hardware": specs,
        "models": list(models),
        "performance_rating": performance_rating
    }
