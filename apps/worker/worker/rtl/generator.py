"""RTL generation engine.

Layer-pipelined dataflow. One Verilog module per linear layer, with the
quantized int8 weights baked in as `localparam` constants. Synthesis tools
fold those constants into the multiplier inputs.

The generator threads the real quantized tensors from the orchestrator into
the templates. The Python reference and the cocotb testbench are emitted
alongside the RTL so verification and synthesis can run from the same
artifact.
"""

from __future__ import annotations

import zipfile
from collections.abc import Awaitable, Callable
from io import BytesIO
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

import json

import torch

from worker.kernels.attention import build_softmax_lut
from worker.kernels.layers import QuantizedEmbedding, QuantizedLayerNorm
from worker.kernels.pack import pack_embedding, pack_layer, pack_layernorm
from worker.pipeline.orchestrator import _cfg_from_dict
from worker.pipeline.parse import parse_model
from worker.types import CompressionConfig, ModelGraph

EmitFn = Callable[[dict[str, Any]], Awaitable[None]]

TEMPLATE_DIR = Path(__file__).parent / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def _multiplier_strategy(quantization: str) -> str:
    return {
        "binary": "xnor_popcount",
        "ternary": "sign_flip_mux",
        "int4": "csd_shift_add",
        "int8": "booth",
        "fp16": "fp16_lut",
    }[quantization]


def _safe_symbol(name: str) -> str:
    """Verilog identifier from a torch module path. `block.0.fc1` -> `block_0_fc1`."""
    out = []
    for ch in name:
        out.append(ch if ch.isalnum() else "_")
    s = "".join(out)
    if s and s[0].isdigit():
        s = "_" + s
    return s or "_anon"


def render_package(graph: ModelGraph, config: CompressionConfig) -> bytes:
    """Build the full RTL package as a zip in memory."""
    multiplier = _multiplier_strategy(config.quantization)
    quantized = graph.metadata.get("_quantized", {})

    # Build per-layer view objects.
    linear_views = []
    layernorm_views = []
    embedding_views = []

    for layer in graph.layers:
        symbol = _safe_symbol(layer.name)
        q = quantized.get(layer.name)

        if layer.kind == "linear":
            linear_views.append(
                {
                    "kind": "linear",
                    "name": layer.name,
                    "symbol": symbol,
                    "module_name": f"layer_{symbol}",
                    "in_features": layer.in_features,
                    "out_features": layer.out_features,
                    "has_bias": layer.metadata.get("has_bias", False),
                    "quantization": q.quantization if q is not None else config.quantization,
                    "weights_decl": pack_layer(symbol, q) if q is not None else None,
                    "quantized": q,
                }
            )
        elif layer.kind == "layernorm" and isinstance(q, QuantizedLayerNorm):
            layernorm_views.append(
                {
                    "kind": "layernorm",
                    "name": layer.name,
                    "symbol": symbol,
                    "module_name": f"layer_{symbol}",
                    "dim": q.dim,
                    "weights_decl": pack_layernorm(symbol, q),
                    "quantized": q,
                }
            )
        elif layer.kind == "embedding" and isinstance(q, QuantizedEmbedding):
            embedding_views.append(
                {
                    "kind": "embedding",
                    "name": layer.name,
                    "symbol": symbol,
                    "module_name": f"layer_{symbol}",
                    "vocab_size": q.vocab_size,
                    "embedding_dim": q.embedding_dim,
                    "weights_decl": pack_embedding(symbol, q),
                    "quantized": q,
                }
            )

    # Pipeline includes everything in declaration order so top.v can wire layers
    # together. For now top.v only chains linear layers; LN/Embedding modules
    # are emitted but the user wires them by hand at the top level.
    pipeline = list(linear_views)

    # Weights JSON for the bit-exact Python reference. Same numbers the
    # SystemVerilog `localparam` declarations carry, just JSON-serialized.
    weights_json = _build_weights_json(linear_views)

    first_in = pipeline[0]["in_features"] if pipeline else 0

    # Softmax LUT: a single global 256-entry table used by every attention block.
    softmax_lut = build_softmax_lut()
    softmax_cells = ", ".join(f"32'd{int(v)}" for v in softmax_lut.tolist())
    softmax_lut_decl = (
        f"localparam logic [31:0] SOFTMAX_LUT [0:{softmax_lut.numel() - 1}] = "
        f"'{{ {softmax_cells} }};"
    )

    ctx: dict[str, Any] = {
        "graph": graph,
        "config": config,
        "multiplier": multiplier,
        "linear_views": linear_views,
        "layernorm_views": layernorm_views,
        "embedding_views": embedding_views,
        "pipeline": pipeline,
        "weights_json": weights_json,
        "random_input_example": json.dumps([0] * first_in) if first_in else "[]",
        "softmax_lut_decl": softmax_lut_decl,
    }

    files: dict[str, str] = {}

    files["top.v"] = env.get_template("top.v.j2").render(**ctx)
    files["weights.vh"] = env.get_template("weights.vh.j2").render(**ctx)
    files["README.md"] = env.get_template("README.md.j2").render(**ctx)

    for view in linear_views:
        per_layer_ctx = dict(ctx)
        per_layer_ctx["multiplier"] = _multiplier_strategy(view["quantization"])
        files[f"modules/{view['module_name']}.v"] = env.get_template(
            "linear_layer.v.j2"
        ).render(layer_view=view, **per_layer_ctx)

    for view in layernorm_views:
        files[f"modules/{view['module_name']}.v"] = env.get_template(
            "layernorm.v.j2"
        ).render(layer_view=view, **ctx)

    for view in embedding_views:
        files[f"modules/{view['module_name']}.v"] = env.get_template(
            "embedding.v.j2"
        ).render(layer_view=view, **ctx)

    # Shared submodules (always emitted; layers may or may not use them).
    files["softmax.v"] = env.get_template("softmax.v.j2").render(**ctx)
    files["kv_cache.v"] = env.get_template("kv_cache.v.j2").render(**ctx)

    files["reference.py"] = env.get_template("reference.py.j2").render(**ctx)
    files["tb_top.py"] = env.get_template("tb_top.py.j2").render(**ctx)
    files["Makefile"] = env.get_template("Makefile.j2").render(**ctx)
    files["synthesis/yosys.tcl"] = env.get_template("yosys.tcl.j2").render(**ctx)
    files["synthesis/nextpnr.sh"] = env.get_template("nextpnr.sh.j2").render(**ctx)
    files["synthesis/vivado.tcl"] = env.get_template("vivado.tcl.j2").render(**ctx)

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, body in files.items():
            zf.writestr(name, body)
    return buf.getvalue()


