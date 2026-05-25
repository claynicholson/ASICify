/**
 * Hand-drawn vector ornaments. Authored with slightly imperfect paths,
 * rounded line caps, and unequal stroke widths to read as ink on paper
 * rather than CAD output.
 */

import type { SVGProps } from "react";

type OrnamentProps = SVGProps<SVGSVGElement> & { className?: string };

/** Squiggly underline, sits beneath a brand word. */
export function ScribbleUnderline({ className, ...rest }: OrnamentProps) {
  return (
    <svg
      viewBox="0 0 220 14"
      fill="none"
      preserveAspectRatio="none"
      className={className}
      aria-hidden
      {...rest}
    >
      <path
        d="M2 8 C 22 2, 48 12, 72 7 S 122 1, 148 9 S 198 3, 218 7"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Looping hand-drawn arrow, pointing down-right. */
export function CurlyArrow({ className, ...rest }: OrnamentProps) {
  return (
    <svg
      viewBox="0 0 96 80"
      fill="none"
      className={className}
      aria-hidden
      {...rest}
    >
      <path
        d="M6 8 C 22 14, 38 26, 44 44 C 48 56, 58 64, 78 64"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M78 64 L 70 58 M 78 64 L 70 70"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}

/** Sharper diagonal arrow, used as a CTA accent. */
export function SharpArrow({ className, ...rest }: OrnamentProps) {
  return (
    <svg
      viewBox="0 0 28 14"
      fill="none"
      className={className}
      aria-hidden
      {...rest}
    >
      <path
        d="M2 7 L 24 7 M 18 2 L 25 7 L 18 12"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

/** Curly bracket, used to group an annotation. */
export function HandBracket({
  className,
  side = "left",
  ...rest
}: OrnamentProps & { side?: "left" | "right" }) {
  const flip = side === "right" ? "scale(-1, 1) translate(-24, 0)" : undefined;
  return (
    <svg
      viewBox="0 0 24 80"
      fill="none"
      className={className}
      aria-hidden
      {...rest}
    >
      <g transform={flip}>
        <path
          d="M18 4 C 8 8, 14 28, 6 38 C 14 48, 8 68, 18 76"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          fill="none"
        />
      </g>
    </svg>
  );
}

/** Tiny checkmark, used in lists in place of bullets. */
export function InkCheck({ className, ...rest }: OrnamentProps) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      className={className}
      aria-hidden
      {...rest}
    >
      <path
        d="M3 11 L 8 16 L 17 4"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Tiny x-mark, used opposite InkCheck. */
export function InkX({ className, ...rest }: OrnamentProps) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      className={className}
      aria-hidden
      {...rest}
    >
      <path
        d="M4 4 L 16 16 M 16 4 L 4 16"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}
