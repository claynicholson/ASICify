"""asicify CLI.

Two subcommands today:

    asicify demo --output ./build/demo
        Build a tiny two-layer MLP, quantize to INT8, render the full RTL
        package, and verify the generated Python reference matches what the
        in-process kernel produces. Self-contained: no network, no model
        files, no GPU.

    asicify estimate --target <id>
        Print a hardware estimate for the demo MLP at a given target.

Future (when the hosted extra is installed):

    asicify compile <model> ...
        Real model loading from local checkpoints or HuggingFace IDs.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import torch
from torch import nn

from worker.estimator.runner import estimate
from worker.kernels.quantize import linear_int8_forward
from worker.pipeline.parse import parse_module
from worker.pipeline.quantize import quantize_graph
from worker.rtl.generator import render_to_directory
from worker.types import (
    CompressionConfig,
    DecompositionConfig,
    SparsityConfig,
)


class TinyMLP(nn.Module):
    """Two-layer MLP. Used by the demo and the test suite."""

    def __init__(self, in_features: int = 8, hidden: int = 16, out_features: int = 4):
        super().__init__()
        self.fc1 = nn.Linear(in_features, hidden, bias=True)
        self.fc2 = nn.Linear(hidden, out_features, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc2(torch.relu(self.fc1(x)))


def _default_config() -> CompressionConfig:
    return CompressionConfig(
        quantization="int8",
        sparsity=SparsityConfig(type="none", ratio=0.0),
        decomposition=DecompositionConfig(type="none"),
    )


def cmd_demo(args: argparse.Namespace) -> int:
    out_dir = Path(args.output).resolve()
    torch.manual_seed(args.seed)

    model = TinyMLP(
        in_features=args.in_features,
        hidden=args.hidden,
        out_features=args.out_features,
    )
    model.eval()

    print(f"-> Building TinyMLP ({args.in_features} -> {args.hidden} -> {args.out_features})")
    print(f"   Parameters: {sum(p.numel() for p in model.parameters())}")

    print("-> Parsing module via worker.pipeline.parse")
    graph = parse_module(model, name="tiny_mlp", task="classification")
    for layer in graph.layers:
        if layer.kind == "linear":
            print(
                f"   linear  {layer.name:25}  "
                f"{layer.in_features:>4} -> {layer.out_features:<4}"
            )

    print("-> Quantizing to INT8 symmetric per-channel")
    config = _default_config()
    graph = quantize_graph(graph, config)
    quant = graph.metadata["_quantized"]
    weights = graph.metadata["_weights"]
    for name, ql in quant.items():
        err = ql.reconstruction_error(weights[name])
        print(f"   quant   {name:25}  recon error = {err:.5f}")

    print(f"-> Rendering RTL package to {out_dir}")
    render_to_directory(graph, config, out_dir)
    rendered = sorted(
        p.relative_to(out_dir).as_posix() for p in out_dir.rglob("*") if p.is_file()
    )
    for f in rendered:
        size = (out_dir / f).stat().st_size
        print(f"   {f:40}  {size:>6} bytes")

    print("-> Cross-checking generated reference vs in-process kernel")
    if "reference" in sys.modules:
        del sys.modules["reference"]
    sys.path.insert(0, str(out_dir))
    try:
        reference = importlib.import_module("reference")
    finally:
        sys.path.pop(0)

    rng = torch.Generator().manual_seed(args.seed + 1)
    x_int8 = torch.randint(
        -32, 32, (args.in_features,), generator=rng, dtype=torch.int8
    )

    # In-process expected: run each layer's int8 forward, clip to int8 between layers.
    h_int32 = linear_int8_forward(x_int8, quant["fc1"]).to(torch.int32)
    h_int8 = torch.clamp(h_int32, -128, 127).to(torch.int8)
    expected = linear_int8_forward(h_int8, quant["fc2"]).to(torch.int32).cpu().numpy()

    actual = reference.reference_forward(x_int8.tolist())

    import numpy as np

    actual_np = np.asarray(actual, dtype=np.int32)

    if np.array_equal(actual_np, expected):
        print(
            f"   PASS  reference output [{actual_np.shape[0]}] = "
            f"{actual_np.tolist()}"
        )
    else:
        print(f"   FAIL  reference output {actual_np.tolist()}")
        print(f"         expected         {expected.tolist()}")
        return 1

    print("-> Hardware estimate (target = sky130)")
    e = estimate(graph, config, "sky130")
    print(
        json.dumps(
            {
                "target": e["target"],
                "area_mm2": round(e["area_mm2"], 6),
                "throughput_per_sec": round(e["throughput_per_sec"], 1),
                "cost_at_100k_usd": round(e["cost_per_chip"]["100000"], 4),
                "confidence": e["confidence"],
            },
            indent=2,
        )
    )

    return 0


def cmd_estimate(args: argparse.Namespace) -> int:
    torch.manual_seed(0)
    model = TinyMLP()
    graph = parse_module(model, name="tiny_mlp", task="classification")
    config = _default_config()
    graph = quantize_graph(graph, config)
    e = estimate(graph, config, args.target)

    # Strip non-serializable bits before printing.
    e = {k: v for k, v in e.items() if k != "graph"}
    json.dump(e, sys.stdout, indent=2, default=float)
    print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="asicify", description="ASICify CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    demo = sub.add_parser("demo", help="End-to-end TinyMLP demo")
    demo.add_argument("--output", default="./build/demo")
    demo.add_argument("--in-features", type=int, default=8)
    demo.add_argument("--hidden", type=int, default=16)
    demo.add_argument("--out-features", type=int, default=4)
    demo.add_argument("--seed", type=int, default=0)
    demo.set_defaults(func=cmd_demo)

    est = sub.add_parser("estimate", help="Hardware estimate for the TinyMLP demo")
    est.add_argument("--target", default="sky130")
    est.set_defaults(func=cmd_estimate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
