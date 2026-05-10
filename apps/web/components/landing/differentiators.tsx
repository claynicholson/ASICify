import { Layers, GitBranch, CircuitBoard } from "lucide-react";

const ITEMS = [
  {
    icon: Layers,
    title: "Eleven hardware targets",
    description:
      "SkyWater 130, GF22FDX, TSMC 28/16/7nm, Lattice ECP5, Lattice CrossLink-NX, Xilinx Artix-7, Xilinx Kria, TinyTapeout, chipIgnite. One source model emits all of them.",
  },
  {
    icon: GitBranch,
    title: "Fully open source",
    description:
      "MIT licensed. The full compiler, RTL generator, and cost models live on GitHub. No NDAs, no per-tape-out fees, no proprietary core.",
  },
  {
    icon: CircuitBoard,
    title: "Hardware-aware compression",
    description:
      "Sub-1-bit effective bits per weight via ternary plus sparsity plus decomposition. Monarch matrix factorization built into synthesis. Hardware-aware fine-tuning.",
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
          A compiler, not a chip company.
        </h2>
        <p className="mt-4 text-[var(--color-text-secondary)] leading-relaxed">
          Cadence and Synopsys built EDA for general-purpose chips. ASICify
          targets one workflow: turning a trained inference network into a
          fixed-function accelerator.
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
