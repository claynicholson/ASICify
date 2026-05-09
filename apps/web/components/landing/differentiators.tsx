import { Layers, GitBranch, CircuitBoard } from "lucide-react";

const ITEMS = [
  {
    icon: Layers,
    title: "Multi-target backend",
    description:
      "One tool, every target. SkyWater, GF22FDX, TSMC 28/16/7nm, Lattice ECP5/CrossLink-NX, Xilinx Artix-7/Kria, TinyTapeout, chipIgnite — all from the same source model.",
  },
  {
    icon: GitBranch,
    title: "Open-source core",
    description:
      "MIT licensed. The compression pipeline and RTL generator are on GitHub. No NDAs, no per-tape-out fees. The hosted version layers convenience and compute.",
  },
  {
    icon: CircuitBoard,
    title: "Hardware-software co-design",
    description:
      "Sub-1-bit effective representation. Monarch matrix decomposition built into synthesis. Hardware-aware fine-tuning. Optimize the model for the silicon.",
  },
];

export function Differentiators() {
  return (
    <section className="mx-auto max-w-[1200px] px-6 py-24">
      <div className="max-w-2xl mb-12">
        <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
          Why ASICify
        </div>
        <h2 className="text-[2.5rem] font-bold tracking-tight-display leading-[1.1]">
          Built for the AI silicon era.
        </h2>
        <p className="mt-4 text-[var(--color-text-secondary)] leading-relaxed">
          Cadence and Synopsys built EDA for general-purpose chips. ASICify is
          built for one thing: turning a trained network into a fixed-function
          inference accelerator.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.title}
              className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-6 hover:border-[var(--color-border-default)] transition-colors"
            >
              <Icon className="h-5 w-5 text-[var(--color-accent)] mb-4" />
              <h3 className="text-base font-semibold mb-2">{item.title}</h3>
              <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                {item.description}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
