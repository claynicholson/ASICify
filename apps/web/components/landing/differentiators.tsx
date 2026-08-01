import { SectionHeader } from "@/components/landing/section-header";

const SPECS: { label: string; value: React.ReactNode }[] = [
  {
    label: "Hardware targets",
    value:
      "SkyWater 130 · GF22FDX · TSMC 28 / 16 / 7 · Lattice ECP5 · CrossLink-NX · Xilinx Artix-7 · Kria K26 · TinyTapeout · chipIgnite",
  },
  {
    label: "Quantization",
    value: "FP16 · INT8 · INT4 · ternary · binary",
  },
  {
    label: "Sparsity",
    value: "none · 2:4 · 4:8 · block 16×16 · unstructured",
  },
  {
    label: "Decomposition",
    value:
      "Monarch matrix factorization, built into synthesis so it changes the resulting gate count.",
  },
  {
    label: "Outputs",
    value:
      "Synthesizable Verilog with hardwired weights, a Cocotb testbench, and an area-and-cost report per target.",
  },
  {
    label: "Cost model",
    value:
      "Cell-library data with published citations, ±20-40% confidence bands. Derivation in /docs/methodology.",
  },
  {
    label: "License",
    value: "MIT. Use, fork, modify, and ship it in commercial products.",
  },
  {
    label: "Status",
    value: "v0.1, pre-1.0. The compiler spine is complete.",
  },
];

export function Differentiators() {
  return (
    <section className="mx-auto max-w-[1200px] px-6 pb-24">
      <SectionHeader index="02" title="Specifications" />

      <dl>
        {SPECS.map((s) => (
          <div
            key={s.label}
            className="grid grid-cols-12 gap-4 py-4 border-b border-[var(--color-border-subtle)] first:border-t first:border-t-[var(--color-border-subtle)]"
          >
            <dt className="col-span-12 md:col-span-3 label-mono pt-1">
              {s.label}
            </dt>
            <dd className="col-span-12 md:col-span-9 m-0 text-[15.5px] text-[var(--color-text-primary)] leading-[1.6]">
              {s.value}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
