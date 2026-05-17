"""Sparsity kernels.

All sparsity operates on the *float* weight tensor before quantization. The
result is a tensor of the same shape with the dropped weights set to zero.
The downstream quantizer doesn't need to know — zeros stay zero through
quantization, and the pack module emits them as `8'sd0` / nibble 0 / ternary
code 00 / binary "no zero allowed" branch.

For binary precision we *cannot* zero out a weight (binary is {-1, +1}). The
2:4 etc. patterns are skipped silently for binary; if you want sparsity at
binary precision, use ternary instead.

Patterns:
    structured_2_4  : every group of 4 contiguous weights keeps the 2 largest by |w|
    structured_4_8  : every group of 8 keeps the 4 largest by |w|
    block_sparse_16 : every 16x16 tile is kept-or-dropped as a whole, drop_ratio
    unstructured    : keep top-N by global magnitude, where N = (1 - ratio) * total
"""

from __future__ import annotations

import torch


def apply_2_to_4(weight: torch.Tensor) -> torch.Tensor:
    """Each consecutive 4-weight group along the in-features axis keeps the 2 largest by |w|.

    Pads the in-features axis with zeros to a multiple of 4 if needed (those
    pads stay zero in the output). Returns a tensor of the same shape as input,
    minus the padding.
    """
    if weight.dim() != 2:
        raise ValueError("apply_2_to_4 expects 2D weight")
    out_f, in_f = weight.shape
    pad = (4 - in_f % 4) % 4
    w = torch.nn.functional.pad(weight, (0, pad))  # pad on right of in axis
    grouped = w.reshape(out_f, -1, 4)
    abs_w = grouped.abs()
    # Find indices of the top-2 by magnitude in each group of 4.
    _, idx = abs_w.topk(2, dim=-1)
    mask = torch.zeros_like(grouped, dtype=torch.bool)
    mask.scatter_(-1, idx, True)
    out = (grouped * mask.to(grouped.dtype)).reshape(out_f, -1)
    return out[:, :in_f]


def apply_4_to_8(weight: torch.Tensor) -> torch.Tensor:
    if weight.dim() != 2:
        raise ValueError("apply_4_to_8 expects 2D weight")
    out_f, in_f = weight.shape
    pad = (8 - in_f % 8) % 8
    w = torch.nn.functional.pad(weight, (0, pad))
    grouped = w.reshape(out_f, -1, 8)
    abs_w = grouped.abs()
    _, idx = abs_w.topk(4, dim=-1)
    mask = torch.zeros_like(grouped, dtype=torch.bool)
    mask.scatter_(-1, idx, True)
    out = (grouped * mask.to(grouped.dtype)).reshape(out_f, -1)
    return out[:, :in_f]


def apply_unstructured(weight: torch.Tensor, ratio: float) -> torch.Tensor:
    """Drop the bottom `ratio` fraction of weights by absolute magnitude (per row)."""
    if not 0.0 <= ratio < 1.0:
        raise ValueError(f"ratio must be in [0, 1); got {ratio}")
    if ratio == 0.0:
        return weight.clone()
    _out_f, in_f = weight.shape
    keep = max(1, round(in_f * (1.0 - ratio)))
    abs_w = weight.abs()
    _, idx = abs_w.topk(keep, dim=-1)
    mask = torch.zeros_like(weight, dtype=torch.bool)
    mask.scatter_(-1, idx, True)
    return weight * mask.to(weight.dtype)


def apply_block_sparse(weight: torch.Tensor, ratio: float, block: int = 16) -> torch.Tensor:
    """Drop entire `block`x`block` tiles by mean magnitude.

    Tiles whose mean |w| falls in the bottom `ratio` fraction get zeroed out.
    """
    if not 0.0 <= ratio < 1.0:
        raise ValueError(f"ratio must be in [0, 1); got {ratio}")
    if ratio == 0.0:
        return weight.clone()
    out_f, in_f = weight.shape
    tiles_o = (out_f + block - 1) // block
    tiles_i = (in_f + block - 1) // block
    pad_o = tiles_o * block - out_f
    pad_i = tiles_i * block - in_f
    w = torch.nn.functional.pad(weight, (0, pad_i, 0, pad_o))
    # Reshape into (tiles_o, block, tiles_i, block)
    tiled = w.reshape(tiles_o, block, tiles_i, block)
    abs_means = tiled.abs().mean(dim=(1, 3))  # (tiles_o, tiles_i)
    n_tiles = tiles_o * tiles_i
    drop = max(0, round(n_tiles * ratio))
    if drop == 0:
        return weight.clone()
    flat = abs_means.reshape(-1)
    threshold = flat.kthvalue(drop).values
    keep_mask = (abs_means > threshold).to(weight.dtype)  # (tiles_o, tiles_i)
    keep_full = keep_mask.unsqueeze(1).unsqueeze(3).expand(tiles_o, block, tiles_i, block)
    out = (tiled * keep_full).reshape(tiles_o * block, tiles_i * block)
    return out[:out_f, :in_f]


def apply_sparsity(weight: torch.Tensor, sparsity_type: str, ratio: float) -> torch.Tensor:
    if sparsity_type == "none" or ratio == 0.0:
        return weight.clone()
    if sparsity_type == "structured_2_4":
        return apply_2_to_4(weight)
    if sparsity_type == "structured_4_8":
        return apply_4_to_8(weight)
    if sparsity_type == "block_sparse_16":
        return apply_block_sparse(weight, ratio, block=16)
    if sparsity_type == "unstructured":
        return apply_unstructured(weight, ratio)
    raise ValueError(f"unknown sparsity type: {sparsity_type}")


def sparsity_ratio(weight: torch.Tensor) -> float:
    """Fraction of weights that are exactly zero."""
    return float((weight == 0).sum() / weight.numel())
