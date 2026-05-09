import Link from "next/link";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 bg-grid pointer-events-none" />
      <div className="relative mx-auto max-w-[1200px] px-6 pt-24 pb-32">
        <div className="inline-flex items-center gap-2 rounded-full border border-[var(--color-border-default)] bg-[var(--color-bg-elevated)] px-3 py-1 mb-8">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-success)] animate-pulse" />
          <span className="text-xs text-[var(--color-text-secondary)]">
            v0.1 — open-source core on GitHub
          </span>
        </div>

        <h1 className="text-[clamp(2.5rem,6vw,3.5rem)] font-bold tracking-display leading-[1.05] max-w-3xl">
          From PyTorch to silicon{" "}
          <span className="text-[var(--color-accent)]">in minutes.</span>
        </h1>

        <p className="mt-6 max-w-2xl text-[18px] text-[var(--color-text-secondary)] leading-relaxed">
          ASICify compiles trained models into hardware-ready specifications.
          Synthesizable Verilog, area estimates across foundry nodes, FPGA
          reference implementations — all from a model checkpoint.
        </p>

        <div className="mt-8 flex items-center gap-3">
          <Button asChild size="lg">
            <Link href="/playground">Try the demo →</Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <a
              href="https://github.com/asicify/asicify"
              target="_blank"
              rel="noreferrer"
            >
              View on GitHub
            </a>
          </Button>
        </div>

        <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl">
          <Stat label="Models supported" value="30+" />
          <Stat label="Hardware targets" value="11" />
          <Stat label="Compression ratio" value="40×" />
          <Stat label="Time to first RTL" value="< 10 min" />
        </div>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-l border-[var(--color-border-default)] pl-4">
      <div className="font-mono text-2xl font-semibold tracking-tight-display">
        {value}
      </div>
      <div className="mt-1 text-xs uppercase tracking-[0.08em] text-[var(--color-text-tertiary)]">
        {label}
      </div>
    </div>
  );
}
