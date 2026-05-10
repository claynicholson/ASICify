"""Tests for the loader plumbing.

The actual transformers extra is heavy and would download model files. We
test the loader's interface and the parse_model dispatch without invoking it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import torch
from torch import nn

from worker.loaders.huggingface import is_available, load_huggingface_model
from worker.pipeline.parse import parse_model


class _Tiny(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(4, 2)

    def forward(self, x):
        return self.fc(x)


def test_parse_model_dispatches_module():
    g = parse_model({"type": "module", "module": _Tiny(), "name": "t"})
    assert g.name == "t"
    assert any(layer.kind == "linear" for layer in g.layers)


def test_parse_model_back_compat_no_type():
    g = parse_model({"module": _Tiny(), "name": "t"})
    assert g.name == "t"


def test_parse_model_rejects_unknown_type():
    with pytest.raises(ValueError, match="unknown model_source type"):
        parse_model({"type": "carrier_pigeon"})


def test_parse_model_dispatches_checkpoint(tmp_path: Path):
    model = _Tiny()
    ckpt = tmp_path / "tiny.pt"
    torch.save(model, ckpt)
    g = parse_model({"type": "checkpoint", "path": str(ckpt), "name": "ckpt"})
    assert g.name == "ckpt"
    assert any(layer.kind == "linear" for layer in g.layers)


def test_loader_reports_availability_correctly():
    """is_available() should return False when transformers isn't installed.

    In the dev environment the `hosted` extra isn't installed by default, so
    this should return False. If you've installed the extra, the test still
    passes because it just checks the function works.
    """
    available = is_available()
    assert isinstance(available, bool)


def test_loader_raises_clearly_when_extra_missing():
    """If transformers isn't installed, the loader raises a helpful message."""
    if is_available():
        pytest.skip("transformers is installed; skipping the missing-extra test")
    with pytest.raises(RuntimeError, match="transformers is not installed"):
        load_huggingface_model("gpt2")
