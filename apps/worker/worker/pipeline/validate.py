"""Stage 5: Quality validation.

Real activation-MSE validation against the original float model when the
live module is available. Falls back to an analytical penalty otherwise.

How it works:
  1. Build a "reconstructed" copy of the original model with dequantized
     weights replacing each Linear's float weights.
  2. Drive both models with random Gaussian inputs.
  3. Compare activation tensors layer-by-layer (relative MSE).
  4. Compare end-to-end outputs (cosine similarity).

For language models with token-id inputs, you need a real text dataset to
get a meaningful quality estimate; that path is exposed via
validate_with_data() but isn't called from the default orchestrator.
"""

from __future__ import annotations

import copy
import math

import torch
from torch import nn

from worker.kernels.quantize import QuantizedLinear
from worker.types import CompressionConfig, ModelGraph


def validate_quality(
    graph: ModelGraph,
    config: CompressionConfig,
    baseline: float,
) -> dict[str, float]:
    """Top-level entry; combines real-MSE if possible with analytical fallback."""
    metrics = _real_activation_mse_if_possible(graph)

    # If we couldn't compute real MSE (token-only model, no live module),
    # fall back to the analytical penalty.
    if "activation_mse" not in metrics:
        compressed = _analytical_penalty(baseline, config)
        return {
            "baseline": baseline,
            "compressed": compressed,
            "delta_pct": ((compressed / max(baseline, 1e-9)) - 1.0) * 100.0,
        }

    # Convert MSE to a relative quality factor (1.0 = perfect, >1 = degraded).
    quality_factor = 1.0 + math.tanh(metrics["activation_mse"] * 4.0) * 0.5
    metrics["baseline"] = baseline
    metrics["compressed"] = baseline * quality_factor
    metrics["delta_pct"] = (quality_factor - 1.0) * 100.0
    return metrics


def validate_with_data(
    graph: ModelGraph,
    inputs: torch.Tensor,
    targets: torch.Tensor | None = None,
    metric: str = "activation_mse",
) -> dict[str, float]:
    """User-supplied dataset entry point.

    Args:
        graph: post-quantization graph (with `_root_module` and `_quantized` set).
        inputs: tensor matching what the model expects (token ids, images, etc.).
        targets: optional reference outputs for top-1 / regression metrics.
        metric: "activation_mse" (default) | "perplexity" | "top1".
    """
    original = graph.metadata.get("_root_module")
    quant = graph.metadata.get("_quantized", {})
    if original is None or not quant:
        return {"error": "graph is missing _root_module or _quantized"}

    reconstructed = _swap_linears_with_dequantized(original, quant)

    if metric == "activation_mse":
        return _activation_mse(original, reconstructed, inputs, list(quant.keys()))

    if metric == "perplexity":
        with torch.no_grad():
            o = original(inputs)
            r = reconstructed(inputs)
            # CrossEntropy uses (N, C, ...) and target ids
            if targets is None:
                return {"error": "perplexity needs targets"}
            ce_o = torch.nn.functional.cross_entropy(o, targets).item()
            ce_r = torch.nn.functional.cross_entropy(r, targets).item()
            return {
                "baseline_perplexity": float(math.exp(ce_o)),
                "compressed_perplexity": float(math.exp(ce_r)),
                "delta_pct": (math.exp(ce_r) / math.exp(ce_o) - 1.0) * 100.0,
            }

    if metric == "top1" and targets is not None:
        with torch.no_grad():
            o = original(inputs).argmax(dim=-1)
            r = reconstructed(inputs).argmax(dim=-1)
            return {
                "baseline_top1": float((o == targets).float().mean()),
                "compressed_top1": float((r == targets).float().mean()),
            }

    return {"error": f"unknown metric: {metric}"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _real_activation_mse_if_possible(graph: ModelGraph) -> dict[str, float]:
    original = graph.metadata.get("_root_module")
    quant: dict[str, object] = graph.metadata.get("_quantized", {})
    if original is None or not quant:
        return {}

    in_dim = _infer_input_dim(graph)
    if in_dim is None:
        return {}

    return _activation_mse_random(original, quant, in_dim)


def _activation_mse_random(
    original: nn.Module,
    quant: dict[str, object],
    in_dim: int,
    n_samples: int = 32,
) -> dict[str, float]:
    torch.manual_seed(0)
    x = torch.randn(n_samples, in_dim)
    reconstructed = _swap_linears_with_dequantized(original, quant)
    return _activation_mse(original, reconstructed, x, list(quant.keys()))


def _activation_mse(
    original: nn.Module,
    reconstructed: nn.Module,
    x: torch.Tensor,
    layer_paths: list[str],
) -> dict[str, float]:
    orig_acts = _capture(original, x, layer_paths)
    recon_acts = _capture(reconstructed, x, layer_paths)

    per_layer: list[float] = []
    for name in layer_paths:
        if name not in orig_acts or name not in recon_acts:
            continue
        a = orig_acts[name]
        b = recon_acts[name]
        if a.shape != b.shape:
            continue
        mse = ((a - b) ** 2).mean().item()
        denom = max(1e-9, (a ** 2).mean().item())
        per_layer.append(mse / denom)

    if not per_layer:
        return {}

    with torch.no_grad():
        y_orig = original(x).detach().reshape(x.shape[0], -1)
        y_recon = reconstructed(x).detach().reshape(x.shape[0], -1)
    cos = torch.nn.functional.cosine_similarity(y_orig, y_recon, dim=-1).mean().item()

    return {
        "activation_mse": float(sum(per_layer) / len(per_layer)),
        "max_layer_mse": float(max(per_layer)),
        "cosine_similarity": float(cos),
    }


def _capture(
    model: nn.Module, x: torch.Tensor, layer_paths: list[str]
) -> dict[str, torch.Tensor]:
    captured: dict[str, torch.Tensor] = {}
    handles = []
    name_to_module = dict(model.named_modules())

    def _make(name: str):
        def hook(_m, _i, out):
            captured[name] = out.detach().clone() if isinstance(out, torch.Tensor) else None

        return hook

    for path in layer_paths:
        if path in name_to_module:
            handles.append(name_to_module[path].register_forward_hook(_make(path)))

    with torch.no_grad():
        model(x)
    for h in handles:
        h.remove()
    return captured


def _swap_linears_with_dequantized(
    model: nn.Module, quant: dict[str, object]
) -> nn.Module:
    clone = copy.deepcopy(model)
    name_to_module = dict(clone.named_modules())
    for path, q in quant.items():
        if not isinstance(q, QuantizedLinear):
            continue
        if path not in name_to_module:
            continue
        target = name_to_module[path]
        if not isinstance(target, nn.Linear):
            continue
        with torch.no_grad():
            target.weight.copy_(q.dequantize())
            if q.bias is not None and target.bias is not None:
                target.bias.copy_(q.bias)
    clone.eval()
    return clone


def _infer_input_dim(graph: ModelGraph) -> int | None:
    for layer in graph.layers:
        if layer.kind == "linear":
            return layer.in_features
        if layer.kind == "embedding":
            return None
    return None


def _analytical_penalty(baseline: float, config: CompressionConfig) -> float:
    PENALTY = {
        "fp16": 1.0,
        "int8": 1.005,
        "int4": 1.04,
        "ternary": 1.18,
        "binary": 1.45,
    }
    return baseline * PENALTY.get(config.quantization, 1.0)
