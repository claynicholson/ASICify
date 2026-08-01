/**
 * Annotated die floorplan for the hero figure.
 *
 * Drawn to datasheet conventions: pad ring, hatched ROM banks, dimension
 * lines with extension ticks. Block proportions follow the estimator's
 * actual area split for GPT-2 124M at INT4 + 2:4 on TSMC 28 (weight ROM
 * dominates a weight-hardwired design). Pure SVG, server-rendered.
 */

const DIE = { x: 100, y: 20, w: 400, h: 400 };
const CORE = { x: 140, y: 60, w: 320, h: 320 };

const PADS_PER_SIDE = 18;

function PadRing() {
  const pads: React.ReactNode[] = [];
  const inset = 12;
  const len = 16;
  const thick = 7;
  for (let i = 0; i < PADS_PER_SIDE; i++) {
    const t = (i + 0.5) / PADS_PER_SIDE;
    const xh = DIE.x + 24 + t * (DIE.w - 48) - thick / 2;
    const yv = DIE.y + 24 + t * (DIE.h - 48) - thick / 2;
    pads.push(
      <rect key={`t${i}`} x={xh} y={DIE.y + inset} width={thick} height={len} />,
      <rect key={`b${i}`} x={xh} y={DIE.y + DIE.h - inset - len} width={thick} height={len} />,
      <rect key={`l${i}`} x={DIE.x + inset} y={yv} width={len} height={thick} />,
      <rect key={`r${i}`} x={DIE.x + DIE.w - inset - len} y={yv} width={len} height={thick} />,
    );
  }
  return (
    <g
      fill="var(--color-bg-overlay)"
      stroke="var(--color-border-strong)"
      strokeWidth="0.75"
    >
      {pads}
    </g>
  );
}

function Block({
  x,
  y,
  w,
  h,
  label,
  sub,
  fill = "var(--color-bg-base)",
  accent = false,
  hatch = false,
}: {
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  sub?: string;
  fill?: string;
  accent?: boolean;
  hatch?: boolean;
}) {
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        fill={hatch ? "url(#fp-hatch)" : fill}
        stroke={accent ? "var(--color-accent)" : "var(--color-text-primary)"}
        strokeWidth={accent ? 1.25 : 0.9}
      />
      <text
        x={x + 8}
        y={y + 17}
        fontFamily="var(--font-mono)"
        fontSize="10"
        letterSpacing="0.08em"
        fill={accent ? "var(--color-accent-deep)" : "var(--color-text-primary)"}
      >
        {label}
      </text>
      {sub && (
        <text
          x={x + 8}
          y={y + 31}
          fontFamily="var(--font-mono)"
          fontSize="8.5"
          letterSpacing="0.05em"
          fill="var(--color-text-tertiary)"
        >
          {sub}
        </text>
      )}
    </g>
  );
}

/** Dimension line with arrowheads and extension ticks. */
function DimH({ x1, x2, y, label }: { x1: number; x2: number; y: number; label: string }) {
  return (
    <g stroke="var(--color-text-tertiary)" strokeWidth="0.8" fill="none">
      <line x1={x1} y1={y - 8} x2={x1} y2={y + 4} />
      <line x1={x2} y1={y - 8} x2={x2} y2={y + 4} />
      <line x1={x1} y1={y} x2={x2} y2={y} />
      <path d={`M ${x1} ${y} l 7 -2.6 v 5.2 z`} fill="var(--color-text-tertiary)" stroke="none" />
      <path d={`M ${x2} ${y} l -7 -2.6 v 5.2 z`} fill="var(--color-text-tertiary)" stroke="none" />
      <text
        x={(x1 + x2) / 2}
        y={y + 15}
        textAnchor="middle"
        fontFamily="var(--font-mono)"
        fontSize="10"
        letterSpacing="0.06em"
        fill="var(--color-text-secondary)"
        stroke="none"
      >
        {label}
      </text>
    </g>
  );
}

