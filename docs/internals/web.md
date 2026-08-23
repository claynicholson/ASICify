# Frontend Internals: `apps/web`

Next.js 15 (App Router), React 19, Tailwind CSS v4, TypeScript strict.

## Directory map

```
apps/web/
├── app/                     Routes (App Router file-system convention)
│   ├── layout.tsx           Root <html>, font preload, metadata
│   ├── page.tsx             Landing
│   ├── globals.css          Tailwind v4 @theme tokens
│   ├── playground/page.tsx  The live demo
│   ├── docs/                Markdown docs site ([...slug] renders /docs/*)
│   ├── about/page.tsx       About
│   └── api/report/          PDF report generation route
├── components/
│   ├── nav.tsx, footer.tsx          Shell
│   ├── ui/                          Primitives (button, card, metric)
│   ├── landing/                     Landing-page sections
│   └── playground/                  Playground widgets
├── lib/
│   ├── catalog.ts           Curated model list (mirrors api/data/catalog.py)
│   ├── estimator.ts         Client-side hardware estimator
│   ├── docs.ts              Markdown loading for the /docs routes
│   ├── report.tsx           @react-pdf/renderer document for /api/report
│   └── utils.ts             cn(), formatCompact, formatUSD, formatArea
├── next.config.ts           Standalone output for the Docker image
├── postcss.config.mjs       Tailwind v4 PostCSS plugin
└── tsconfig.json            Path aliases @/, @asicify/shared
```

## Routing

App Router conventions. Every page is a server component by default; client
components opt in via the `"use client"` directive. The two pages that
matter most:

- `app/playground/page.tsx`: entirely client-side, drives the live estimator.
- `app/docs/[...slug]/page.tsx`: server component that reads markdown from
  the repo's `docs/` directory at request time via `lib/docs.ts`.

There is no hosted dashboard (projects, sign-in) in the tree yet; those
pages arrive with the public API deployment.

Path aliases:

- `@/*`: anything inside `apps/web/`
- `@asicify/shared`: types from `packages/shared/src/index.ts`
- `@asicify/shared/targets`: target catalog

## Styling

Tailwind v4 with `@theme` design tokens defined in
[`app/globals.css`](../../apps/web/app/globals.css). The design system is
the "engineering datasheet" look documented in [DESIGN.md](../../DESIGN.md):
porcelain near-white paper, warm ink, one copper accent, hairline rules.

```css
@theme {
  --color-bg-base: oklch(0.972 0.0045 78);   /* porcelain */
  --color-bg-ink: oklch(0.215 0.012 55);     /* warm near-black bands */
  --color-text-primary: oklch(0.22 0.014 55);
  --color-accent: oklch(0.60 0.18 40);       /* fab copper */
  /* … */
}
```

Components reference these via `var(--color-…)` rather than Tailwind
shorthand: the brand tokens don't map cleanly to the default Tailwind
palette, and it keeps the palette single-source.

**Conventions** (full version in [DESIGN.md](../../DESIGN.md)):

- Hairline borders everywhere; small radii (2px on buttons), never the
  default Tailwind radii.
- Copper appears on hover/focus and in figures, never as wallpaper.
- Essentially no motion: hover/focus transitions 120–150ms `ease-out` only.
- No emoji, no gradients as decoration. Technical software.

## The component anatomy

### Primitives: `components/ui/`

Three primitives, all built on Radix where useful:

- **`button.tsx`**: `cva` variants (`primary`, `secondary`, `ghost`,
  `outline`, `danger`), three sizes. The `asChild` prop forwards to a Radix
  Slot so you can wrap a `<Link>` and keep the styles.
- **`card.tsx`**: `Card`, `CardHeader`, `CardTitle`, `CardDescription`,
  `CardContent`. Pure layout, no behavior.
- **`metric.tsx`**: The big numeric display used throughout the playground.
  Mono font for the value, uppercase tracked label, optional delta with
  semantic color.

These primitives are the only place where raw Tailwind utility classes
intermix with `var(--color-*)`. Higher-level components consume the
primitives instead of restyling from scratch.

### Landing page: `components/landing/`

Five sections, each a self-contained component invoked from
[`app/page.tsx`](../../apps/web/app/page.tsx) in order:

1. `hero.tsx`: headline + CTAs, with the die-floorplan figure
   (`die-floorplan.tsx`) as the hero artifact.
2. `how-it-works.tsx`: the model-to-silicon flow.
3. `differentiators.tsx`: pillar value props as ruled definition lists.
4. `vs-closed-silicon.tsx`: comparison table against the closed-EDA
   status quo (dark ink band).
5. `code-snippet.tsx`: terminal transcript of the CLI output (dark ink
   band, no fake traffic-light dots).

Shared: `section-header.tsx` renders the hairline rule + mono section
index (`01`, `02`, …) that opens every section.

When you add a section, follow this pattern: server component if static,
client only when state is needed. Each section file owns its data; landing
sections never import from `lib/`.

### Playground: `components/playground/`

Three columns:

- **Left** (`config-panel.tsx`): model picker, quantization buttons,
  sparsity slider, decomposition radio, target dropdown, big Compile button.
  Stateless: receives `state` and `onChange` from the parent.
