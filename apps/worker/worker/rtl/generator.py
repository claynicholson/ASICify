"""Verilog generation engine.

Architecture: layer-pipelined dataflow.
  - Each layer gets its own physical region
  - Activations stream forward through layers
  - Pipeline registers between layers for timing closure
  - KV cache lives in BRAM-mapped buffers

Generates:
  output/
  ├── README.md
  ├── top.v
  ├── modules/<layer>.v
  ├── weights/weights.vh
  ├── tb_top.py            (cocotb)
  ├── reference.py         (bit-exact Python)
  ├── Makefile             (sim, synth-yosys, synth-vivado)
  └── synthesis/
      ├── yosys.tcl
      ├── nextpnr.sh
      └── vivado.tcl
"""

from __future__ import annotations

import zipfile
from collections.abc import Awaitable, Callable
from io import BytesIO
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

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
    """Return the multiplier kind for a given precision."""
    return {
        "binary": "xnor_popcount",
        "ternary": "sign_flip_mux",
        "int4": "csd_shift_add",
        "int8": "booth",
        "fp16": "fp16_lut",
    }[quantization]


def render_package(graph: ModelGraph, config: CompressionConfig) -> bytes:
    """Build the full RTL package as a zip in memory."""
    multiplier = _multiplier_strategy(config.quantization)
    ctx = {
        "graph": graph,
        "config": config,
        "multiplier": multiplier,
        "linear_layers": [
            l for l in graph.layers if l.kind in ("linear", "ffn", "attention")
        ],
    }

    files: dict[str, str] = {}

    # Top-level
    files["top.v"] = env.get_template("top.v.j2").render(**ctx)
    files["README.md"] = env.get_template("README.md.j2").render(**ctx)
    files["weights/weights.vh"] = env.get_template("weights.vh.j2").render(**ctx)

    # Per-layer
    for layer in graph.layers:
        if layer.kind == "linear" or layer.kind == "ffn":
            content = env.get_template("linear_layer.v.j2").render(layer=layer, **ctx)
        elif layer.kind == "attention":
            content = env.get_template("attention.v.j2").render(layer=layer, **ctx)
        elif layer.kind == "layernorm":
            content = env.get_template("layernorm.v.j2").render(layer=layer, **ctx)
        elif layer.kind == "embedding":
            content = env.get_template("embedding.v.j2").render(layer=layer, **ctx)
        else:
            continue
        files[f"modules/{layer.name}.v"] = content

    files["kv_cache.v"] = env.get_template("kv_cache.v.j2").render(**ctx)

    # Verification
    files["tb_top.py"] = env.get_template("tb_top.py.j2").render(**ctx)
    files["reference.py"] = env.get_template("reference.py.j2").render(**ctx)
    files["Makefile"] = env.get_template("Makefile.j2").render(**ctx)

    # Synthesis scripts
    files["synthesis/yosys.tcl"] = env.get_template("yosys.tcl.j2").render(**ctx)
    files["synthesis/nextpnr.sh"] = env.get_template("nextpnr.sh.j2").render(**ctx)
    files["synthesis/vivado.tcl"] = env.get_template("vivado.tcl.j2").render(**ctx)

    # Pack
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, body in files.items():
            zf.writestr(name, body)
    return buf.getvalue()


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
                "n_modules": float(len(graph.layers)),
            },
        }
    )

    # In production: upload package_bytes to R2 with a key like
    #   projects/<project_id>/rtl-<config_hash>.zip
    # then create an Artifact row referencing it.
