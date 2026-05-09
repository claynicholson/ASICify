# Quickstart

Compile your first model to RTL in 5 minutes.

## Hosted

1. Visit [asicify.com/playground](https://asicify.com/playground)
2. Pick a model (e.g. `gpt2-small`)
3. Slide quantization to INT4, sparsity to 50%
4. Pick a target (e.g. TSMC 28nm)
5. Hit **Compile** — full RTL package downloads as a zip

## CLI

```bash
pip install asicify
asicify compile gpt2 \
    --quantization int4 \
    --sparsity 2:4 \
    --target tsmc28,ecp5 \
    --output ./build
```

This produces:

```
./build/gpt2.zip
```

Containing the full RTL package (`top.v`, per-layer modules, weights,
testbench, synthesis scripts). Unzip and run:

```bash
unzip -d gpt2 ./build/gpt2.zip
cd gpt2
make sim          # cocotb + Verilator simulation
make synth-yosys  # ECP5 synthesis
```

## API

```bash
curl -X POST https://api.asicify.com/api/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "gpt2 on tsmc28",
    "model_source": {"type": "huggingface", "id": "gpt2"},
    "compression": {
      "quantization": "int4",
      "sparsity": {"type": "structured_2_4", "ratio": 0.5},
      "decomposition": {"type": "none"}
    },
    "targets": ["tsmc28", "ecp5"]
  }'
```

Then `POST /api/projects/{id}/compress` to start the job. Stream progress via
the WebSocket at `wss://api.asicify.com/api/projects/{id}/progress`.
