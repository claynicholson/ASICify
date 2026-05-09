"use client";
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import type { QuickEstimate } from "@/lib/estimator";
import type { TargetId } from "@asicify/shared";
import { TARGETS } from "@asicify/shared";

interface Point {
  target: TargetId;
  name: string;
  cost: number;
  throughput: number;
  area: number;
}

export function ParetoPlot({ estimates }: { estimates: QuickEstimate[] }) {
  const data: Point[] = estimates.map((e) => ({
    target: e.target,
    name: TARGETS[e.target].display_name,
    cost: e.cost_per_chip["100000"],
    throughput: e.throughput_per_sec,
    area: e.area_mm2,
  }));

  return (
    <div className="h-full w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 12, right: 12, bottom: 30, left: 50 }}>
          <CartesianGrid stroke="var(--color-border-subtle)" />
          <XAxis
            type="number"
            dataKey="cost"
            name="Cost"
            stroke="var(--color-text-tertiary)"
            tick={{ fontSize: 10, fontFamily: "var(--font-mono)" }}
            label={{
              value: "Cost per chip @ 100K units ($)",
              position: "bottom",
              offset: 12,
              fill: "var(--color-text-tertiary)",
              fontSize: 11,
            }}
          />
          <YAxis
            type="number"
            dataKey="throughput"
            name="Throughput"
            stroke="var(--color-text-tertiary)"
            tick={{ fontSize: 10, fontFamily: "var(--font-mono)" }}
            label={{
              value: "Throughput (ops/s)",
              angle: -90,
              position: "left",
              offset: 35,
              fill: "var(--color-text-tertiary)",
              fontSize: 11,
            }}
            scale="log"
            domain={["auto", "auto"]}
          />
          <ZAxis type="number" dataKey="area" range={[40, 400]} name="Area" />
          <Tooltip
            cursor={{ stroke: "var(--color-accent)", strokeDasharray: "3 3" }}
            contentStyle={{
              backgroundColor: "var(--color-bg-overlay)",
              border: "1px solid var(--color-border-default)",
              borderRadius: 6,
              fontSize: 12,
              fontFamily: "var(--font-mono)",
            }}
          />
          <Scatter
            data={data}
            fill="var(--color-accent)"
            stroke="var(--color-accent-hover)"
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
