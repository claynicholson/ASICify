"use client";

import { useMemo, useState } from "react";
import type { CompressionConfig, TargetId } from "@asicify/shared";
import { TARGET_LIST } from "@asicify/shared";
import { Nav } from "@/components/nav";
import { ConfigPanel } from "@/components/playground/config-panel";
import { ResultsPanel } from "@/components/playground/results-panel";
import { Floorplan } from "@/components/playground/floorplan";
import { ParetoPlot } from "@/components/playground/pareto-plot";
import { InferenceComparison } from "@/components/playground/inference-comparison";
import { MODEL_CATALOG, opsPerInference } from "@/lib/catalog";
import { quickEstimate } from "@/lib/estimator";
import { Button } from "@/components/ui/button";

const DEFAULT_CONFIG: CompressionConfig = {
  quantization: "int4",
  sparsity: { type: "structured_2_4", ratio: 0.5 },
  decomposition: { type: "none" },
  fine_tune: false,
  fine_tune_steps: 1000,
};

export default function PlaygroundPage() {
  const [modelId, setModelId] = useState(MODEL_CATALOG[0].id);
  const [config, setConfig] = useState<CompressionConfig>(DEFAULT_CONFIG);
  const [target, setTarget] = useState<TargetId>("tsmc28");

  const model = useMemo(
    () => MODEL_CATALOG.find((m) => m.id === modelId) ?? MODEL_CATALOG[0],
    [modelId],
  );

  const estimate = useMemo(
    () =>
      quickEstimate({
        param_count: model.parameters,
        ops_per_token: opsPerInference(model.parameters),
        config,
        target,
        baseline_metric: model.task === "language_modeling" ? 9.2 : 1,
      }),
    [model, config, target],
  );

  // Compare across all ASIC + key FPGA targets for the Pareto plot
  const paretoEstimates = useMemo(() => {
    const targets: TargetId[] = [
      "sky130",
      "gf22fdx",
      "tsmc28",
      "tsmc16",
      "tsmc7",
      "ecp5",
      "artix7",
      "kria",
    ];
    return targets.map((t) =>
      quickEstimate({
        param_count: model.parameters,
        ops_per_token: opsPerInference(model.parameters),
        config,
        target: t,
        baseline_metric: model.task === "language_modeling" ? 9.2 : 1,
      }),
    );
  }, [model, config]);

  const onCompile = () => {
    // In production, hits POST /api/projects then routes to /projects/[id].
    // Stub for the playground demo.
    alert(
      "Compilation queued. Sign in to save the project and download the RTL package.",
    );
  };

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[1440px] px-6 py-8">
        <div className="mb-8 flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-bold tracking-tight-display">
              Playground
            </h1>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              Live estimates as you tune compression. Cached numbers update in
              real time — full compile generates real RTL.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              Save as project
            </Button>
            <Button variant="outline" size="sm">
              Share
            </Button>
            <Button size="sm">Download RTL</Button>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          {/* Left: configuration */}
          <aside className="col-span-12 lg:col-span-3">
            <div className="sticky top-20 rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-5">
              <ConfigPanel
                modelId={modelId}
                setModelId={setModelId}
                config={config}
                setConfig={setConfig}
                target={target}
                setTarget={setTarget}
                onCompile={onCompile}
              />
            </div>
          </aside>

          {/* Middle: live results */}
          <section className="col-span-12 lg:col-span-5">
            <div className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-6">
              <div className="flex items-center gap-2 mb-6">
                <h2 className="text-lg font-semibold">
                  {model.display_name} →{" "}
                  <span className="text-[var(--color-accent)]">
                    {TARGET_LIST.find((t) => t.id === target)?.display_name}
                  </span>
                </h2>
                <span className="ml-auto text-[10px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-mono">
                  cached estimate
                </span>
              </div>
              <ResultsPanel
                estimate={estimate}
                baselineParams={model.parameters}
              />
            </div>

            <div className="mt-6">
              <InferenceComparison quantization={config.quantization} />
            </div>
          </section>

          {/* Right: visualizations */}
          <section className="col-span-12 lg:col-span-4 flex flex-col gap-6">
            <div className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-5">
              <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
                Silicon floorplan
              </div>
              <Floorplan estimate={estimate} />
            </div>

            <div className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-5">
              <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
                Cost vs throughput across targets
              </div>
              <div className="h-[280px]">
                <ParetoPlot estimates={paretoEstimates} />
              </div>
            </div>
          </section>
        </div>
      </main>
    </>
  );
}
