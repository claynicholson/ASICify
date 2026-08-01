# Design

## Theme

Light "engineering document" base (a chip-team lead reading on a large monitor at their desk, deciding if the cost model is credible), with dark ink bands reserved for terminal output and the comparison table. Not a dark-mode site.

## Color

Strategy: Restrained-to-Committed. Porcelain neutrals tinted toward the copper hue; near-black warm ink; one copper accent (`oklch(0.60 0.18 40)`, descended from the fab-orange in the logomark) used decisively in figures, links, and active states.

Tokens live in `apps/web/app/globals.css` under `@theme`:

- `--color-bg-base` porcelain near-white, `--color-bg-elevated`, `--color-bg-overlay`
- `--color-bg-ink` warm near-black for dark bands and terminals
- `--color-accent` copper + hover/deep/muted variants
- Text scale `--color-text-primary/secondary/tertiary/on-ink`
- Border scale subtle/default/strong (hairlines everywhere)
- Chart series `--color-series-1..6`

Never `#000`/`#fff`. No gradients as decoration.

## Typography

- **Archivo** (variable, `wdth` axis) is the only text family. Display headings: weight 600-650, `font-stretch` 110-125%, tracking -0.02 to -0.04em. Body: 400/16-17px.
- **JetBrains Mono** strictly for data, code, labels, and figure annotations.
- No serif anywhere. Scale ratio >= 1.25 between steps.

## Datasheet grammar (the named system)

- Each landing section opens with a full-width hairline rule; on it sit a mono section index (`01`, `02`...) and the section title.
- Figures are real product artifacts (die floorplan SVG, terminal transcript) with mono captions in the form `FIG. N` + one factual sentence with real numbers.
- Dimension lines, pad rings, hatched ROM fills in figures follow EDA/datasheet drawing conventions.
- Micro-labels use `.label-mono` (11px mono, 0.14em tracking, uppercase). Used for data labeling only, never as decorative eyebrows over every heading.

## Components

- **Button**: 2px radius, precise. `ink` (near-black solid) is the primary CTA. `outline` hairline for secondary. Copper appears on hover/focus, not as the default fill.
- **Cards**: avoided. Spec content uses ruled definition lists and tables.
- **Terminal blocks**: dark ink bg, hairline border, mono header row with command context. No traffic-light dots.

## Motion

Essentially none. No entrance animations, no wobble, no shimmer on marketing surfaces. Hover/focus transitions 120-150ms ease-out only.

## Bans (project-specific)

Rotated elements, paper grain, hand-drawn ornaments, marker underlines, stamps, sticker shadows, icon-card grids, serif display type.
