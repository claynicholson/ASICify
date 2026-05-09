"use client";
import { useState } from "react";
import { cn } from "@/lib/utils";

const PERSONAS = [
  {
    id: "ml-systems",
    label: "I'm exploring custom silicon",
    headline: "30-page hardware feasibility report from a checkpoint in 10 minutes.",
    description:
      "You have a model that runs on GPUs but is too expensive at scale. Leadership wants a credible cost / feasibility analysis. ASICify produces it: target comparison, BOM at volume, throughput projections — defensible numbers your CFO can actually use.",
    bullets: [
      "Cost per chip at 1K / 100K / 1M volume tiers",
      "Throughput per area across 11 hardware targets",
      "Apples-to-apples comparison vs. continued GPU spend",
    ],
  },
  {
    id: "asic-designer",
    label: "I'm an ASIC designer",
    headline: "Skip the bottom 60% of your stack.",
    description:
      "You currently hand-write quantization, sparsity, and RTL templates for every model. That's not where your differentiation is. Use ASICify for the boilerplate so you can focus on cell-level and process-level work.",
    bullets: [
      "Synthesizable Verilog with hardwired multipliers",
      "Cocotb testbench + bit-exact Python reference",
      "Open templates — extend with your own primitives",
    ],
  },
  {
    id: "researcher",
    label: "I'm a researcher",
    headline: "Real silicon estimates for your methodology section.",
    description:
      "You publish on efficient inference but reviewers ask 'what would this cost in actual hardware?' ASICify is the free, open-source tool you cite — with confidence intervals derived from published cell library data.",
    bullets: [
      "Reproducible: every estimate pinned to a config hash",
      "MIT-licensed core, no commercial EDA dependency",
      "Citeable: published cost models documented in /docs/methodology",
    ],
  },
  {
    id: "edge-deployer",
    label: "I'm deploying on FPGAs",
    headline: "Lattice and Xilinx, ready to flash.",
    description:
      "You're shipping IoT, automotive, or robotics products. ASICify generates the FPGA RTL today and gives you the path to ASIC if your volumes justify it.",
    bullets: [
      "ECP5 + nextpnr toolchain (open source)",
      "Vivado scripts for Artix-7 and Kria",
      "Same source model as the eventual ASIC tape-out",
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
          Built for the people who actually ship silicon.
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
