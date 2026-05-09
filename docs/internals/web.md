# Frontend Internals — `apps/web`

Next.js 15 (App Router), React 19, Tailwind CSS v4, TypeScript strict.

## Directory map

```
apps/web/
├── app/                     Routes (App Router file-system convention)
│   ├── layout.tsx           Root <html>, font preload, metadata
│   ├── page.tsx             Landing
│   ├── globals.css          Tailwind v4 @theme tokens
│   ├── playground/page.tsx  The demo
│   ├── projects/page.tsx    Dashboard
│   ├── projects/[id]/page.tsx  Project detail
│   ├── docs/page.tsx        Docs index
│   ├── pricing/page.tsx     Pricing tiers
│   └── sign-in/page.tsx     Clerk sign-in stub
├── components/
│   ├── nav.tsx, footer.tsx          Shell
│   ├── ui/                          Primitives (button, card, metric)
│   ├── landing/                     Landing-page sections
│   └── playground/                  Three-column playground widgets
├── lib/
│   ├── api.ts               Fetch wrappers + WebSocket helper
│   ├── catalog.ts           Curated model list (mirrors api/data/catalog.py)
│   ├── estimator.ts         Client-side hardware estimator (the soul of /playground)
│   └── utils.ts             cn(), formatCompact, formatUSD, formatArea
├── next.config.ts           Rewrites /api/backend/* → backend
├── postcss.config.mjs       Tailwind v4 PostCSS plugin
└── tsconfig.json            Path aliases @/, @asicify/shared
```

## Routing

App Router conventions. Every page is a server component by default; client
components opt in via the `"use client"` directive. The two important client
pages are:

- `app/playground/page.tsx` — entirely client-side, drives the live estimator.
- `app/projects/[id]/page.tsx` — server-rendered shell, with a client island
  inside the future Verification tab.

Path aliases:

- `@/*` — anything inside `apps/web/`
- `@asicify/shared` — types from `packages/shared/src/index.ts`
- `@asicify/shared/targets` — target catalog

## Styling

Tailwind v4 with `@theme` design tokens defined in
[`app/globals.css`](../../apps/web/app/globals.css). The token names map 1:1
to the brand system in the spec:

```css
@theme {
  --color-bg-base: #0A0B0E;
  --color-bg-elevated: #14161B;
  --color-bg-overlay: #1C1F26;
  --color-border-subtle: #232730;
  --color-border-default: #2D323C;
  --color-text-primary: #F4F5F7;
  --color-text-secondary: #A0A6B1;
  --color-text-tertiary: #6B7280;
  --color-accent: #5B8FF9;
  /* … */
}
```

Components reference these via `var(--color-…)` rather than Tailwind
shorthand for two reasons: (1) the brand system tokens don't map cleanly to
the default Tailwind palette, and (2) it makes the dark theme single-source.

**Conventions:**

- Sharp corners with `rounded-[6px]`, never the default Tailwind radii.
- Hover = brightness shift, never color shift.
- Animations: 150–200ms `ease-out`. Anything slower feels sluggish in
  developer tools.
- No emoji, no celebratory confetti, no bouncy springs. Technical software.

## The component anatomy

### Primitives — `components/ui/`

Three primitives, all built on Radix where useful:

- **`button.tsx`** — `cva` variants (`primary`, `secondary`, `ghost`,
  `outline`, `danger`), three sizes. The `asChild` prop forwards to a Radix
  Slot so you can wrap a `<Link>` and keep the styles.
- **`card.tsx`** — `Card`, `CardHeader`, `CardTitle`, `CardDescription`,
  `CardContent`. Pure layout, no behavior.
- **`metric.tsx`** — The big numeric display used throughout the playground
  and project detail. Mono font for the value, uppercase tracked label,
  optional delta with semantic color.

These primitives are the only place where raw Tailwind utility classes
intermix with `var(--color-*)`. Higher-level components consume the
primitives instead of restyling from scratch.

### Landing page — `components/landing/`

Five sections, each a self-contained component invoked from
[`app/page.tsx`](../../apps/web/app/page.tsx) in order:

1. `hero.tsx` — H1 + two CTAs + four stats. Background grid via
   `.bg-grid` class in `globals.css`.
2. `how-it-works.tsx` — 3-step horizontal flow with Lucide icons. Uses a
   subtle 1px grid effect (border-collapse trick: `gap-px` over a tinted
   background).
