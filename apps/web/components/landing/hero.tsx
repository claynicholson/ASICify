import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AlgorithmicArt } from "@/components/landing/algorithmic-art";
import { SharpArrow } from "@/components/ornaments";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 bg-blueprint pointer-events-none" />

      <div className="relative mx-auto max-w-[1200px] px-6 pt-16 pb-24 md:pt-24 md:pb-32">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-start">
          {/* Left: copy */}
          <div className="lg:col-span-7">
            <div className="mb-7">
              <span className="stamp">v0.1 · MIT · open source</span>
            </div>

            <h1 className="font-serif text-[clamp(3rem,6.8vw,5rem)] leading-[1.02] tracking-serif text-[var(--color-text-primary)]">
              An open compiler from PyTorch to Verilog
            </h1>

            <p className="mt-7 max-w-2xl text-[18px] md:text-[19px] text-[var(--color-text-secondary)] leading-[1.55]">
              ASICify takes a trained PyTorch model and emits synthesizable
              Verilog, a Cocotb testbench, and area-and-cost estimates across
              eleven hardware targets. It is MIT licensed, and the source is
              available on GitHub.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button asChild size="lg">
                <Link href="/playground">
                  Open the playground
                  <SharpArrow className="w-5 h-3 text-[var(--color-accent-ink)]" />
                </Link>
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

            <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-5 max-w-[520px]">
              <Stat label="hardware targets" value="11" />
              <Stat label="foundry nodes" value="5" />
              <Stat label="quant modes" value="5" />
              <Stat label="license" value="MIT" />
            </div>
          </div>

          {/* Right: abstract algorithmic art */}
          <div className="lg:col-span-5 relative wobble-in">
            <div className="relative">
              <div className="absolute -inset-3 sticker rounded-[3px] rotate-[0.6deg]" />
              <div className="relative p-4">
                <AlgorithmicArt className="w-full h-auto" />
              </div>
              <p className="mt-3 text-center font-serif italic text-[var(--color-text-tertiary)] text-[15px]">
                fig. 1. seed 7.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-l-2 border-[var(--color-border-default)] pl-3">
      <div className="font-mono text-[26px] font-semibold tracking-tight-display text-[var(--color-text-primary)]">
        {value}
      </div>
      <div className="mt-1 text-[10.5px] uppercase tracking-[0.14em] text-[var(--color-text-tertiary)] font-medium">
        {label}
      </div>
    </div>
  );
}
