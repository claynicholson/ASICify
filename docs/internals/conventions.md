# Conventions

Naming, formatting, structure. The rules we hold ourselves to.

When the codebase is consistent, you can read unfamiliar parts of it as
fast as the parts you wrote. Inconsistency taxes every future
contributor.

## Languages and tools

| Where         | Language          | Linter        | Formatter     | Type checker |
| ------------- | ----------------- | ------------- | ------------- | ------------ |
| apps/web      | TypeScript strict | Next ESLint   | Prettier      | tsc          |
| apps/api      | Python 3.11+      | Ruff          | Ruff format   | mypy         |
| apps/worker   | Python 3.11+      | Ruff          | Ruff format   | mypy         |
| packages/shared | TypeScript      | (none yet)    | Prettier      | tsc          |
| Verilog       | SystemVerilog-ish | (verilator lint) | (none)     | (verilator)  |
| Jinja2 templates | n/a            | (none)        | (manual)      | StrictUndefined |

Run before pushing:

```bash
pnpm lint && pnpm typecheck
```

## File names

- **TypeScript components**: `kebab-case.tsx`. The component name inside is
  PascalCase (`HowItWorks`, `ParetoPlot`).
- **TypeScript libraries / utilities**: `kebab-case.ts`.
- **Python modules**: `snake_case.py`.
- **Jinja2 templates**: `<output_filename>.j2`. e.g. `linear_layer.v.j2`
  renders to `linear_layer.v`. The double extension makes the relationship
  obvious.

Avoid `index.ts` barrel files except where they match a runtime entry
point convention (e.g. `packages/shared/src/index.ts`). Barrel files cost
build time and make import graphs harder to read.

## Module imports

### Python

Order:

```python
# 1. Future imports
from __future__ import annotations

# 2. Stdlib
import asyncio
import json
from pathlib import Path

# 3. Third-party
import structlog
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

# 4. First-party (this app)
from app.config import get_settings
from app.models import Project
```

Ruff's `I` rule enforces this. **No relative imports.** Always use the
package root (`app.` or `worker.`).

Cross-app imports are forbidden:

- `apps/api` may not `from worker import …`
- `apps/worker` may not `from app import …`

If you find yourself wanting to, you're probably reaching for shared types.
Add them to the type files (see "Shared types" below).

### TypeScript

Order:

```ts
// 1. External
import * as React from "react";
import { motion } from "framer-motion";

// 2. Aliased (workspace package or @/ alias)
import type { CompressionConfig } from "@asicify/shared";
import { Button } from "@/components/ui/button";

// 3. Relative
import { ConfigPanel } from "./config-panel";
```

Avoid relative imports like `../../components/ui/button`. Use `@/` instead.

## Shared types: three places, one source of truth

The `CompressionConfig`, `Quantization`, etc. live in three files:

- TypeScript: `packages/shared/src/types.ts` (**canonical**)
- Pydantic: `apps/api/app/schemas.py`
- Dataclass: `apps/worker/worker/types.py`

Rule: **change TypeScript first**, then propagate. Code-review checklist
includes "did all three move together?". The duplication is annoying but
honest: it's the price of not having Python-TS interop tooling, and it
forces you to think about wire formats.

When sync drifts, the Pydantic schema is what actually validates the wire,
so the API will reject malformed payloads. That's a feature.

## Type annotations

### Python

- All function signatures fully annotated. `def foo(x: int) -> str: …`.
- `from __future__ import annotations` at the top of every module so we
  can use modern syntax (`list[X]`, `X | None`) on Python 3.10+.
- `mapped_column[T]` for SQLAlchemy ORM columns.
- Pydantic for any data that crosses a process boundary; dataclasses for
  internal IR.
- Use `Literal[...]` for closed string sets, not `str`. Compilers help.

### TypeScript

- `strict: true`. No `any` without a comment justifying it.
- `interface` for object shapes, `type` for unions and aliases.
- Prefer `unknown` over `any` when you really don't know.
- Don't use `React.FC`; write the prop type and use a function declaration:

```ts
function Hero({ title }: { title: string }) { … }
// or with a named props type
interface HeroProps { title: string }
function Hero({ title }: HeroProps) { … }
```

## Comments

The default is **no comment**. Code should be readable; names should carry
intent.

Comment when:

- The *why* isn't obvious. ("This 1.5× routing overhead is empirical for
  digital-only designs; mixed-signal needs more.")
