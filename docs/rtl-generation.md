# RTL Generation

How ASICify turns a compressed `ModelGraph` into a synthesizable Verilog
package.

## Architecture: layer-pipelined dataflow

- Each layer is its own physical region
- Activations stream forward through layers
- Pipeline registers between layers for timing closure
- KV cache lives in BRAM-mapped buffers

This trades silicon area for latency and throughput predictability. For models
that fit comfortably on one die (<1B params at INT4), this is the right
default. Larger models need tile-based reuse; see the roadmap.

## Templates

One Jinja2 template per primitive, in
[`apps/worker/worker/rtl/templates/`](../apps/worker/worker/rtl/templates):

| Template                | Generates                              |
| ----------------------- | -------------------------------------- |
| `top.v.j2`              | Top wrapper; wires layers in pipeline  |
| `linear_layer.v.j2`     | Fixed-coefficient matrix-vector MAC    |
| `fp16_layer.v.j2`       | FP16 linear layer (behavioral float multiply) |
| `attention_block.v.j2`  | Q/K/V/O projections + softmax + KV cache, wired structurally |
| `layernorm.v.j2`        | Mean/variance + normalize+scale+shift  |
| `embedding.v.j2`        | Mask-ROM lookup table                  |
| `softmax.v.j2`          | LUT-based integer softmax              |
| `kv_cache.v.j2`         | Addressable BRAM read/write port       |
| `weights.vh.j2`         | Hardwired weight constants             |
| `tb_top.py.j2`          | Cocotb testbench                       |
| `reference.py.j2`       | Bit-exact Python reference             |
| `Makefile.j2`           | sim / synth-yosys / synth-vivado       |
| `yosys.tcl.j2`          | Yosys synthesis script                 |
| `nextpnr.sh.j2`         | nextpnr place-and-route (ECP5)         |
| `vivado.tcl.j2`         | Vivado script (Xilinx)                 |
| `README.md.j2`          | Package README                         |

## Multiplier strategies

| Precision | Strategy             | Verilog idiom                              |
| --------- | -------------------- | ------------------------------------------ |
| binary    | XNOR + bit-count     | `~(in ^ w) ? 1 : -1` aggregated            |
| ternary   | sign-flip + zero-out | `case (w) 01: +in; 11: -in; default: 0`    |
| INT4      | CSD shift-add        | `±(in << a) ± (in << b)`                   |
| INT8      | Booth                | `$signed(in) * $signed(w)` (synth folds)   |
| FP16      | LUT-based            | small per-multiply ROM                     |

The `weights.vh` file declares each weight as a `localparam`, and the
synthesis tool folds the constants into the multiplier inputs, which is how
the area numbers come down. For binary and ternary, this turns into a
network of XOR/AND gates with no actual multipliers.

## Verification

The cocotb testbench drives random inputs through the RTL and compares each
output to the Python reference. For deterministic operations the comparison
is bit-exact; for parallel reductions a small tolerance applies.

The reference Python (`reference.py`) loads the same weight tensors that were
packed into `weights.vh` and applies them with the same fixed-point
arithmetic the multiplier strategy uses. This means CI can run the testbench
on push and fail the build on any drift between RTL and reference.

## Synthesis flow

For ECP5 (open-source, recommended for MVP):

```
make synth-yosys
# emits build/top.json → nextpnr-ecp5 → ecppack → top.bit
```

For Xilinx Artix-7 / Kria:

```
make synth-vivado
# Vivado batch mode → place + route → bitstream + utilization report
```

For sky130 ASIC tape-out, drop the package into [OpenLane](https://github.com/The-OpenROAD-Project/OpenLane)
and use the supplied `weights.vh` + module list.
