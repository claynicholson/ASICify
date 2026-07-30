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
    Monarch projection   - blockwise rank-1 SVD (Dao et al. 2022); the k x k
                           block grid of W is projected so every block has
                           rank <= 1, which is exactly the Monarch class
    Butterfly            - realized as the Monarch projection with a
                           power-of-two block count (the product of the two
                           halves of a radix-2 butterfly chain lands in the
                           Monarch class, and one intermediate stage costs
                           only one int8 requantization in hardware)
    Activation-aware     - (future) weighted SVD using Hessian info; tracked

The Monarch factors are materialized as ordinary dense weight matrices with
structured zeros and the permutation folded into row ordering, so the rest
of the pipeline (quantize, pack, render) treats them as plain Linears.
"""

from __future__ import annotations

import math
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


@dataclass
class MonarchFactors:
    """Result of projecting one Linear onto the Monarch class.

    W (out, in) is viewed as a k x k grid of (q x p) blocks with p = in/k,
    q = out/k. Each block is replaced by its best rank-1 approximation
    l_ij @ r_ij^T (blockwise SVD), which is the optimal projection onto the
    Monarch class. The two factors are materialized densely:

        b (k*k, in):  row i*k+j carries r_ij^T in columns [j*p, (j+1)*p)
        a (out, k*k): a[i*q:(i+1)*q, i*k+j] = l_ij  (block-diagonal)

    so `a @ b` is the reconstruction, forward(x) = a @ (b @ x), and the
    fixed Monarch permutation is folded into the row ordering of `b`.
    Density of each factor is 1/k; nonzero counts are k*in and k*out.
    """

    a: torch.Tensor    # (out_features, k*k)
    b: torch.Tensor    # (k*k, in_features)
    bias: torch.Tensor | None
    n_blocks: int
    mid_features: int  # k*k
    in_features: int
    out_features: int
    nnz_a: int         # n_blocks * out_features
    nnz_b: int         # n_blocks * in_features

    def reconstruction_error(self, original: torch.Tensor) -> float:
        recon = self.a @ self.b
        denom = original.abs().mean().clamp_min(1e-12)
        return float((recon - original).abs().mean() / denom)


def monarch_decompose(
    weight: torch.Tensor,
    bias: torch.Tensor | None,
    n_blocks: int,
) -> MonarchFactors:
    """Project W onto the Monarch class via independent per-block rank-1 SVDs.

    The energy of each block's top singular value is split sqrt/sqrt between
    the two factors (same trick as `low_rank_decompose`) so neither factor
    dominates the int8 dynamic range downstream.
    """
    if weight.dim() != 2:
        raise ValueError(f"monarch_decompose expects 2D weight; got {tuple(weight.shape)}")
    out_f, in_f = weight.shape
    k = n_blocks
    if k < 2:
        raise ValueError(f"n_blocks must be >= 2; got {k}")
    if in_f % k != 0 or out_f % k != 0:
        raise ValueError(
            f"n_blocks={k} must divide both in_features={in_f} and out_features={out_f}"
        )
    p = in_f // k
    q = out_f // k

    w = weight.detach().to(torch.float32)
    # (i, j, q, p): block (i, j) of the k x k grid.
    blocks = w.reshape(k, q, k, p).permute(0, 2, 1, 3)
    u, s, vh = torch.linalg.svd(blocks, full_matrices=False)
    sqrt_s1 = torch.sqrt(s[..., 0])                    # (k, k)
    left = u[..., :, 0] * sqrt_s1.unsqueeze(-1)        # (k, k, q)
    right = vh[..., 0, :] * sqrt_s1.unsqueeze(-1)      # (k, k, p)

    b = torch.zeros(k * k, in_f, dtype=torch.float32)
    a = torch.zeros(out_f, k * k, dtype=torch.float32)
    for i in range(k):
        for j in range(k):
            b[i * k + j, j * p:(j + 1) * p] = right[i, j]
            a[i * q:(i + 1) * q, i * k + j] = left[i, j]

    return MonarchFactors(
        a=a,
        b=b,
        bias=None if bias is None else bias.detach().to(torch.float32).clone(),
        n_blocks=k,
        mid_features=k * k,
        in_features=in_f,
        out_features=out_f,
        nnz_a=k * out_f,
        nnz_b=k * in_f,
    )


def monarch_parameter_savings(in_features: int, out_features: int, n_blocks: int) -> float:
    """Fraction of parameters dropped, counting only nonzeros.

    Nonzero params are k*in + k*out, so savings grow as k shrinks (fewer,
    larger blocks) while reconstruction quality grows with k.

    >>> monarch_parameter_savings(4096, 4096, 64)
    0.96875
    """
    original = in_features * out_features
    decomposed = n_blocks * (in_features + out_features)
    if original == 0:
        return 0.0
    return 1.0 - (decomposed / original)


def auto_n_blocks(
    in_features: int,
    out_features: int,
    requested: int | None = None,
    power_of_two: bool = False,
) -> int | None:
    """Pick a block count that divides both dims, snapping down from a target.

    Target is the request if given, else round(sqrt(min dim)) — the Monarch
    paper's sqrt(n) default. Candidates are divisors of gcd(in, out) (powers
    of two only for the butterfly flavor). Returns None when no k >= 2 fits
    or when the decomposition wouldn't save parameters — callers skip the
    layer in that case, mirroring the low-rank skip logic.
    """
    if in_features < 2 or out_features < 2:
        return None
    target = requested or max(2, round(math.sqrt(min(in_features, out_features))))
    g = math.gcd(in_features, out_features)

    best: int | None = None
    for k in range(2, min(target, g) + 1):
        if g % k != 0:
            continue
        if power_of_two and (k & (k - 1)) != 0:
            continue
        best = k
    if best is None:
        return None
    if monarch_parameter_savings(in_features, out_features, best) <= 0:
        return None
    return best
