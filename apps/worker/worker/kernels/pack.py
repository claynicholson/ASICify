"""Tensor -> SystemVerilog constant-string packing.

Each quantization choice has its own packing format that matches what the
multiplier strategy in the Verilog template expects:

    INT8     : signed 8-bit per weight
               '{ '{8'sd-12, ...}, ... };

    INT4     : two signed 4-bit nibbles per byte, low nibble first
               '{ 8'h<lo:hi>, 8'h<lo:hi>, ... }
               (the layer module unpacks back to signed nibbles before MAC)

    Ternary  : 2 bits per weight (00=zero, 01=+1, 11=-1), packed 4 per byte
               '{ 8'h<...>, ... }

    Binary   : 1 bit per weight (1=+1, 0=-1), packed 8 per byte
               '{ 8'h<...>, ... }

All scales remain Q0.31 unsigned 32-bit. All biases remain pre-rescale int32.
The only thing that changes per precision is how the weights are stored.
"""

from __future__ import annotations

import torch

from worker.kernels.quantize import QuantizedLinear

# ---------------------------------------------------------------------------
# Scale + bias tables (precision-independent)
# ---------------------------------------------------------------------------


def scale_q31_array_to_sv(name: str, scale: torch.Tensor) -> str:
    if scale.dim() != 1:
        raise ValueError("scale must be 1D")
    q31 = (
        (scale.to(torch.float64) * (1 << 31))
        .round()
        .clamp(0, (1 << 31) - 1)
        .to(torch.int64)
    )
    cells = ", ".join(f"32'd{int(v)}" for v in q31.tolist())
    return f"localparam logic [31:0] {name} [0:{q31.numel() - 1}] = '{{ {cells} }};"


# Backwards-compatible alias used by older call sites and tests.
scale_q15_array_to_sv = scale_q31_array_to_sv


def bias_q_array_to_sv(name: str, bias: torch.Tensor | None, scale: torch.Tensor) -> str:
    if bias is None:
        return f"// {name}: no bias for this layer"
    if bias.dim() != 1:
        raise ValueError("bias must be 1D")
    s = scale.to(torch.float64).clamp_min(1e-30)
    bias_int = (
        (bias.to(torch.float64) / s)
        .round()
        .clamp(-(2**31), 2**31 - 1)
        .to(torch.int64)
    )
    cells = ", ".join(
        f"32'sd{int(v)}" if int(v) >= 0 else f"-32'sd{-int(v)}"
        for v in bias_int.tolist()
    )
    return (
        f"localparam logic signed [31:0] {name} [0:{bias_int.numel() - 1}] = "
        f"'{{ {cells} }};"
    )


# ---------------------------------------------------------------------------
# Weight tables (precision-specific)
# ---------------------------------------------------------------------------


def int8_array_to_sv(name: str, tensor: torch.Tensor) -> str:
    """Per-weight signed 8-bit array. INT8 path."""
    if tensor.dim() != 2 or tensor.dtype != torch.int8:
        raise ValueError(
            f"int8_array_to_sv expects 2D int8; got "
            f"shape={tuple(tensor.shape)} dtype={tensor.dtype}"
        )
    out_f, in_f = tensor.shape
    rows: list[str] = []
    for row in tensor.tolist():
        cells = ", ".join(f"8'sd{v}" if v >= 0 else f"-8'sd{-v}" for v in row)
        rows.append(f"        '{{ {cells} }}")
    body = ",\n".join(rows)
    return (
        f"localparam logic signed [7:0] {name} [0:{out_f - 1}][0:{in_f - 1}] = "
        f"'{{\n{body}\n    }};"
    )


