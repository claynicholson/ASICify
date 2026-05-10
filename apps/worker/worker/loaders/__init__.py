"""Model loaders.

Each loader takes a string identifier and returns a `(nn.Module, metadata)`
tuple suitable for `worker.pipeline.parse.parse_module`. The HF loader is in
the `hosted` extra because transformers + accelerate is heavy.
"""