- **Middle** (`results-panel.tsx`): live `Metric` cards driven by the
  `quickEstimate` output: quality (perplexity), size reduction, throughput,
  area, max clock, energy, cost at three volume tiers.
- **Right** (`floorplan.tsx` + `pareto-plot.tsx`): silicon floorplan
  treemap and cost-vs-throughput Pareto scatter. Floorplan colors map to
  area-breakdown components; Pareto plot uses Recharts.

Plus two inference previews: `inference-comparison.tsx` is a canned
side-by-side text sample keyed by quantization level, and
`webgpu-inference.tsx` runs real in-browser inference via
`@huggingface/transformers` (WebGPU with WASM fallback, DistilGPT-2 by
default, ~80MB cached after first load).

The state for the whole playground lives in
[`app/playground/page.tsx`](../../apps/web/app/playground/page.tsx) using
plain `useState`. No global store, no React Query: every config change
re-runs `quickEstimate` synchronously. With 1.1B-param models and the math in
`lib/estimator.ts`, this is sub-millisecond.

## The client-side estimator

[`lib/estimator.ts`](../../apps/web/lib/estimator.ts) is a pure TypeScript
function `quickEstimate(input)` returning a `QuickEstimate`. It does the same
job as `apps/worker/worker/estimator/runner.py:estimate` but with simplified
math, all in the browser.

Why duplicate it? Three reasons:

1. The playground needs to update as fast as a user can drag a slider. Round
   trips to the API are too slow.
2. The playground works without auth or a backend. We get search-engine
   indexable demos for free.
3. The two estimators serve as a cross-check. If they disagree by > 30%,
   one is wrong.

**When you change cell library numbers**, change them in both:
- `apps/web/lib/estimator.ts` (`NODE_PARAMS`)
- `apps/worker/worker/estimator/targets.py` (`ASIC_NODES`)

The math involves four functions of interest:

- `quickEstimate(input)`: top-level entry; returns `QuickEstimate`.
- `effectiveParams(params, config)`: applies sparsity + decomposition to
  shrink param count.
- `computeAsicCost(area_mm2, params)`: Murphy's yield + NRE amortization +
  margin to produce three volume-tier prices.
- `fpgaUnitCost(target)`: flat lookup for FPGAs.

The complexity-vs-accuracy tradeoff favors complexity here; the user *expects*
their tweaks to be reflected, even if rough.

## API client

There is no `lib/api.ts` yet; the playground talks to its own in-browser
estimator until the hosted API ships. When it does, the plan is a small
`fetch` wrapper with an auth bearer header plus a
`subscribeProgress(projectId, onEvent)` WebSocket helper — deliberately
minimal, wrapped with TanStack Query later if the dashboard needs cache
invalidation.

## Catalog

[`lib/catalog.ts`](../../apps/web/lib/catalog.ts) duplicates
`apps/api/app/data/catalog.py`. The web copy is what the playground shows when
unauthenticated; the API copy is canonical and what the dashboard fetches.
**These must stay in sync.** When you add a model:

1. Add it in `apps/api/app/data/catalog.py:CATALOG`
2. Add a matching entry in `apps/web/lib/catalog.ts:MODEL_CATALOG`
3. Make sure `recommended_compression` matches across both

This duplication is brittle. The future state is a build-time codegen step
that emits the TS file from the Python list. Until volume justifies that,
keep the discipline manual.

## State management: what we use, what we don't

| Used                | Not used                                          |
| ------------------- | ------------------------------------------------- |
| `useState`          | Redux, MobX                                       |
| Server components   | useReducer for complex state (we don't have any)  |
| URL params          | Page-level Suspense (yet)                         |
| `Set`s + `Map`s     | Immer                                             |

The playground deliberately keeps state local. The dashboard will need
TanStack Query when project lists get large, but starting that early would be
premature.

## Auth integration

There is no sign-in UI in the tree yet. The integration plan, when the
hosted dashboard lands:

1. Wrap `app/layout.tsx`'s `<body>` children in `<ClerkProvider>`.
2. Add a sign-in page using `<SignIn />` from `@clerk/nextjs`.
3. Add `apps/web/middleware.ts` to protect the `/projects` routes.
4. Forward the Clerk JWT in the (future) `lib/api.ts` request wrapper.

`@clerk/nextjs` is already in `package.json:dependencies`. We didn't wire it
because development without a Clerk account would hit a wall; the API has a
dev-mode fallback (`X-Dev-User-Id` header).

## Build + dev workflow

```bash
pnpm dev        # turbo runs all apps in parallel
pnpm --filter @asicify/web dev   # web only
pnpm --filter @asicify/web build # production build
pnpm --filter @asicify/web typecheck
```

The `next.config.ts` `transpilePackages: ["@asicify/shared"]` is what makes
the workspace types import cleanly without a separate build step on shared.

## Testing strategy (planned, not yet wired)

- **Vitest** for `lib/` pure functions (estimator math, catalog lookups,
  formatters). High value, low cost.
- **Playwright** for the playground E2E. Verifies that moving sliders updates
  numbers within frame budgets.
- **No** component tests: components are presentational; if `lib/` is
  tested, components rarely break in isolation.

When you add a Vitest config: put it at `apps/web/vitest.config.ts`, add
`pnpm test` script, no jsdom (we're testing pure functions, not DOM).
