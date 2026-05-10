"""Tensor-level operations used by the compression pipeline.

The pipeline modules in worker/pipeline/ are pure orchestration: they walk a
ModelGraph, decide what to do, and call into this kernels package to do the
actual numeric work on real PyTorch tensors.
"""