3. `differentiators.tsx` — 3-card grid of pillar value props.
4. `use-cases.tsx` — Persona tabs. Client component — switches the visible
   panel without route changes.
5. `code-snippet.tsx` — Two-column layout with a fake terminal showing the
   CLI output. The "terminal chrome" (three dots + label) is a decorative
   div, not a real terminal embed.

When you add a section, follow this pattern: server component if static,
client only when state is needed. Each section file owns its data; landing
sections never import from `lib/`.

### Playground — `components/playground/`

This is the killer demo. Three columns:

- **Left** (`config-panel.tsx`) — model picker, quantization buttons,
  sparsity slider, decomposition radio, target dropdown, big Compile button.
  Stateless: receives `state` and `onChange` from the parent.
- **Middle** (`results-panel.tsx`) — live `Metric` cards driven by the
  `quickEstimate` output: quality (perplexity), size reduction, throughput,
  area, max clock, energy, cost at three volume tiers.
- **Right** (`floorplan.tsx` + `pareto-plot.tsx`) — silicon floorplan
  treemap and cost-vs-throughput Pareto scatter. Floorplan colors map to
  area-breakdown components; Pareto plot uses Recharts.

Plus `inference-comparison.tsx` for the side-by-side text generation preview.
This is a **stub** that picks from canned outputs by quantization level — the
real version uses transformers.js + WebGPU and is on the roadmap.

The state for the whole playground lives in
[`app/playground/page.tsx`](../../apps/web/app/playground/page.tsx) using
plain `useState`. No global store, no React Query — every config change
re-runs `quickEstimate` synchronously. With 1.1B-param models and the math in
`lib/estimator.ts`, this is sub-millisecond.

## The client-side estimator (the soul of /playground)

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
- `apps/web/lib/estimator.ts:25` (`NODE_PARAMS`)
- `apps/worker/worker/estimator/targets.py:23` (`ASIC_NODES`)

The math involves four functions of interest:

- `quickEstimate(input)` — top-level entry; returns `QuickEstimate`.
- `effectiveParams(params, config)` — applies sparsity + decomposition to
  shrink param count.
- `computeAsicCost(area_mm2, params)` — Murphy's yield + NRE amortization +
  margin to produce three volume-tier prices.
- `fpgaUnitCost(target)` — flat lookup for FPGAs.

The complexity-vs-accuracy tradeoff favors complexity here; the user *expects*
their tweaks to be reflected, even if rough.

## API client

[`lib/api.ts`](../../apps/web/lib/api.ts) is a small `fetch` wrapper with
auth bearer header and a `subscribeProgress(projectId, onEvent)` helper that
opens a WebSocket and dispatches typed `ProgressEvent` messages.

`request<T>(path, init)` is intentionally minimal — no React Query / SWR. The
hosted dashboard does need cache invalidation later; when that happens, wrap
this with TanStack Query rather than replacing.

## Catalog

[`lib/catalog.ts`](../../apps/web/lib/catalog.ts) duplicates
`apps/api/app/data/catalog.py`. The web copy is what the playground shows when
unauthenticated; the API copy is canonical and what the dashboard fetches.
**These must stay in sync.** When you add a model:

1. Add it in `apps/api/app/data/catalog.py:CATALOG`
2. Add a matching entry in `apps/web/lib/catalog.ts:MODEL_CATALOG`
3. Make sure `recommended_compression` matches across both

Yes, it's brittle. The future state is a build-time codegen step that emits
the TS file from the Python list. Until volume justifies that, keep the
discipline manual.

## State management — what we use, what we don't

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

The repo currently ships a sign-in **stub** at `app/sign-in/page.tsx`. The
real integration plan:

1. Wrap `app/layout.tsx`'s `<body>` children in `<ClerkProvider>`.
2. Replace the stub with `<SignIn />` from `@clerk/nextjs`.
3. Add a `middleware.ts` at `apps/web/middleware.ts` to protect `/projects`
   and `/projects/[id]`.
4. Forward the Clerk JWT in `lib/api.ts:request` via the existing `token`
   parameter.

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
- **No** component tests — components are presentational; if `lib/` is
  tested, components rarely break in isolation.

When you add a Vitest config: put it at `apps/web/vitest.config.ts`, add
`pnpm test` script, no jsdom (we're testing pure functions, not DOM).
