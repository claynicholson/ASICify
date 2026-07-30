"""Close the bit-exactness chain: kernel <-> reference.py <-> RTL.

The rest of the suite proves `kernel == reference.py`. This test runs the
generated cocotb testbench (`tb_top.py`, 8 random vectors) under Verilator
via the package's own `make sim` target, machine-checking the
`reference.py == RTL` leg. By transitivity the RTL matches the kernel.

Skipped automatically when the RTL toolchain (verilator, cocotb, make)
isn't on PATH, so plain `pytest` stays fast on laptops without EDA tools.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import torch
from torch import nn

from worker.pipeline.parse import parse_module
from worker.pipeline.quantize import quantize_graph
from worker.rtl.generator import render_to_directory
from worker.types import CompressionConfig, DecompositionConfig, SparsityConfig

_TOOLS_MISSING = (
    shutil.which("verilator") is None
    or shutil.which("cocotb-config") is None
    or shutil.which("make") is None
)

# Locally, missing tools skip the test. In CI, ASICIFY_REQUIRE_SIM=1 forces
# it to run (and fail loudly) so a broken tool install can't go green.
requires_sim_tools = pytest.mark.skipif(
    _TOOLS_MISSING and not os.environ.get("ASICIFY_REQUIRE_SIM"),
    reason="RTL simulation needs verilator, cocotb, and make on PATH",
)


class TinyMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(8, 16)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(16, 4)

    def forward(self, x):
        return self.fc2(self.relu(self.fc1(x)))


@requires_sim_tools
@pytest.mark.sim
def test_generated_package_simulates_bit_exact(tmp_path: Path):
    torch.manual_seed(0)
    config = CompressionConfig(
        quantization="int8",
        sparsity=SparsityConfig(type="none", ratio=0.0),
        decomposition=DecompositionConfig(type="none"),
    )
    graph = parse_module(TinyMLP(), name="tiny_mlp", task="classification")
    graph = quantize_graph(graph, config)

    pkg = tmp_path / "pkg"
    render_to_directory(graph, config, pkg)

    env = os.environ.copy()
    result = subprocess.run(
        ["make", "sim"],
        cwd=pkg,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"make sim failed:\n{output}"

    # cocotb's Makefile flow doesn't always propagate test failures into the
    # exit code, so check the JUnit results file explicitly.
    results = pkg / "results.xml"
    assert results.is_file(), f"no results.xml produced:\n{output}"
    xml = results.read_text()
    assert re.search(r"<(failure|error)\b", xml) is None, f"cocotb reported failures:\n{xml}"
    assert 'name="bit_exact_random"' in xml
