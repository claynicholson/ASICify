const SPECS: { label: string; value: string }[] = [
  {
    label: "Hardware targets",
    value:
      "Eleven targets are supported: SkyWater 130, GF22FDX, TSMC 28 / 16 / 7, Lattice ECP5, CrossLink-NX, Xilinx Artix-7, Kria, TinyTapeout, and chipIgnite.",
  },
  {
    label: "Quantization",
    value: "INT4, INT8, and ternary modes are available.",
  },
  {
    label: "Sparsity",
    value:
      "Structured 2:4 sparsity and configurable density patterns are supported.",
  },
  {
    label: "Decomposition",
    value:
      "Monarch matrix factorization is built into synthesis so it influences the resulting gate count.",
  },
  {
    label: "Outputs",
    value:
      "Each run produces synthesizable Verilog with hardwired weights, a Cocotb testbench, and an area-and-cost report for every selected target.",
  },
  {
    label: "License",
    value:
      "MIT, so you can use, fork, modify, and ship it in commercial products.",
  },
  {
    label: "Source",
    value: "github.com/claynicholson/asicify",
  },
  {
    label: "Status",
    value: "Version 0.1, pre-1.0. The compiler spine is complete.",
  },
];

export function Differentiators() {
  return (
    <section className="relative">
      <div className="relative mx-auto max-w-[1200px] px-6 py-24">
        <div className="max-w-2xl mb-12">
          <div className="eyebrow mb-3">Specifications</div>
          <h2 className="font-serif text-[clamp(2.25rem,4.5vw,3rem)] leading-[1.05] tracking-serif">
            What it is
          </h2>
        </div>

        <dl className="border-t border-[var(--color-border-default)]">
          {SPECS.map((s) => (
            <div
              key={s.label}
              className="grid grid-cols-12 gap-4 py-5 border-b border-[var(--color-border-subtle)]"
            >
              <dt className="col-span-12 md:col-span-3 font-mono text-[11px] tracking-[0.16em] uppercase text-[var(--color-text-tertiary)] pt-1">
                {s.label}
              </dt>
              <dd className="col-span-12 md:col-span-9 text-[16px] text-[var(--color-text-primary)] leading-relaxed">
                {s.value}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
