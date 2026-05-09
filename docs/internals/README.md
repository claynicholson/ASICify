# Internals

Engineering documentation for ASICify contributors. If you're a user, you
want [docs/quickstart.md](../quickstart.md) and
[docs/architecture.md](../architecture.md) instead.

## Read these in order

1. [../codebase.md](../codebase.md) — High-level map. Mental model. Where
   each layer fits.
2. **Pick the area you're touching:**
   - [web.md](web.md) — Next.js frontend, playground, client estimator
   - [api.md](api.md) — FastAPI, auth, queue, WebSocket
   - [worker.md](worker.md) — Pipeline, RTL gen, hardware estimator
3. [data-flow.md](data-flow.md) — End-to-end traces of three real user
   actions, file by file.
4. [extending.md](extending.md) — Recipes: add a target, a quantization
   mode, an RTL primitive, a pipeline stage, etc.
5. [conventions.md](conventions.md) — Code style, naming, structure.
6. [glossary.md](glossary.md) — ML, silicon, EDA, and ASICify-specific
   vocabulary. Use as you read.

## When you change something

The hard sync points to remember:

- **`CompressionConfig` and friends** live in three files. Changing one
  requires changing all three. See [conventions.md#shared-types](conventions.md#shared-types--three-places-one-source-of-truth).
- **Cell library numbers** live in two places (TS estimator + Python
  estimator). See [codebase.md#the-estimator-lives-in-two-places](../codebase.md#the-estimator-lives-in-two-places--on-purpose).
- **Model catalog** lives in two places (web + api). See
  [extending.md#add-a-model-to-the-catalog](extending.md#add-a-model-to-the-catalog).
- **Hardware target list** lives in three places. See
  [extending.md#add-a-hardware-target](extending.md#add-a-hardware-target).

These are explicit duplications, not bugs. The discipline is that they move
together in the same commit.

## What's not yet documented

- **Modal deployment** — Worker isn't on Modal yet. When it goes live, add
  `modal-deployment.md` here.
- **Production deployment runbook** — Once Fly.io / Vercel / Neon are
  wired, add a `runbook.md`.
- **Performance tuning** — When we have real load, document the knobs.
- **PDF report generation** — When `@react-pdf/renderer` is wired, document
  the report layout templates.
- **WebGPU inference** — When `transformers.js` is integrated for the
  side-by-side comparison, document the model loading pipeline.

If you're working on any of these, please add docs in the same PR.
