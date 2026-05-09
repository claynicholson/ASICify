"""Stage 1: Model parsing.

Use torch.fx to symbolically trace the model into a compute graph, detect layer
types, extract parameter shapes and dataflow dependencies.

For the MVP this returns a synthesized ModelGraph from HuggingFace metadata when
the actual model isn't loaded — enough to drive the rest of the pipeline.
"""

from __future__ import annotations

from worker.types import LayerInfo, ModelGraph

# Heuristic: synthesize a transformer-style graph from declared parameter count.
# Replace with real torch.fx tracing when models are loaded.

def synthesize_transformer(
    name: str, total_params: int, hidden: int = 768, layers: int = 12
) -> ModelGraph:
    layer_list: list[LayerInfo] = []
    layer_list.append(
        LayerInfo(
            name="embed",
            kind="embedding",
            in_features=50_257,
            out_features=hidden,
            param_count=50_257 * hidden,
        )
    )
    per_block_params = (total_params - layer_list[0].param_count) // max(layers, 1)
    for i in range(layers):
        layer_list.append(
            LayerInfo(
                name=f"block_{i}.attn",
                kind="attention",
                in_features=hidden,
                out_features=hidden,
                param_count=per_block_params // 4,
            )
        )
        layer_list.append(
            LayerInfo(
                name=f"block_{i}.ffn",
                kind="ffn",
                in_features=hidden,
                out_features=4 * hidden,
                param_count=per_block_params // 2,
            )
        )
        layer_list.append(
            LayerInfo(
                name=f"block_{i}.ln",
                kind="layernorm",
                in_features=hidden,
                out_features=hidden,
                param_count=2 * hidden,
            )
        )
    return ModelGraph(
        name=name,
        task="language_modeling",
        layers=layer_list,
        total_params=total_params,
        metadata={"hidden": hidden, "n_layers": layers, "synthesized": True},
    )


def parse_model(model_source: dict) -> ModelGraph:
    """Parse a model from its declared source (huggingface ID or upload key).

    The full implementation:
        from transformers import AutoModel
        model = AutoModel.from_pretrained(model_source['id'])
        graph = torch.fx.symbolic_trace(model)
        ... walk graph.graph.nodes, extract layer info ...

    The stub below covers the common transformer case and is enough for the
    rest of the pipeline to produce realistic numbers in tests.
    """
    name = model_source.get("id", "unknown")
    # Map known catalog IDs to parameter counts; fall back to 100M.
    KNOWN: dict[str, int] = {
        "gpt2": 124_000_000,
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0": 1_100_000_000,
        "distilbert-base-uncased": 66_000_000,
        "google/mobilebert-uncased": 25_000_000,
    }
    params = KNOWN.get(name, 100_000_000)
    return synthesize_transformer(name, params)
