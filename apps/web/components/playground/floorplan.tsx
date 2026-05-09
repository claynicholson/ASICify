"use client";
import type { QuickEstimate } from "@/lib/estimator";

/**
 * Silicon floorplan visualization. Shows storage / compute / SRAM / I/O regions
 * sized proportionally to area_breakdown.
 */
export function Floorplan({ estimate }: { estimate: QuickEstimate }) {
  const { storage_mm2, compute_mm2, sram_mm2, io_mm2, routing_overhead_mm2 } =
    estimate.area_breakdown;
  const total = storage_mm2 + compute_mm2 + sram_mm2 + io_mm2 + routing_overhead_mm2;

  // Normalized fractions
  const fStorage = storage_mm2 / total;
  const fCompute = compute_mm2 / total;
  const fSram = sram_mm2 / total;
  const fIo = io_mm2 / total;

  // Treemap-ish layout in a square. Storage spans left, compute right-top,
  // SRAM right-mid, I/O ring around edges.
  return (
    <div className="aspect-square w-full rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-overlay)] p-3 relative overflow-hidden">
      {/* I/O ring (border) */}
      <div
        className="absolute inset-0 border-[3px] rounded-[6px] pointer-events-none"
        style={{
          borderColor: "var(--color-series-4)",
          opacity: 0.4 + fIo * 2,
        }}
      />

      <div className="relative h-full w-full grid grid-cols-2 gap-1">
        <Region
          label="Storage"
          sublabel={`${storage_mm2.toFixed(2)} mm²`}
          fraction={fStorage}
          color="var(--color-series-1)"
          className="row-span-2"
        />
        <Region
          label="Compute"
          sublabel={`${compute_mm2.toFixed(2)} mm²`}
          fraction={fCompute}
          color="var(--color-series-2)"
        />
        <Region
          label="SRAM"
          sublabel={`${sram_mm2.toFixed(2)} mm²`}
          fraction={fSram}
          color="var(--color-series-3)"
        />
      </div>

      <div className="absolute bottom-3 left-3 right-3 flex justify-between items-end pointer-events-none">
        <div className="text-[10px] font-mono text-[var(--color-text-tertiary)]">
          {Math.sqrt(estimate.area_mm2).toFixed(2)} ×{" "}
          {Math.sqrt(estimate.area_mm2).toFixed(2)} mm
        </div>
        <div className="text-[10px] font-mono text-[var(--color-text-tertiary)]">
          {estimate.area_mm2.toFixed(2)} mm² total
        </div>
      </div>
    </div>
  );
}

function Region({
  label,
  sublabel,
  fraction,
  color,
  className,
}: {
  label: string;
  sublabel: string;
  fraction: number;
  color: string;
  className?: string;
}) {
  return (
    <div
      className={`relative rounded-[3px] flex flex-col justify-between p-2 overflow-hidden ${className ?? ""}`}
      style={{
        backgroundColor: color,
        opacity: 0.15 + Math.min(fraction * 1.5, 0.6),
      }}
    >
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: `linear-gradient(135deg, transparent 49.5%, ${color} 49.5%, ${color} 50.5%, transparent 50.5%)`,
          backgroundSize: "8px 8px",
          opacity: 0.3,
        }}
      />
      <div className="relative">
        <div className="text-[10px] font-medium uppercase tracking-[0.08em]">
          {label}
        </div>
      </div>
      <div className="relative font-mono text-[10px]">
        {sublabel}
        <div className="text-[var(--color-text-tertiary)]">
          {(fraction * 100).toFixed(0)}%
        </div>
      </div>
    </div>
  );
}
