# Quickstart

Two ways to use ASICify today: explore the design space in the browser, or
run the compiler from source on your machine.

## Playground (in browser, zero install)

The fastest way to get a feel for what ASICify does. The hardware estimator
runs entirely in your browser. No signup, no backend.

1. Open the [playground](/playground)
2. Pick a model (e.g. `GPT-2 Small`)
3. Drag quantization to INT4 and sparsity to 50%
4. Pick a target (e.g. `TSMC 28nm`)
5. Watch the silicon floorplan, area, and per-volume cost update live

Try ternary against TinyTapeout to see what an ultra-small implementation
looks like, or FP16 against TSMC 7nm to see the area cost of full
precision.

## CLI (from source)

The CLI lives in `apps/worker`. There is no PyPI package yet, so you run
it directly from a clone.

```bash
git clone https://github.com/claynicholson/asicify
cd asicify/apps/worker
uv sync
uv run asicify compile gpt2 \
    --quantization int4 \
    --sparsity 2:4 \
    --target tsmc28,ecp5 \
    --output ./build
```

This produces:

```
./build/gpt2.zip
```

Containing the RTL package (`top.v`, per-layer modules, weights,
testbench, synthesis scripts). Unzip and run:

```bash
unzip -d gpt2 ./build/gpt2.zip
cd gpt2
make sim          # cocotb + Verilator simulation
make synth-yosys  # ECP5 synthesis (requires yosys + nextpnr)
```

> **Note**: the compiler core (parsing, quantization, sparsity,
> decomposition, RTL generation, validation) is implemented end-to-end.
> See the [roadmap](/docs/roadmap) for what's shipped versus pending.

## REST API (not yet deployed)

The FastAPI backend in `apps/api` is fully implemented locally but has no
public deployment yet. To run it on your own machine:

```bash
docker compose -f infra/docker-compose.yml up -d   # Postgres + Redis + MinIO
cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
# OpenAPI docs at http://localhost:8000/docs
```

The endpoint surface is documented in
[docs/internals/api.md](/docs/internals/api). When the hosted version
goes live, this section will get a public base URL and an auth token
example.
