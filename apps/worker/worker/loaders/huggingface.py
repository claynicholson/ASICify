"""HuggingFace model loader.

Requires the `hosted` extra:
    cd apps/worker && uv sync --extra hosted

The loader is intentionally narrow: it grabs a model by id, puts it in eval
mode, and returns the nn.Module. ASICify's parser does the rest.

We don't import transformers at module-load time so that worker installs
without the `hosted` extra still work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch


def is_available() -> bool:
    """True if the `transformers` package is importable."""
    try:
        import transformers  # noqa: F401

        return True
    except Exception:
        return False


def load_huggingface_model(
    model_id: str,
    cache_dir: str | Path | None = None,
    device: str = "cpu",
    torch_dtype: torch.dtype | None = torch.float32,
    trust_remote_code: bool = False,
    revision: str | None = None,
) -> tuple[torch.nn.Module, dict[str, Any]]:
    """Download (or read from cache) a HuggingFace checkpoint.

    Args:
        model_id: HF id like "gpt2", "distilbert-base-uncased",
                  "TinyLlama/TinyLlama-1.1B-Chat-v1.0".
        cache_dir: Where to store model files. Defaults to HF's default.
        device: "cpu" by default. We compile on CPU; quantization doesn't need a GPU.
        torch_dtype: Defaults to fp32. The compiler quantizes to int anyway.
        trust_remote_code: Pass-through to AutoModel.from_pretrained.
        revision: Optional pin to a commit hash or tag.

    Returns:
        (model, metadata) where metadata contains config snapshot, hf_id, etc.
    """
    if not is_available():
        raise RuntimeError(
            "transformers is not installed. Run `uv sync --extra hosted` from "
            "apps/worker to enable the HuggingFace loader."
        )

    # Lazy import so worker installs without the extra still load.
    from transformers import AutoConfig, AutoModel  # type: ignore

    cache_kwargs: dict[str, Any] = {}
    if cache_dir is not None:
        cache_kwargs["cache_dir"] = str(cache_dir)
    if revision is not None:
        cache_kwargs["revision"] = revision

    config = AutoConfig.from_pretrained(
        model_id, trust_remote_code=trust_remote_code, **cache_kwargs
    )
    model = AutoModel.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
        trust_remote_code=trust_remote_code,
        **cache_kwargs,
    )
    model.to(device)
    model.eval()

    metadata = {
        "hf_id": model_id,
        "model_type": getattr(config, "model_type", "unknown"),
        "config_class": type(config).__name__,
        "n_params": sum(p.numel() for p in model.parameters()),
    }

    if revision is not None:
        metadata["revision"] = revision

    return model, metadata
