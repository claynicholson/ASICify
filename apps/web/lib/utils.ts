import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a number compactly: 1234567 -> "1.2M". */
export function formatCompact(n: number, digits = 1): string {
  if (n === 0) return "0";
  const abs = Math.abs(n);
  if (abs < 1_000) return n.toFixed(digits === 0 ? 0 : 0);
  if (abs < 1_000_000) return `${(n / 1_000).toFixed(digits)}K`;
  if (abs < 1_000_000_000) return `${(n / 1_000_000).toFixed(digits)}M`;
  return `${(n / 1_000_000_000).toFixed(digits)}B`;
}

/** Format a value as USD currency. */
export function formatUSD(n: number): string {
  if (n < 1) return `$${n.toFixed(3)}`;
  if (n < 100) return `$${n.toFixed(2)}`;
  return `$${Math.round(n).toLocaleString("en-US")}`;
}

/** Format mm² with appropriate precision. */
export function formatArea(mm2: number): string {
  if (mm2 < 1) return `${mm2.toFixed(3)} mm²`;
  if (mm2 < 100) return `${mm2.toFixed(2)} mm²`;
  return `${Math.round(mm2)} mm²`;
}
