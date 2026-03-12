import logging
from pathlib import Path
import os
import gc

from PIL import Image

log = logging.getLogger(__name__)

class FlorenceTagger:
    """Zero-shot image tagger and captioner backed by Microsoft Florence-2."""
    
    def __init__(self, model_id: str = "microsoft/Florence-2-base", model_dir: Path | None = None) -> None:
        self._model_id = model_id
        if model_dir is None:
            # Fallback to local project directory if home cache is not writable
            try:
                model_dir = Path.home() / ".cache" / "imgtagplus"
                model_dir.mkdir(parents=True, exist_ok=True)
                # Test write access
                test_file = model_dir / ".write_test"
                test_file.touch()
                test_file.unlink()
            except (PermissionError, OSError):
                log.warning(f"Could not use {model_dir} for cache. Falling back to local .cache directory.")
                model_dir = Path(__file__).parent.parent / ".cache" / "imgtagplus"
                model_dir.mkdir(parents=True, exist_ok=True)
                
        self._model_dir = model_dir
        
        # Force huggingface_hub to use our local cache directory for everything
        os.environ["HF_HOME"] = str(self._model_dir)

        import torch
        from transformers import AutoProcessor, AutoModelForCausalLM
        
        # ── Compatibility shim for transformers ≥5.3 ────────────────────────-
        # Florence-2's remote code (processing_florence2.py / configuration_florence2.py / modeling_florence2.py) 
        # makes assumptions about attributes or initialization order that the 
        # new transformers v5.3.0 classes no longer satisfy.
        
        # 1. Patch TokenizersBackend for processor initialization
        try:
            from transformers.tokenization_utils_tokenizers import TokenizersBackend
            if not hasattr(TokenizersBackend, "additional_special_tokens"):
                TokenizersBackend.additional_special_tokens = property(
                    lambda self: getattr(self, "_additional_special_tokens", [])
                )
                log.debug("Patched TokenizersBackend.additional_special_tokens")
        except ImportError:
            pass

        # 2. Patch PretrainedConfig for model config initialization
        from transformers.configuration_utils import PretrainedConfig
        _orig_config_getattribute = PretrainedConfig.__getattribute__
        def _patched_config_getattribute(self, item):
            try:
                return _orig_config_getattribute(self, item)
            except AttributeError:
                if item == "forced_bos_token_id":
                    return None
                raise
        PretrainedConfig.__getattribute__ = _patched_config_getattribute

        # 3. Patch PreTrainedModel for model instance initialization
        # Florence-2's @property '_supports_sdpa' / '_supports_flash_attn_2' 
        # fail during __init__ because they access self.language_model before it exists.
        from transformers.modeling_utils import PreTrainedModel
        _orig_model_getattribute = PreTrainedModel.__getattribute__
        def _patched_model_getattribute(self, item):
            try:
                return _orig_model_getattribute(self, item)
            except AttributeError:
                # If these specific properties fail, it's usually because language_model is missing
                if item in ("_supports_sdpa", "_supports_flash_attn_2"):
                    return False
                raise
        PreTrainedModel.__getattribute__ = _patched_model_getattribute
        log.debug("Applied full Florence-2 compatibility triple-patch (Tokenizer/Config/Model).")

        # Decide on the device and precision
        self.device = "cpu"
        self.dtype = torch.float32
        self.is_onnx = False
        
        if torch.cuda.is_available():
            self.device = "cuda"
            self.dtype = torch.float16
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = "mps"
            self.dtype = torch.float32
            
        if self.device == "cpu":
            log.info(f"CPU environment detected. Attempting to load ONNX optimized {self._model_id} via Optimum...")
            try:
                from optimum.onnxruntime import ORTModelForConditionalGeneration
                onnx_model_id = f"onnx-community/{self._model_id.split('/')[-1]}-ft"
                self.processor = AutoProcessor.from_pretrained(onnx_model_id, trust_remote_code=True, cache_dir=str(self._model_dir))
                self.model = ORTModelForConditionalGeneration.from_pretrained(onnx_model_id, cache_dir=str(self._model_dir))
                self.is_onnx = True
                log.info("Successfully loaded ONNX CPU pathway.")
            except ImportError:
                log.warning("Optimum ONNX not available. Falling back to native PyTorch CPU inference with SDPA...")
                self.processor = AutoProcessor.from_pretrained(self._model_id, trust_remote_code=True, cache_dir=str(self._model_dir))
                self.model = AutoModelForCausalLM.from_pretrained(
                    self._model_id, 
                    torch_dtype=self.dtype, 
                    attn_implementation="eager",
                    trust_remote_code=True,
                    low_cpu_mem_usage=False,
                    device_map=None,
                    cache_dir=str(self._model_dir)
                )
        else:
            log.info(f"GPU environment detected. Loading native {self._model_id} on {self.device} with eager attention...")
            self.processor = AutoProcessor.from_pretrained(self._model_id, trust_remote_code=True, cache_dir=str(self._model_dir))
            self.model = AutoModelForCausalLM.from_pretrained(
                self._model_id, 
                torch_dtype=self.dtype,
                attn_implementation="eager",
                trust_remote_code=True,
                low_cpu_mem_usage=False,
                device_map=None,
                cache_dir=str(self._model_dir)
            ).to(self.device)
            
        if not self.is_onnx:
            self.model.eval()

    def unload(self) -> None:
        """Frees up memory when the model is no longer needed."""
        self.model = None
        self.processor = None
        
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            # torch.mps.empty_cache() is available in newer PyTorch versions.
            try:
                torch.mps.empty_cache()
            except AttributeError:
                pass
                
        gc.collect()
        log.info(f"Unloaded {self._model_id}")

    def tag_image(self, image_path: Path, max_tags: int = 15) -> list[tuple[str, float]]:
        """Tags an image using Florence-2's detailed captioning task."""
        image = self._load_image(image_path)
        
        prompt = "<DETAILED_CAPTION>"
        inputs = self.processor(text=prompt, images=image, return_tensors="pt")
        inputs = {k: v.to(self.device, self.dtype if k == "pixel_values" else None) for k, v in inputs.items()}

        log.debug(f"Running inference on {image_path.name}")
        
        import torch
        with torch.no_grad():
            generated_ids = self.model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=1024,
                early_stopping=False,
                do_sample=False,
                num_beams=3,
                use_cache=False,
            )

        generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        # Clean up output
        parsed = self.processor.post_process_generation(
            generated_text,
            task="<DETAILED_CAPTION>",
            image_size=(image.width, image.height)
        )
        
        caption = parsed["<DETAILED_CAPTION>"].strip()
        
        log.debug(f"Generated caption: {caption}")
        
        # We need to extract tags from the caption instead of just returning the caption directly, 
        # so it plays nicely with the rest of the application. We use keywords.
        keywords = self._extract_keywords_from_caption(caption)
        
        # Florence-2 doesn't give discrete confidence scores out-of-the-box like CLIP in this mode, 
        # so we assign a 1.0 pseudo-confidence for tags it clearly identified.
        results = [(kw, 1.0) for kw in keywords[:max_tags]]
        
        # Special behaviour: If it's pure VLM, we might want to also include the raw caption as an XMP description, 
        # but for now we format it as a single mega-tag or handle it in `metadata.py`. 
        if results is None or len(results) == 0:
            if caption:
               results = [(caption[:100], 1.0)] 

        return results

    def _extract_keywords_from_caption(self, caption: str) -> list[str]:
        """A simple heuristic to split a descriptive sentence into descriptive tags."""
        import string
        
        # Remove punctuation
        translator = str.maketrans('', '', string.punctuation)
        clean = caption.translate(translator).lower()
        
        words = clean.split()
        
        # Basic common non-descriptive words to remove
        stopwords = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", 
            "with", "of", "is", "are", "was", "were", "this", "that", "it", "there", 
            "their", "they", "its", "photo", "image", "picture", "shows", "showing"
        }
        
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        # Identify noun pairs simply by adjacency? E.g. "red car"
        # Since Florence-2 might say "a red car parked on a street", this might yield:
        # ["red", "car", "parked", "street"]. That's decent for an auto-tagger.
        
        # We will preserve the order but deduplicate
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
                
        return unique_keywords

    @staticmethod
    def _load_image(path: Path) -> Image.Image:
        """Load an image."""
        img = Image.open(path).convert("RGB")
        return img