- A surprising constraint exists. ("Ordering matters here: Job row must
  exist before the worker can BLPOP.")
- A spec or paper is the source of truth. Cite it.
- A decision was costly to make and is non-obvious. ("Using JSON instead
  of normalized columns because shapes change weekly during MVP.")

Don't comment when:

- The function name says it. (`def get_user_by_id(...)`)
- The code is self-evident.
- You're tempted to write `# TODO: improve this`. Open an issue instead, or
  delete the line.

## Comment markers

We use exactly three markers. Avoid inventing new ones:

| Marker  | Meaning                                              |
| ------- | ---------------------------------------------------- |
| `TODO`  | This is incomplete; will be addressed soon.          |
| `NOTE`  | Important context for the reader.                    |
| `HACK`  | This is wrong but expedient. Track in an issue.      |

No `FIXME` (use `TODO` or `HACK`), no `XXX` (no one knows what it means).

## Logging

Python: `structlog`. Always pass keyword args, never f-string the message:

```python
log.info("job.start", job_id=job_id, type=job_type)  # YES
log.info(f"starting job {job_id}")                   # NO
```

The structured form survives JSON output, log shipping, and search.

Event names are dotted: `<area>.<verb>` like `worker.start`,
`job.failed`, `api.startup`. Keep them stable; dashboards and alerts
key off them.

TypeScript: `console.error` for errors, `console.warn` sparingly. We don't
have a structured logger client-side; if we add one (Sentry breadcrumbs),
update this section.

## Error handling

### Python

- Catch the narrowest exception you can. `except ValueError`, not
  `except Exception` (let alone bare `except`).
- Re-raise with `from e` to preserve the chain.
- Don't catch and log unless you can recover. If you can't, let it propagate
  to the framework boundary.
- `HTTPException` for known API error responses.

### TypeScript

- `throw new Error("…")` with descriptive messages.
- `try`/`catch` only at boundaries (API calls, dynamic imports). Inside
  pure logic, exceptions are bugs.
- Don't return `null | T` when `T | undefined` makes more sense for
  optionality. Pick one and be consistent within a module.

## Naming

### General

- Be specific. `users` is fine; `things` is not. `parsed_graph` beats
  `result`.
- Avoid Hungarian notation (`strName`, `iCount`). Types live in the type
  system.
- Constants are `SCREAMING_SNAKE_CASE` in both languages.

### Domain-specific

- Hardware targets: lowercase ids (`tsmc28`, `gf22fdx`, `ecp5`). Display
  names live in the catalogs.
- Quantization modes: lowercase (`int4`, `ternary`).
- Stage names in progress events: snake_case (`quantization`,
  `rtl_generation`).

## React component patterns

- Server components by default. Client components only when state, refs, or
  browser APIs are needed.
- One component per file (with helper components below it OK).
- Named exports for components. `export function Hero()` not
  `export default function`. Exception: Next.js page files require a
  default export.
- Props destructured at the function signature, not inside the body.
- Avoid `useEffect` for derivations. Compute in render or use `useMemo`.
- Don't fetch in `useEffect`; use server components or React Query.

## State management

| State scope                      | Use                                       |
| -------------------------------- | ----------------------------------------- |
| One component                    | `useState`                                |
| Closely-coupled component tree   | Lift to common parent + props             |
| URL-shareable                    | Search params (`useSearchParams`)         |
| Cross-route, server-fetched      | TanStack Query (when wired) or RSC fetch  |
| Truly global UI state (modals)   | Zustand (one store, ~50 lines)            |

We deliberately don't have Redux or Recoil. The complexity isn't justified
yet.

## Database conventions

- Tables: plural snake_case (`projects`, `artifacts`).
- Primary keys: `id`, UUID.
- Foreign keys: `<table>_id`. Always with `ondelete="CASCADE"` unless you
  have a reason otherwise.
- Timestamps: `created_at`, `updated_at`. UTC. SQLAlchemy `default=` is
  set on the model so unit tests work without DB defaults.
- JSON columns are fine for shapes that vary or evolve. Don't normalize
  prematurely.
- Indexes on every FK and every status field we filter on.

Migrations:

```bash
uv run alembic revision --autogenerate -m "what changed"
# Review the generated file. Hand-tune as needed.
uv run alembic upgrade head
```

Never edit a migration that's already been deployed. Make a new one.

## API design

- REST first. WebSocket where streams genuinely matter (progress).
- Plural resource names: `/api/projects`, not `/api/project`.
- Verbs as sub-routes for actions: `/api/projects/{id}/compress`.
- 2xx for success, 4xx for client error, 5xx for server error. Use
  `HTTPException`'s `status_code` argument; don't return your own status
  via response classes.
- `204 No Content` for deletes. Don't return the deleted resource.
- Pagination, when added, will use `?cursor=…&limit=…`. Don't reinvent it
  per route.

## Verilog conventions

- `\`default_nettype none` at the top of every file. `wire` at the bottom.
- Active-low reset everywhere: `rst_n`. Synchronous deassertion.
- Standard handshake: `valid` / `ready` pair, `data` payload. Apply this
  uniformly across modules.
- Module names match file names. `module foo (...)` lives in `foo.v`.
- Parameters: `SCREAMING_SNAKE_CASE`. Signals: `snake_case`.
- No `wire reg`. No `wand`/`wor`. Pure structural / sequential.
- Always block style:
  ```verilog
  always @(posedge clk or negedge rst_n) begin
      if (!rst_n) ...
      else ...
  end
  ```
- Generated files include a header comment: `// ASICify generated …` plus
  config summary.

## Jinja2 conventions

- `StrictUndefined` mode. Templates fail loudly on undefined names.
- `trim_blocks=True, lstrip_blocks=True` so generated code is human-readable.
- No filters beyond `replace`. If you need logic, do it in `generator.py`.
- Templates live in `apps/worker/worker/rtl/templates/<name>.<output_ext>.j2`.

## Git conventions

- Branch names: `<area>/<short-slug>`. Examples: `web/playground-tooltip`,
  `worker/fp4-quantization`, `docs/cell-library-citations`.
- Commit messages: `<area>: <imperative summary>`. Body explains why.
- One concept per PR. If you can't summarize the PR in one sentence, split
  it.
- Squash on merge. Linear history.

## When in doubt

Match the code that's already there. If the existing code is wrong by these
conventions, fix it in a separate, narrow PR. Don't quietly diverge.

If you genuinely think a convention is wrong, open an issue with the
proposed change. The convention shifts when there's a better answer; until
then, follow it.