def _build_weights_json(linear_views: list[dict[str, Any]]) -> str:
    """Render all packed weights as a single Python dict literal string.

    The reference template renders this verbatim where its WEIGHTS dict goes,
    so we produce something Python can `eval` (or rather, that the file can
    contain as a literal). The values are nested lists of ints, matching the
    Verilog representation cell-for-cell.
    """
    out: dict[str, list] = {}
    for view in linear_views:
        ql = view["quantized"]
        if ql is None:
            continue
        sym = view["symbol"]
        out[f"W_{sym}"] = ql.weight_int8.to(torch.int64).tolist()

        # Q0.31 scale, same conversion the pack module does.
        scale_q31 = (
            (ql.scale.to(torch.float64) * (1 << 31))
            .round()
            .clamp(0, (1 << 31) - 1)
            .to(torch.int64)
            .tolist()
        )
        out[f"SCALE_Q31_{sym}"] = scale_q31

        # Bias in pre-rescale int32 units.
        if ql.bias is None:
            out[f"BIAS_Q_{sym}"] = [0] * ql.out_features
        else:
            bias_int = (
                (ql.bias.to(torch.float64) / ql.scale.to(torch.float64).clamp_min(1e-30))
                .round()
                .clamp(-(2**31), 2**31 - 1)
                .to(torch.int64)
                .tolist()
            )
            out[f"BIAS_Q_{sym}"] = bias_int

    return json.dumps(out, indent=2)


def render_to_directory(graph: ModelGraph, config: CompressionConfig, out_dir: Path) -> Path:
    """Convenience: render the package and unzip it into `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pkg = render_package(graph, config)
    buf = BytesIO(pkg)
    with zipfile.ZipFile(buf, "r") as zf:
        zf.extractall(out_dir)
    return out_dir


async def run_rtl_job(job: dict[str, Any], emit: EmitFn) -> None:
    graph = parse_model(job["model_source"])
    config = _cfg_from_dict(job["compression_config"])

    await emit({"event": "stage_start", "stage": "rtl_generation"})
    package_bytes = render_package(graph, config)
    await emit(
        {
            "event": "stage_complete",
            "stage": "rtl_generation",
            "duration_ms": 0,
            "metrics": {
                "package_bytes": float(len(package_bytes)),
                "n_modules": float(
                    sum(1 for layer in graph.layers if layer.kind == "linear")
                ),
            },
        }
    )