def int4_array_to_sv(name: str, tensor: torch.Tensor) -> str:
    """Pack signed 4-bit weights two-per-byte, low nibble first.

    Each row is padded to an even number of weights with zeros if needed. The
    Verilog template unpacks via shift+sign-extend before the MAC.
    """
    if tensor.dim() != 2 or tensor.dtype != torch.int8:
        raise ValueError("int4_array_to_sv expects 2D int8 tensor in [-7, 7]")
    out_f, in_f = tensor.shape
    bytes_per_row = (in_f + 1) // 2
    rows: list[str] = []
    for row in tensor.tolist():
        bytes_out: list[str] = []
        for j in range(bytes_per_row):
            lo = row[2 * j] if 2 * j < in_f else 0
            hi = row[2 * j + 1] if 2 * j + 1 < in_f else 0
            byte = ((lo & 0xF) | ((hi & 0xF) << 4)) & 0xFF
            bytes_out.append(f"8'h{byte:02x}")
        rows.append(f"        '{{ {', '.join(bytes_out)} }}")
    body = ",\n".join(rows)
    return (
        f"localparam logic [7:0] {name} [0:{out_f - 1}][0:{bytes_per_row - 1}] = "
        f"'{{\n{body}\n    }};"
    )


def ternary_array_to_sv(name: str, tensor: torch.Tensor) -> str:
    """Pack ternary weights 4-per-byte. Encoding: 00=zero, 01=+1, 11=-1.

    Rows are padded with zeros if not divisible by 4. The Verilog template
    decodes each 2-bit chunk via a small mux: out = byte[1:0]==01 ? +x : byte[1:0]==11 ? -x : 0.
    """
    if tensor.dim() != 2 or tensor.dtype != torch.int8:
        raise ValueError("ternary_array_to_sv expects 2D int8 tensor in {-1, 0, 1}")
    out_f, in_f = tensor.shape
    bytes_per_row = (in_f + 3) // 4
    rows: list[str] = []
    for row in tensor.tolist():
        bytes_out: list[str] = []
        for j in range(bytes_per_row):
            byte = 0
            for k in range(4):
                idx = 4 * j + k
                v = row[idx] if idx < in_f else 0
                code = 0 if v == 0 else (1 if v > 0 else 3)
                byte |= (code & 0x3) << (2 * k)
            bytes_out.append(f"8'h{byte:02x}")
        rows.append(f"        '{{ {', '.join(bytes_out)} }}")
    body = ",\n".join(rows)
    return (
        f"localparam logic [7:0] {name} [0:{out_f - 1}][0:{bytes_per_row - 1}] = "
        f"'{{\n{body}\n    }};"
    )


def fp16_array_to_sv(name: str, tensor: torch.Tensor) -> str:
    """Pack FP16 weights as 16-bit hex literals.

    Each FP16 value goes out as `16'h<bit-pattern>`. The Verilog FP16
    multiplier reads these as IEEE half-precision floats. Compatible with
    Verilator (which has $shortrealtobits) and synthesis tools that infer
    fp16 multipliers from the right module pattern.
    """
    if tensor.dim() != 2 or tensor.dtype != torch.float16:
        raise ValueError(
            f"fp16_array_to_sv expects 2D float16; got "
            f"shape={tuple(tensor.shape)} dtype={tensor.dtype}"
        )
    out_f, in_f = tensor.shape
    rows: list[str] = []
    for row in tensor.view(torch.int16).tolist():
        # int16 view of fp16 bits; convert negative two's-complement back to
        # the unsigned 16-bit hex pattern Verilog expects.
        cells = ", ".join(f"16'h{(v & 0xFFFF):04x}" for v in row)
        rows.append(f"        '{{ {cells} }}")
    body = ",\n".join(rows)
    return (
        f"localparam logic [15:0] {name} [0:{out_f - 1}][0:{in_f - 1}] = "
        f"'{{\n{body}\n    }};"
    )


