"""asicify CLI — local compile without the hosted service.

  asicify compile <model> --quantization int4 --sparsity 2:4 --target tsmc28,ecp5

Useful for CI pipelines and reproducible research. Same compiler as the
hosted product; just runs the worker pipeline directly against a local model.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from worker.estimator.runner import estimate
from worker.pipeline.orchestrator import _cfg_from_dict
from worker.pipeline.parse import parse_model
from worker.rtl.generator import render_package
from worker.types import CompressionConfig, DecompositionConfig, SparsityConfig


def parse_sparsity(spec: str) -> SparsityConfig:
    if spec == "none" or spec == "0":
        return SparsityConfig(type="none", ratio=0.0)
    if spec == "2:4":
        return SparsityConfig(type="structured_2_4", ratio=0.5)
    if spec == "4:8":
        return SparsityConfig(type="structured_4_8", ratio=0.5)
    try:
        ratio = float(spec) / 100 if "%" in spec else float(spec)
        return SparsityConfig(type="unstructured", ratio=ratio)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Bad sparsity spec: {spec}") from e


def main() -> None:
    parser = argparse.ArgumentParser(prog="asicify", description="ASICify CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    compile_parser = sub.add_parser("compile", help="Compile a model to RTL")
    compile_parser.add_argument("model", help="HuggingFace model id or local path")
    compile_parser.add_argument("--quantization", default="int8")
    compile_parser.add_argument("--sparsity", default="none", type=parse_sparsity)
    compile_parser.add_argument("--decomposition", default="none")
    compile_parser.add_argument("--target", default="tsmc28")
    compile_parser.add_argument("--output", default="./build")

    estimate_parser = sub.add_parser("estimate", help="Run hardware estimation only")
    estimate_parser.add_argument("model")
    estimate_parser.add_argument("--target", default="tsmc28")

    args = parser.parse_args()

    if args.cmd == "compile":
        cfg = CompressionConfig(
            quantization=args.quantization,
            sparsity=args.sparsity,
            decomposition=DecompositionConfig(type=args.decomposition),
        )
        graph = parse_model({"id": args.model, "type": "huggingface"})
        package = render_package(graph, cfg)
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        zip_path = out / f"{args.model.replace('/', '_')}.zip"
        zip_path.write_bytes(package)
        print(f"Wrote {zip_path} ({len(package)/1024:.1f} KB)")

        targets = args.target.split(",")
        for t in targets:
            e = estimate(graph, cfg, t.strip())
            print(json.dumps({"target": t.strip(), **e}, indent=2))

    elif args.cmd == "estimate":
        graph = parse_model({"id": args.model, "type": "huggingface"})
        cfg = CompressionConfig()
        e = estimate(graph, cfg, args.target)
        print(json.dumps(e, indent=2))


if __name__ == "__main__":
    sys.exit(main() or 0)
