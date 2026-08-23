# Internals

Engineering documentation for ASICify contributors. If you're a user, you
want [docs/quickstart.md](../quickstart.md) and
[docs/architecture.md](../architecture.md) instead.

## Read these in order

1. [../codebase.md](../codebase.md): high-level map and mental model.
2. **Pick the area you're touching:**
   - [web.md](web.md): Next.js frontend, playground, client estimator,
     PDF reports, WebGPU inference
   - [api.md](api.md): FastAPI, auth, queue, WebSocket
   - [worker.md](worker.md): high-level worker tour
3. **Worker deep dives:**
   - [kernels.md](kernels.md): the kernel modules (quantize, pack,
     sparsity, layers, attention). The bit-exactness contract lives here.
   - [rtl-templates.md](rtl-templates.md): the Verilog templates, what
     each generates, what variables it expects, how to extend it.
   - [testing.md](testing.md): test layout, what each suite proves, how
     to add new tests.
4. [data-flow.md](data-flow.md): end-to-end traces of three real
   user actions, file by file.
5. [extending.md](extending.md): recipes to add a precision, a sparsity
   pattern, a target, a layer kind, an HF attention naming scheme, a CLI
   subcommand, a DB table, a catalog entry.
6. [deployment.md](deployment.md): production deploy runbook for web,
   API, worker, plus CI.
7. [conventions.md](conventions.md): code style, naming, structure.
8. [glossary.md](glossary.md): ML, silicon, EDA, ASICify-specific terms.

## When you change something

The hard sync points to remember:

- **`CompressionConfig` and friends** live in three files (TS, Pydantic,
  dataclass). Changing one requires changing all three. See
  [conventions.md](conventions.md#shared-types-three-places-one-source-of-truth).
- **Cell library numbers** live in two places (TS estimator + Python
  estimator). See [codebase.md](../codebase.md#the-estimator-lives-in-two-places-on-purpose).
- **Model catalog** lives in two places (web + api). See
  [extending.md](extending.md#add-a-model-to-the-catalog).
- **Hardware target list** lives in three places. See
  [extending.md](extending.md#add-a-hardware-target).
- **Kernel forward and reference template** must implement the same
  arithmetic. See [kernels.md](kernels.md#the-bit-exactness-contract).

These are explicit duplications, not bugs. The discipline is that they
move together in the same commit.

## Pick the right deep dive

| You're working on... | Read |
|---------------------|------|
| The compiler core (kernels, math) | [kernels.md](kernels.md) |
| Verilog generation (templates) | [rtl-templates.md](rtl-templates.md) |
| Tests | [testing.md](testing.md) |
| Frontend (Next.js, playground, PDF, WebGPU) | [web.md](web.md) |
| API endpoints, auth, queue | [api.md](api.md) |
| Production deploys | [deployment.md](deployment.md) |
| Adding a new feature | [extending.md](extending.md) |
| End-to-end request lifecycle | [data-flow.md](data-flow.md) |
| Code style questions | [conventions.md](conventions.md) |
| Terminology you don't know | [glossary.md](glossary.md) |

## What's not yet documented

- **Hardware-aware fine-tuning**: not yet started; see
  [../roadmap.md](../roadmap.md).
- **Multi-token attention / KV-cache rotation**: the single-token path
  is documented in [rtl-templates.md](rtl-templates.md); the rotation
  work is pending.

If you're working on any of these, please add docs in the same PR.
