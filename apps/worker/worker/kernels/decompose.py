"""Low-rank decomposition kernels.

Replace a single `Linear(in, out)` with two:
    Linear_B(in, r) -> Linear_A(r, out)
where W ≈ A @ B (an SVD truncation to rank r).

Parameter count drops from `out * in` to `out * r + r * in = r * (out + in)`,
so the savings are large when r << min(in, out). For 4096x4096 with r=128,
that's a 16x reduction.

The pipeline integration replaces the original layer's float weight tensor
with two new tensors (B and A) plus inserts a synthetic "low_rank_pair" layer
record that the generator can render as two cascaded Linear modules.

Algorithms today:
    SVD truncation       - exact best-rank-r approximation in L2
    Activation-aware     - (future) weighted SVD using Hessian info; tracked

Monarch and butterfly factorizations live alongside this in spirit but
require their own kernels (block-diagonal A and B with permutations).
"""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass
class LowRankFactors:
    """Result of decomposing one Linear into two via SVD truncation.

    Reconstructs as: forward(x) = A @ (B @ x)
    Stored as float tensors; quantization happens downstream as usual.
    """

    a: torch.Tensor    # (out_features, rank)
    b: torch.Tensor    # (rank, in_features)
    bias: torch.Tensor | None
    rank: int
    in_features: int
    out_features: int

    def reconstruction_error(self, original: torch.Tensor) -> float:
        recon = self.a @ self.b
        denom = original.abs().mean().clamp_min(1e-12)
        return float((recon - original).abs().mean() / denom)


def low_rank_decompose(
    weight: torch.Tensor,
    bias: torch.Tensor | None,
    rank: int,
) -> LowRankFactors:
    """Truncated SVD: W ≈ U[:, :r] * S[:r] @ V^T[:r, :].

    Returns A = U * sqrt(S) and B = sqrt(S) * V^T so the energy is split
    between the two factors. Either factor alone has the same Frobenius
    norm, which is the best conditioning for downstream quantization.
    """
    if weight.dim() != 2:
        raise ValueError(f"low_rank_decompose expects 2D weight; got {tuple(weight.shape)}")
    out_f, in_f = weight.shape
    rank = min(rank, out_f, in_f)
    if rank <= 0:
        raise ValueError(f"rank must be positive; got {rank}")

    w = weight.detach().to(torch.float32)
    u, s, vh = torch.linalg.svd(w, full_matrices=False)
    # Truncate.
    u = u[:, :rank]              # (out_f, rank)
    s = s[:rank]                 # (rank,)
    vh = vh[:rank, :]            # (rank, in_f)
    sqrt_s = torch.sqrt(s)

    a = u * sqrt_s.unsqueeze(0)              # (out_f, rank)
    b = vh * sqrt_s.unsqueeze(1)             # (rank, in_f)

    return LowRankFactors(
        a=a,
        b=b,
        bias=None if bias is None else bias.detach().to(torch.float32).clone(),
        rank=rank,
        in_features=in_f,
        out_features=out_f,
    )


def parameter_savings(in_features: int, out_features: int, rank: int) -> float:
    """Fraction of parameters dropped by the decomposition.

    >>> parameter_savings(4096, 4096, 128)
    0.9375
    """
    original = in_features * out_features
    decomposed = rank * (in_features + out_features)
    if original == 0:
        return 0.0
    return 1.0 - (decomposed / original)
