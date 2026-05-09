"""Curated model catalog. Mirrors apps/web/lib/catalog.ts."""

from app.schemas import (
    CatalogModel,
    CompressionConfig,
    DecompositionConfig,
    SparsityConfig,
)


def _cfg(quant, sparsity_type="none", sparsity_ratio=0.0, decomp="none") -> CompressionConfig:
    return CompressionConfig(
        quantization=quant,
        sparsity=SparsityConfig(type=sparsity_type, ratio=sparsity_ratio),
        decomposition=DecompositionConfig(type=decomp),
        fine_tune=False,
        fine_tune_steps=1000,
    )


CATALOG: list[CatalogModel] = [
    CatalogModel(
        id="tinyllama-1.1b",
        hf_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        display_name="TinyLlama 1.1B Chat",
        family="Llama",
        task="language_modeling",
        parameters=1_100_000_000,
        recommended_compression=_cfg("int4", "structured_2_4", 0.5),
    ),
    CatalogModel(
        id="gpt2-small",
        hf_id="gpt2",
        display_name="GPT-2 Small (124M)",
        family="GPT",
        task="language_modeling",
        parameters=124_000_000,
        recommended_compression=_cfg("int4"),
    ),
    CatalogModel(
        id="distilbert-base",
        hf_id="distilbert-base-uncased",
        display_name="DistilBERT Base",
        family="BERT",
        task="language_modeling",
        parameters=66_000_000,
        recommended_compression=_cfg("int8", "structured_2_4", 0.5),
    ),
    CatalogModel(
        id="mobilebert",
        hf_id="google/mobilebert-uncased",
        display_name="MobileBERT",
        family="BERT",
        task="language_modeling",
        parameters=25_000_000,
        recommended_compression=_cfg("int8"),
    ),
    CatalogModel(
        id="resnet18",
        hf_id="microsoft/resnet-18",
        display_name="ResNet-18",
        family="ResNet",
        task="classification",
        parameters=11_700_000,
        recommended_compression=_cfg("int8"),
    ),
    CatalogModel(
        id="mobilenet-v3",
        hf_id="google/mobilenet_v3_small_1.0_224",
        display_name="MobileNet V3 Small",
        family="MobileNet",
        task="classification",
        parameters=2_500_000,
        recommended_compression=_cfg("int4"),
    ),
    CatalogModel(
        id="whisper-tiny",
        hf_id="openai/whisper-tiny",
        display_name="Whisper Tiny",
        family="Whisper",
        task="speech",
        parameters=39_000_000,
        recommended_compression=_cfg("int8"),
    ),
]
