import { SectionHeader } from "@/components/landing/section-header";

const STAGES = [
  {
    index: "01",
    title: "Input",
    artifact: "checkpoint.pt → graph.json",
    description:
      "A PyTorch checkpoint, a HuggingFace ID, or a model from the curated catalog. ASICify parses the compute graph and prepares it for compression.",
  },
  {
    index: "02",
    title: "Compression",
    artifact: "graph.json → weights.q4",
    description:
      "INT4 or INT8 quantization, structured sparsity, Monarch decomposition, and optional hardware-aware fine-tuning. Quality is measured on a held-out benchmark before any artifact is written.",
  },
  {
    index: "03",
    title: "Output",
    artifact: "weights.q4 → top.v + tb/ + report",
    description:
      "Synthesizable Verilog with hardwired weights, a Cocotb testbench, and an area-and-cost report for every selected target. Each artifact is pinned to a config hash so the run is reproducible.",
  },
];

export function HowItWorks() {
  return (
    <section className="mx-auto max-w-[1200px] px-6 pb-24">
      <SectionHeader index="01" title="Pipeline" />

      <div className="grid grid-cols-1 md:grid-cols-3 md:divide-x divide-y md:divide-y-0 divide-[var(--color-border-subtle)] border-y border-[var(--color-border-subtle)]">
        {STAGES.map((stage) => (
          <div
            key={stage.index}
            className="py-8 md:px-8 first:md:pl-0 last:md:pr-0"
          >
            <div className="flex items-baseline justify-between mb-4">
              <h3 className="display-sub text-[1.375rem] text-[var(--color-text-primary)]">
                {stage.title}
              </h3>
              <span className="font-mono text-[12px] text-[var(--color-text-tertiary)]">
                {stage.index}
              </span>
            </div>
            <p className="text-[15px] text-[var(--color-text-secondary)] leading-[1.65]">
              {stage.description}
            </p>
            <p className="mt-5 font-mono text-[12px] tracking-[0.02em] text-[var(--color-accent-deep)]">
              {stage.artifact}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