def binary_array_to_sv(name: str, tensor: torch.Tensor) -> str:
    """Pack binary weights 8-per-byte. Encoding: 1=+1, 0=-1. LSB first."""
    if tensor.dim() != 2 or tensor.dtype != torch.int8:
        raise ValueError("binary_array_to_sv expects 2D int8 tensor in {-1, +1}")
    out_f, in_f = tensor.shape
    bytes_per_row = (in_f + 7) // 8
    rows: list[str] = []
    for row in tensor.tolist():
        bytes_out: list[str] = []
        for j in range(bytes_per_row):
            byte = 0
            for k in range(8):
                idx = 8 * j + k
                v = row[idx] if idx < in_f else 1
                bit = 1 if v > 0 else 0
                byte |= (bit & 1) << k
            bytes_out.append(f"8'h{byte:02x}")
        rows.append(f"        '{{ {', '.join(bytes_out)} }}")
    body = ",\n".join(rows)
    return (
        f"localparam logic [7:0] {name} [0:{out_f - 1}][0:{bytes_per_row - 1}] = "
        f"'{{\n{body}\n    }};"
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def pack_layernorm(symbol: str, qln) -> str:
    """Emit gamma/beta/eps for a quantized LayerNorm (int32 Q15 representation)."""
    n = qln.dim

    def _int32_array(name: str, t: torch.Tensor) -> str:
        cells = ", ".join(
            f"32'sd{int(v)}" if int(v) >= 0 else f"-32'sd{-int(v)}" for v in t.tolist()
        )
        return f"localparam logic signed [31:0] {name} [0:{n - 1}] = '{{ {cells} }};"

    return "\n".join(
        [
            f"// {symbol}: LayerNorm dim={n}",
            _int32_array(f"GAMMA_Q15_{symbol}", qln.gamma_q15),
            _int32_array(f"BETA_Q15_{symbol}", qln.beta_q15),
            f"localparam logic [31:0] EPS_Q15_{symbol} = 32'd{int(qln.eps_q15)};",
        ]
    )


def pack_embedding(symbol: str, qe) -> str:
    """Emit the int8 embedding lookup table."""
    if qe.table_int8.dim() != 2 or qe.table_int8.dtype != torch.int8:
        raise ValueError("embedding table must be 2D int8")
    vocab, dim = qe.table_int8.shape
    rows: list[str] = []
    for row in qe.table_int8.tolist():
        cells = ", ".join(f"8'sd{v}" if v >= 0 else f"-8'sd{-v}" for v in row)
        rows.append(f"        '{{ {cells} }}")
    body = ",\n".join(rows)
    return "\n".join(
        [
            f"// {symbol}: Embedding vocab={vocab} dim={dim}",
            f"localparam logic signed [7:0] EMBED_{symbol} [0:{vocab - 1}][0:{dim - 1}] = "
            f"'{{\n{body}\n    }};",
        ]
    )


def pack_layer(symbol: str, q: QuantizedLinear) -> str:
    """Emit the three localparam declarations for one Linear layer.

    The weight array's storage format depends on q.quantization. The scale and
    bias tables stay constant across precisions.
    """
    if q.quantization == "int8":
        weights_sv = int8_array_to_sv(f"W_{symbol}", q.weight_int8)
    elif q.quantization == "int4":
        weights_sv = int4_array_to_sv(f"W_{symbol}", q.weight_int8)
    elif q.quantization == "ternary":
        weights_sv = ternary_array_to_sv(f"W_{symbol}", q.weight_int8)
    elif q.quantization == "binary":
        weights_sv = binary_array_to_sv(f"W_{symbol}", q.weight_int8)
    elif q.quantization == "fp16":
        weights_sv = fp16_array_to_sv(f"W_{symbol}", q.weight_int8)
    else:
        weights_sv = int8_array_to_sv(f"W_{symbol}", q.weight_int8)

    return "\n".join(
        [
            f"// {symbol}: in={q.in_features} out={q.out_features} quant={q.quantization}",
            weights_sv,
            scale_q31_array_to_sv(f"SCALE_Q31_{symbol}", q.scale),
            bias_q_array_to_sv(f"BIAS_Q_{symbol}", q.bias, q.scale),
        ]
    )
