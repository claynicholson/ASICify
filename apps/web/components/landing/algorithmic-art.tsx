/**
 * Abstract algorithmic art.
 *
 * "Lithographic Subdivision": a recursive binary-space partitioning of a
 * rectangle. Each leaf cell is filled from a tight vocabulary (paper, ink,
 * accent, halftone dots, ruled lines) chosen by a weighted seeded RNG.
 * Renders identically on server and client, so no hydration drift.
 */

type Fill = "paper" | "ink" | "accent" | "halftone" | "lines";
interface Cell {
  x: number;
  y: number;
  w: number;
  h: number;
  fill: Fill;
}

/** Mulberry32: tiny deterministic PRNG. */
function rngFrom(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function generate(seed: number, W: number, H: number): Cell[] {
  const rng = rngFrom(seed);
  const cells: Cell[] = [];
  const maxDepth = 6;
  const stopProb = 0.18;
  const minSize = 46;
  const gap = 3;
  const splitMin = 0.34;
  const splitRange = 0.32;

  const pickFill = (): Fill => {
    const r = rng();
    if (r < 0.32) return "paper";
    if (r < 0.57) return "ink";
    if (r < 0.79) return "halftone";
    if (r < 0.92) return "lines";
    return "accent";
  };

  const emit = (x: number, y: number, w: number, h: number) => {
    cells.push({
      x: x + gap,
      y: y + gap,
      w: w - gap * 2,
      h: h - gap * 2,
      fill: pickFill(),
    });
  };

  const subdivide = (x: number, y: number, w: number, h: number, d: number) => {
    const stop =
      d >= maxDepth ||
      (d > 1 && rng() < stopProb) ||
      Math.min(w, h) < minSize * 2;
    if (stop) {
      emit(x, y, w, h);
      return;
    }
    const splitVertical = w > h ? rng() < 0.72 : rng() < 0.28;
    const frac = splitMin + rng() * splitRange;
    if (splitVertical) {
      subdivide(x, y, w * frac, h, d + 1);
      subdivide(x + w * frac, y, w * (1 - frac), h, d + 1);
    } else {
      subdivide(x, y, w, h * frac, d + 1);
      subdivide(x, y + h * frac, w, h * (1 - frac), d + 1);
    }
  };

  subdivide(0, 0, W, H, 0);
  return cells;
}

export function AlgorithmicArt({
  seed = 7,
  className,
}: {
  seed?: number;
  className?: string;
}) {
  const W = 520;
  const H = 416;
  const cells = generate(seed, W, H);

  return (
    <svg
      viewBox={`-14 -14 ${W + 28} ${H + 28}`}
      className={className}
      role="img"
      aria-label="Abstract procedural composition: a recursive subdivision of a rectangle into ink and accent cells."
    >
      <defs>
        <pattern
          id="alg-halftone"
          width="7"
          height="7"
          patternUnits="userSpaceOnUse"
        >
          <rect width="7" height="7" fill="#F4EFE6" />
          <circle cx="3.5" cy="3.5" r="1.4" fill="#1F1B16" />
        </pattern>
        <pattern
          id="alg-lines"
          width="6"
          height="6"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <rect width="6" height="6" fill="#F4EFE6" />
          <line x1="0" y1="0" x2="0" y2="6" stroke="#1F1B16" strokeWidth="1.6" />
        </pattern>
        <pattern
          id="alg-accent-grain"
          width="7"
          height="7"
          patternUnits="userSpaceOnUse"
        >
          <rect width="7" height="7" fill="#E0531F" />
          <circle cx="3.5" cy="3.5" r="1.1" fill="#A33810" opacity="0.6" />
        </pattern>
      </defs>

      {/* registration crosses in each corner */}
      <g stroke="#E0531F" strokeWidth="1.5" strokeLinecap="round">
        <path d="M -10 0 L -2 0 M 0 -10 L 0 -2" />
        <path d={`M ${W + 10} 0 L ${W + 2} 0 M ${W} -10 L ${W} -2`} />
        <path d={`M -10 ${H} L -2 ${H} M 0 ${H + 10} L 0 ${H + 2}`} />
        <path
          d={`M ${W + 10} ${H} L ${W + 2} ${H} M ${W} ${H + 10} L ${W} ${H + 2}`}
        />
      </g>

      {/* outer ink rule */}
      <rect
        x="0"
        y="0"
        width={W}
        height={H}
        fill="none"
        stroke="#1F1B16"
        strokeWidth="1.1"
      />

      {/* cells */}
      {cells.map((c, i) => {
        const fill =
          c.fill === "paper"
            ? "#F4EFE6"
            : c.fill === "ink"
              ? "#1F1B16"
              : c.fill === "accent"
                ? "url(#alg-accent-grain)"
                : c.fill === "halftone"
                  ? "url(#alg-halftone)"
                  : "url(#alg-lines)";
        return (
          <rect
            key={i}
            x={c.x}
            y={c.y}
            width={c.w}
            height={c.h}
            fill={fill}
            stroke="#1F1B16"
            strokeWidth={c.fill === "paper" ? 0.6 : 0}
            opacity={c.fill === "paper" ? 0.45 : 1}
          />
        );
      })}
    </svg>
  );
}
