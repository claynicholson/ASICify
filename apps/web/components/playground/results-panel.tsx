"use client";

import { Metric } from "@/components/ui/metric";
import { formatArea, formatCompact, formatUSD } from "@/lib/utils";
import type { QuickEstimate } from "@/lib/estimator";

export function ResultsPanel({
  estimate,
  baselineParams,
}: {
  estimate: QuickEstimate;
  baselineParams: number;
}) {
  const reduction = 1 - estimate.effective_param_count / baselineParams;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
          Estimated metrics
        </div>
        <div className="grid grid-cols-2 gap-6">
          <Metric
            label="Quality (ppl)"
            value={estimate.estimated_metric.toFixed(1)}
            delta={{
              value: `+${(((estimate.estimated_metric / 10) - 1) * 100).toFixed(1)}%`,
              tone:
                estimate.estimated_metric > 12
                  ? "negative"
                  : estimate.estimated_metric > 10.5
                    ? "neutral"
                    : "positive",
            }}
          />
          <Metric
            label="Size reduction"
            value={`${(reduction * 100).toFixed(1)}`}
            unit="%"
            delta={{
              value: `${formatCompact(estimate.effective_param_count)} effective params`,
              tone: "neutral",
            }}
          />
          <Metric
            label="Bits / weight"
            value={estimate.bits_per_weight.toFixed(2)}
            unit="bit"
          />
          <Metric
            label="Throughput"
            value={formatCompact(estimate.throughput_per_sec)}
            unit="ops/s"
          />
        </div>
      </div>

      <div className="border-t border-[var(--color-border-subtle)]" />

      <div>
        <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
          Hardware estimate
        </div>
        <div className="grid grid-cols-2 gap-6">
          <Metric
            label="Die area"
            value={formatArea(estimate.area_mm2).split(" ")[0]}
            unit="mm²"
          />
          <Metric
            label="Max clock"
            value={estimate.max_clock_mhz.toFixed(0)}
            unit="MHz"
          />
          <Metric
            label="Energy / op"
            value={estimate.energy_per_op_pj.toFixed(2)}
            unit="pJ"
          />
          <Metric
            label="Confidence"
            value={`±${Math.round((1 - estimate.confidence) * 100)}`}
            unit="%"
          />
        </div>
      </div>

      <div className="border-t border-[var(--color-border-subtle)]" />

      <div>
        <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
          Cost per chip
        </div>
        <div className="grid grid-cols-3 gap-6">
          <Metric
            label="@ 1K units"
            value={formatUSD(estimate.cost_per_chip["1000"])}
          />
          <Metric
            label="@ 100K units"
            value={formatUSD(estimate.cost_per_chip["100000"])}
          />
          <Metric
            label="@ 1M units"
            value={formatUSD(estimate.cost_per_chip["1000000"])}
          />
        </div>
      </div>
    </div>
  );
}
