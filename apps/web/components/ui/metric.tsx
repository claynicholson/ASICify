import { cn } from "@/lib/utils";

export function Metric({
  label,
  value,
  unit,
  delta,
  className,
}: {
  label: string;
  value: string | number;
  unit?: string;
  delta?: { value: string; tone: "positive" | "negative" | "neutral" };
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <span className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium">
        {label}
      </span>
      <div className="flex items-baseline gap-1.5">
        <span className="font-mono text-2xl font-semibold text-[var(--color-text-primary)]">
          {value}
        </span>
        {unit && (
          <span className="font-mono text-xs text-[var(--color-text-tertiary)]">
            {unit}
          </span>
        )}
      </div>
      {delta && (
        <span
          className={cn(
            "font-mono text-[11px]",
            delta.tone === "positive" && "text-[var(--color-success)]",
            delta.tone === "negative" && "text-[var(--color-error)]",
            delta.tone === "neutral" && "text-[var(--color-text-tertiary)]",
          )}
        >
          {delta.value}
        </span>
      )}
    </div>
  );
}
