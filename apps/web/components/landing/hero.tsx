import Link from "next/link";
import { Button } from "@/components/ui/button";
import { DieFloorplan } from "@/components/landing/die-floorplan";

const QUICK_SPECS = [
  { value: "11", unit: "", label: "hardware targets" },
  { value: "5", unit: "", label: "foundry nodes" },
  { value: "<1", unit: "ms", label: "estimate latency" },
  { value: "MIT", unit: "", label: "license" },
];

export function Hero() {
  return (
    <section className="relative">
      <div className="mx-auto max-w-[1200px] px-6 pt-16 pb-20 md:pt-24 md:pb-24">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-start">
          <div className="lg:col-span-6">
            <p className="font-mono text-[12px] tracking-[0.08em] text-[var(--color-text-tertiary)] mb-6">
              v0.1 · MIT · open source
            </p>

            <h1 className="display text-[clamp(2.75rem,6vw,4.5rem)] text-[var(--color-text-primary)]">
              An open compiler from PyTorch to Verilog
            </h1>

            <p className="mt-6 max-w-[54ch] text-[17px] md:text-[18px] text-[var(--color-text-secondary)] leading-[1.6]">
              ASICify takes a trained PyTorch model and emits synthesizable
              Verilog, a Cocotb testbench, and area-and-cost estimates across
              eleven hardware targets. You run it. You keep the RTL.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button asChild size="lg">
                <Link href="/playground">Open the playground</Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <a
                  href="https://github.com/claynicholson/asicify"
                  target="_blank"
                  rel="noreferrer"
                >
                  Read the source
                </a>
              </Button>
            </div>

            <dl className="mt-14 grid grid-cols-2 sm:grid-cols-4 border-y border-[var(--color-border-default)]">
              {QUICK_SPECS.map((s) => (
                <div
                  key={s.label}
                  className="py-4 px-4 first:pl-0 sm:[&:not(:first-child)]:border-l max-sm:even:border-l max-sm:[&:nth-child(n+3)]:border-t border-[var(--color-border-subtle)]"
                >
                  <dd className="font-mono text-[22px] leading-none text-[var(--color-text-primary)]">
                    {s.value}
                    {s.unit && (
                      <span className="text-[13px] text-[var(--color-text-tertiary)] ml-0.5">
                        {s.unit}
                      </span>
                    )}
                  </dd>
                  <dt className="mt-2 label-mono">{s.label}</dt>
                </div>
              ))}
            </dl>
          </div>

          <figure className="lg:col-span-6 lg:pl-6 m-0">
            <DieFloorplan className="w-full h-auto" />
            <figcaption className="mt-4 font-mono text-[11px] leading-[1.7] tracking-[0.03em] text-[var(--color-text-tertiary)] max-w-[52ch]">
              <span className="text-[var(--color-accent-deep)]">FIG. 1</span>
              {"  "}Estimated floorplan · GPT-2 124M, INT4, 2:4 sparsity →
              TSMC 28 nm. 8.2 mm² die, $4.10 per chip at 100 K units.
            </figcaption>
          </figure>
        </div>
      </div>
    </section>
  );
}
