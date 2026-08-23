# asicify-worker

Heavy-compute backend for ASICify. Three responsibilities:

1. **Compression pipeline** — quantize, sparsify, decompose, validate quality.
2. **RTL generation** — emit synthesizable Verilog with hardwired weights, plus
   testbench, reference Python, and synthesis scripts.
3. **Hardware estimation** — area, throughput, energy, cost across targets.

## Run locally

```bash
uv sync
uv run python -m worker.main
```

The worker blocks on `BLPOP asicify:jobs` and dispatches by `job_type`:
`compress | rtl | estimate`.

## Layout

```
worker/
├── main.py              Entry point — Redis poller + dispatcher
├── cli.py               asicify compile / demo / estimate
├── modal_app.py         Modal deployment definition
├── types.py             ModelGraph IR, CompressionConfig
├── kernels/             Pure tensor work: quantize, pack, sparsity,
│                        decompose, layers, attention
├── pipeline/            Compression stages
│   ├── parse.py
│   ├── quantize.py
│   ├── sparsity.py
│   ├── decompose.py
│   ├── validate.py
│   └── orchestrator.py
├── loaders/             HuggingFace model loader (`hosted` extra)
├── rtl/
│   ├── generator.py     Jinja2 → Verilog package
│   └── templates/       *.v.j2, tb_top.py.j2, Makefile.j2, …
└── estimator/
    ├── area.py
    ├── throughput.py
    ├── cost.py
    ├── targets.py       Per-node cell library data
    └── runner.py
```

## Modal deployment

In production the worker runs on [Modal](https://modal.com). See
`worker/modal_app.py` for the app definition. One job = one container =
scales to zero when idle.
