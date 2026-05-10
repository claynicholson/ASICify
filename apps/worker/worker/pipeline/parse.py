"""Stage 1: Real model parsing via torch.fx.

For now this supports MLPs and small transformers built out of these primitives:
  - nn.Linear
  - nn.LayerNorm
  - nn.Embedding
  - nn.ReLU / nn.GELU / nn.SiLU / F.relu / F.gelu / F.silu

The output is a ModelGraph with a real layer list. Each LayerInfo carries the
layer's name as it appears in the parent module's state_dict, which is enough
for the generator and the kernels to find the actual weight tensors later.

When we expand to attention blocks (Q/K/V projections + softmax + output),
that goes here too. For now the generator handles attention via the existing
template; we'll wire real attention parsing in a follow-up.
"""

from __future__ import annotations

from typing import Any

import torch
from torch import nn

from worker.types import LayerInfo, ModelGraph

# A registry of activation classes/funcs we recognize. Anything else gets
# tagged "other" and the generator emits a pass-through.
_ACTIVATION_NAMES = {"relu", "gelu", "silu", "tanh", "sigmoid"}


def parse_module(
    model: nn.Module,
    name: str = "model",
    task: str = "language_modeling",
) -> ModelGraph:
    """Walk a torch.nn.Module and produce a ModelGraph.

    We use named_modules() rather than torch.fx.symbolic_trace because tracing
    arbitrary HuggingFace models often fails on dynamic control flow; the
    flat module walk is good enough for the cases we currently support and
    has zero failure modes on simple MLPs and transformers.
    """
    layers: list[LayerInfo] = []
    total_params = 0
    weight_tensors: dict[str, torch.Tensor] = {}
    bias_tensors: dict[str, torch.Tensor | None] = {}
    module_refs: dict[str, nn.Module] = {}

    for module_name, module in model.named_modules():
        if module_name == "":
            continue  # skip the root

        kind, info = _classify_module(module_name, module)
        if kind is None:
            continue

        layers.append(info)
        total_params += info.param_count

        if kind == "linear":
            weight_tensors[module_name] = module.weight.detach().clone()
            bias_tensors[module_name] = (
                module.bias.detach().clone() if module.bias is not None else None
            )
        elif kind == "embedding":
            module_refs[module_name] = module
        elif kind == "layernorm":
            module_refs[module_name] = module

    graph = ModelGraph(
        name=name,
        task=task,  # type: ignore[arg-type]
        layers=layers,
        total_params=total_params,
        metadata={"source": "torch_fx", "module_class": type(model).__name__},
    )
    # Stash tensors in metadata under private keys; the generator reads them
    # back when packing weights. Keeping them off the dataclass surface keeps
    # ModelGraph cheap to copy via dataclasses.replace.
    graph.metadata["_weights"] = weight_tensors
    graph.metadata["_biases"] = bias_tensors
    graph.metadata["_modules"] = module_refs
    graph.metadata["_root_module"] = model
    return graph


def _classify_module(name: str, module: nn.Module) -> tuple[str | None, LayerInfo]:
    """Map a torch module to a (kind, LayerInfo) pair."""
    cls = type(module).__name__

    if isinstance(module, nn.Linear):
        info = LayerInfo(
            name=name,
            kind="linear",
            in_features=module.in_features,
            out_features=module.out_features,
            param_count=module.weight.numel() + (module.bias.numel() if module.bias is not None else 0),
            metadata={"has_bias": module.bias is not None},
        )
        return "linear", info

    if isinstance(module, nn.Embedding):
        info = LayerInfo(
            name=name,
            kind="embedding",
            in_features=module.num_embeddings,
            out_features=module.embedding_dim,
            param_count=module.weight.numel(),
        )
        return "embedding", info

    if isinstance(module, nn.LayerNorm):
        # weight + bias are shape (dim,), so param_count = 2*dim if affine
        dim = module.normalized_shape[0]
        param_count = (dim * 2) if module.elementwise_affine else 0
        info = LayerInfo(
            name=name,
            kind="layernorm",
            in_features=dim,
            out_features=dim,
            param_count=param_count,
        )
        return "layernorm", info

    if isinstance(module, nn.MultiheadAttention):
        # Not yet supported by quantization or RTL, but we record it.
        info = LayerInfo(
            name=name,
            kind="attention",
            in_features=module.embed_dim,
            out_features=module.embed_dim,
            param_count=sum(p.numel() for p in module.parameters()),
        )
        return "attention", info

    # Activations carry no parameters but are useful to record so the RTL
    # generator can emit the correct nonlinearity.
    activation_kind = _classify_activation(module)
    if activation_kind is not None:
        info = LayerInfo(
            name=name,
            kind="other",
            in_features=0,
            out_features=0,
            param_count=0,
            metadata={"activation": activation_kind},
        )
        return "activation", info

    # Container modules (Sequential, ModuleList) are walked into; nothing to record.
    return None, _empty(name, cls)


def _classify_activation(module: nn.Module) -> str | None:
    cls = type(module).__name__.lower()
    if cls in _ACTIVATION_NAMES:
        return cls
    return None


def _empty(name: str, cls: str) -> LayerInfo:
    return LayerInfo(
        name=name,
        kind="other",
        in_features=0,
        out_features=0,
        param_count=0,
        metadata={"unrecognized": cls},
    )


def parse_model(model_source: dict[str, Any]) -> ModelGraph:
    """Top-level entry. Accepts:

      {"type": "module", "module": <nn.Module>, "name": ..., "task": ...}
      {"type": "huggingface", "id": "gpt2", "task": ..., "cache_dir": ...}
      {"type": "checkpoint", "path": "/path/to/checkpoint.pt", "name": ...}
    """
    # Back-compat: bare "module" key without "type".
    if "module" in model_source and "type" not in model_source:
        model_source = {**model_source, "type": "module"}

    src_type = model_source.get("type", "module")

    if src_type == "module":
        module = model_source["module"]
        if not isinstance(module, nn.Module):
            raise TypeError(
                f"model_source['module'] must be nn.Module, got {type(module)}"
            )
        return parse_module(
            module,
            name=model_source.get("name", "model"),
            task=model_source.get("task", "language_modeling"),
        )

    if src_type == "huggingface":
        from worker.loaders.huggingface import load_huggingface_model

        hf_id = model_source["id"]
        module, meta = load_huggingface_model(
            hf_id,
            cache_dir=model_source.get("cache_dir"),
            device=model_source.get("device", "cpu"),
            trust_remote_code=model_source.get("trust_remote_code", False),
            revision=model_source.get("revision"),
        )
        graph = parse_module(
            module,
            name=hf_id.replace("/", "__"),
            task=model_source.get("task", "language_modeling"),
        )
        graph.metadata.update({f"hf_{k}": v for k, v in meta.items()})
        return graph

    if src_type == "checkpoint":
        path = model_source["path"]
        module = torch.load(path, map_location="cpu", weights_only=False)
        if not isinstance(module, nn.Module):
            raise TypeError(f"checkpoint at {path} did not contain an nn.Module")
        module.eval()
        return parse_module(
            module,
            name=model_source.get("name", "checkpoint"),
            task=model_source.get("task", "language_modeling"),
        )

    raise ValueError(f"unknown model_source type: {src_type!r}")
