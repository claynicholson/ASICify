"use client";
import { useState } from "react";
import { cn } from "@/lib/utils";

const PERSONAS = [
  {
    id: "ml-systems",
    label: "Exploring custom silicon",
    headline: "Hardware feasibility report from a checkpoint.",
    description:
      "You have a model that runs on GPUs but is too expensive at scale. Leadership wants a credible cost analysis. ASICify produces target comparisons, BOM at volume, and throughput projections you can defend in a CFO meeting.",
    bullets: [
      "Cost per chip at 1K, 100K, and 1M volume tiers",
      "Throughput per area across eleven hardware targets",
      "Direct comparison vs. continued GPU spend",
    ],
  },
  {
    id: "asic-designer",
    label: "ASIC designer at a chip startup",
    headline: "Stop hand-writing the boilerplate.",
    description:
      "You currently hand-write quantization, sparsity, and RTL templates for every model. That isn't where your differentiation is. Use ASICify for the repetitive work and focus on cell-level and process-level engineering.",
    bullets: [
      "Synthesizable Verilog with hardwired multipliers",
      "Cocotb testbench plus bit-exact Python reference",
      "Open templates you can extend with your own primitives",
    ],
  },
  {
    id: "researcher",
    label: "Research and academia",
    headline: "Real silicon estimates for your methodology section.",
    description:
      "You publish on efficient inference. Reviewers ask what your method would cost in actual hardware. ASICify is the free, open-source tool you can cite, with confidence intervals derived from published cell library data.",
    bullets: [
      "Reproducible estimates pinned to a config hash",
      "MIT-licensed core, no commercial EDA dependency",
      "Cost models documented in /docs/methodology",
    ],
  },
  {
    id: "edge-deployer",
    label: "Edge AI deployment",
    headline: "FPGA bitstreams, ready to flash.",
    description:
      "You ship IoT, automotive, or robotics products. ASICify generates the FPGA RTL today and gives you a path to ASIC if your volumes justify it.",
    bullets: [
      "ECP5 plus nextpnr toolchain (open source)",
      "Vivado scripts for Artix-7 and Kria",
      "Same source model when you migrate to ASIC",
    ],
  },
];

export function UseCases() {
  const [active, setActive] = useState(PERSONAS[0].id);
  const persona = PERSONAS.find((p) => p.id === active)!;

  return (
    <section className="mx-auto max-w-[1200px] px-6 py-24">
      <div className="max-w-2xl mb-10">
        <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
          Use cases
        </div>
        <h2 className="text-[2.5rem] font-bold tracking-tight-display leading-[1.1]">
          Four common workflows.
        </h2>
      </div>

      <div className="flex flex-wrap gap-2 mb-8">
        {PERSONAS.map((p) => (
          <button
            key={p.id}
            onClick={() => setActive(p.id)}
            className={cn(
              "px-4 py-2 rounded-[6px] text-sm border transition-colors",
              active === p.id
                ? "border-[var(--color-accent)] bg-[var(--color-accent-muted)] text-[var(--color-text-primary)]"
                : "border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]",
            )}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-8">
        <h3 className="text-2xl font-semibold tracking-tight-display mb-3">
          {persona.headline}
        </h3>
        <p className="text-[var(--color-text-secondary)] leading-relaxed mb-6 max-w-3xl">
          {persona.description}
        </p>
        <ul className="space-y-2">
          {persona.bullets.map((b) => (
            <li
              key={b}
              className="flex gap-3 text-sm text-[var(--color-text-secondary)]"
            >
              <span className="text-[var(--color-accent)]">▸</span>
              {b}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