function DimV({ y1, y2, x, label }: { y1: number; y2: number; x: number; label: string }) {
  return (
    <g stroke="var(--color-text-tertiary)" strokeWidth="0.8" fill="none">
      <line x1={x - 4} y1={y1} x2={x + 8} y2={y1} />
      <line x1={x - 4} y1={y2} x2={x + 8} y2={y2} />
      <line x1={x} y1={y1} x2={x} y2={y2} />
      <path d={`M ${x} ${y1} l -2.6 7 h 5.2 z`} fill="var(--color-text-tertiary)" stroke="none" />
      <path d={`M ${x} ${y2} l -2.6 -7 h 5.2 z`} fill="var(--color-text-tertiary)" stroke="none" />
      <text
        x={x - 10}
        y={(y1 + y2) / 2}
        textAnchor="middle"
        fontFamily="var(--font-mono)"
        fontSize="10"
        letterSpacing="0.06em"
        fill="var(--color-text-secondary)"
        stroke="none"
        transform={`rotate(-90 ${x - 10} ${(y1 + y2) / 2})`}
      >
        {label}
      </text>
    </g>
  );
}

export function DieFloorplan({ className }: { className?: string }) {
  const romW = 172;
  const rightX = CORE.x + romW + 8;
  const rightW = CORE.x + CORE.w - rightX;

  return (
    <svg
      viewBox="0 0 560 452"
      className={className}
      role="img"
      aria-label="Annotated die floorplan of a GPT-2 accelerator on TSMC 28 nm: four hatched weight-ROM banks, a 32 by 32 MAC array, KV-cache SRAM, attention, layernorm, and sequencer blocks inside a pad ring. Die measures 2.86 by 2.86 millimeters."
    >
      <defs>
        <pattern
          id="fp-hatch"
          width="6"
          height="6"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <rect width="6" height="6" fill="var(--color-bg-base)" />
          <line x1="0" y1="0" x2="0" y2="6" stroke="var(--color-border-default)" strokeWidth="1.1" />
        </pattern>
      </defs>

      {/* Die outline + seal ring */}
      <rect
        x={DIE.x}
        y={DIE.y}
        width={DIE.w}
        height={DIE.h}
        fill="var(--color-bg-elevated)"
        stroke="var(--color-text-primary)"
        strokeWidth="1.4"
      />
      <rect
        x={DIE.x + 6}
        y={DIE.y + 6}
        width={DIE.w - 12}
        height={DIE.h - 12}
        fill="none"
        stroke="var(--color-border-default)"
        strokeWidth="0.75"
      />

      <PadRing />

      {/* ROM banks: the dominant area in a weight-hardwired design */}
      {[0, 1, 2, 3].map((i) => (
        <Block
          key={i}
          x={CORE.x}
          y={CORE.y + i * 80}
          w={romW}
          h={i === 3 ? 80 : 76}
          label={`WEIGHT ROM ${i}`}
          sub={i === 0 ? "int4 · 2:4 sparse" : undefined}
          hatch
        />
      ))}

      {/* Compute + memory blocks */}
      <Block
        x={rightX}
        y={CORE.y}
        w={rightW}
        h={132}
        label="MAC ARRAY"
        sub="32×32 · CSD shift-add"
        fill="var(--color-accent-muted)"
        accent
      />
      <Block x={rightX} y={CORE.y + 136} w={rightW} h={84} label="KV SRAM" sub="256 KB" />
      <Block x={rightX} y={CORE.y + 224} w={68} h={96} label="ATTN" />
      <Block x={rightX + 72} y={CORE.y + 224} w={rightW - 72} h={46} label="LNORM" />
      <Block x={rightX + 72} y={CORE.y + 274} w={rightW - 72} h={46} label="SEQ" />

      {/* Dimension lines */}
      <DimV x={DIE.x - 22} y1={DIE.y} y2={DIE.y + DIE.h} label="2.86 mm" />
      <DimH y={DIE.y + DIE.h + 22} x1={DIE.x} x2={DIE.x + DIE.w} label="2.86 mm" />

      {/* Corner marker: A1 pad reference, like a package drawing */}
      <circle
        cx={DIE.x + 24}
        cy={DIE.y + 24}
        r="3"
        fill="var(--color-accent)"
      />
      <text
        x={DIE.x + DIE.w}
        y={DIE.y - 8}
        textAnchor="end"
        fontFamily="var(--font-mono)"
        fontSize="10"
        letterSpacing="0.1em"
        fill="var(--color-text-tertiary)"
      >
        TSMC 28 · 8.2 mm²
      </text>
    </svg>
  );
}
