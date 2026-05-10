"""End-to-end tests: tiny MLP -> RTL package -> Python reference matches kernel.

This is the test that locks in the bit-exactness guarantee. If a future change
to the kernel, the pack module, the templates, or the rescale arithmetic
breaks the equivalence between in-process compute and the generated RTL, this
test fails.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

from worker.cli import TinyMLP, _default_config
from worker.kernels.quantize import linear_int8_forward
from worker.pipeline.parse import parse_module
from worker.pipeline.quantize import quantize_graph
from worker.rtl.generator import render_to_directory


def _load_reference_module(out_dir: Path):
    """Import the freshly-rendered reference.py without polluting sys.modules."""
    spec = importlib.util.spec_from_file_location(
        "asicify_test_reference", out_dir / "reference.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def compiled_mlp(tmp_path: Path):
    """Render a tiny MLP into a temp directory and return (graph, kernel_quants, reference_module)."""
    torch.manual_seed(0)
    model = TinyMLP(in_features=8, hidden=16, out_features=4)
    model.eval()

    graph = parse_module(model, name="tiny_mlp", task="classification")
    config = _default_config()
    graph = quantize_graph(graph, config)

    out_dir = tmp_path / "rtl"
    render_to_directory(graph, config, out_dir)

    return {
        "graph": graph,
        "quant": graph.metadata["_quantized"],
        "reference": _load_reference_module(out_dir),
        "out_dir": out_dir,
    }


def test_rtl_package_files_exist(compiled_mlp):
    """The renderer emits the full package."""
    out = compiled_mlp["out_dir"]
    expected = [
        "top.v",
        "weights.vh",
        "modules/layer_fc1.v",
        "modules/layer_fc2.v",
        "reference.py",
        "tb_top.py",
        "Makefile",
        "synthesis/yosys.tcl",
        "synthesis/nextpnr.sh",
        "synthesis/vivado.tcl",
        "README.md",
    ]
    for rel in expected:
        assert (out / rel).is_file(), f"missing {rel}"


def test_weights_vh_contains_real_constants(compiled_mlp):
    """The weights header must contain actual int8 numeric literals, not zeros or stubs."""
    weights_vh = (compiled_mlp["out_dir"] / "weights.vh").read_text()
    assert "W_fc1" in weights_vh
    assert "W_fc2" in weights_vh
    assert "SCALE_Q31_fc1" in weights_vh
    assert "BIAS_Q_fc1" in weights_vh
    # At least one weight should hit the saturation rail at +127 or -127 because
    # of how per-row max-abs scaling works.
    assert "8'sd127" in weights_vh or "-8'sd127" in weights_vh


def test_reference_matches_kernel_bit_exact(compiled_mlp):
    """The generated reference.py and the in-process kernel produce identical output.

    This is the central correctness invariant: if Verilator runs the RTL and
    cocotb checks against reference.py, and reference.py matches the kernel,
    then the RTL matches the kernel by transitivity. Run on multiple random
    inputs to catch sign/wrap edge cases.
    """
    quant = compiled_mlp["quant"]
    reference = compiled_mlp["reference"]

    rng = torch.Generator().manual_seed(123)
    for trial in range(32):
        x_int8 = torch.randint(-128, 128, (8,), generator=rng, dtype=torch.int8)

        # In-process expected: layer 1 -> clip to int8 -> layer 2.
        h_int32 = linear_int8_forward(x_int8, quant["fc1"]).to(torch.int32)
        h_int8 = torch.clamp(h_int32, -128, 127).to(torch.int8)
        expected = linear_int8_forward(h_int8, quant["fc2"]).to(torch.int32).numpy()

        actual = np.asarray(reference.reference_forward(x_int8.tolist()), dtype=np.int32)

        assert np.array_equal(actual, expected), (
            f"trial {trial}: actual {actual.tolist()} != expected {expected.tolist()}"
        )


def test_reference_input_shape_validation(compiled_mlp):
    """reference_forward should reject inputs of the wrong length."""
    reference = compiled_mlp["reference"]
    with pytest.raises(ValueError):
        reference.reference_forward([1, 2, 3])  # MLP expects 8 inputs


def test_quantization_per_layer_sensible(compiled_mlp):
    """Each linear layer should round-trip with low reconstruction error."""
    graph = compiled_mlp["graph"]
    quant = graph.metadata["_quantized"]
    weights = graph.metadata["_weights"]
    for name, ql in quant.items():
        err = ql.reconstruction_error(weights[name])
        assert err < 0.02, f"{name}: reconstruction error {err} too large"
