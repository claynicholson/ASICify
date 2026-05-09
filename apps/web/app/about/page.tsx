import Link from "next/link";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";

export const metadata = {
  title: "About — ASICify",
  description: "The compiler for AI silicon — vision, mission, and contact.",
};

export default function AboutPage() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[760px] px-6 py-16">
        <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
          About
        </div>
        <h1 className="text-[2.5rem] font-bold tracking-tight-display leading-[1.1]">
          The horizontal layer underneath every AI chip company.
        </h1>

        <div className="mt-8 space-y-6 text-[var(--color-text-secondary)] leading-relaxed">
          <p>
            Custom AI silicon costs $5–30M per tape-out and takes 6–18 months.
            The bottleneck isn't fabrication — it's the model-to-hardware
            translation. Every chip company and edge-AI deployer currently does
            that translation by hand, with expensive specialist engineers.
          </p>
          <p>
            ASICify is an automated compiler for that translation. Upload a
            model, get back: aggressively compressed weights, synthesizable RTL
            with hardwired multipliers, area estimates across foundry nodes, an
            FPGA reference implementation, and a verified testbench. We work
            with you to deploy on TinyTapeout, chipIgnite, FPGA-as-a-Service,
            or commercial fabs.
          </p>
          <p>
            Cadence and Synopsys built EDA for general-purpose chips. We're
            building it for one thing: turning a trained network into a
            fixed-function inference accelerator.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card label="Open source" body="MIT-licensed core. The compression pipeline and RTL generator are on GitHub." />
          <Card label="Hardware targets" body="11 supported: SkyWater 130, GF22FDX, TSMC 28/16/7, Lattice, Xilinx, shuttles." />
          <Card label="Time to first RTL" body="Under 10 minutes from checkpoint to a synthesizable Verilog package." />
        </div>

        <div className="mt-16 pt-8 border-t border-[var(--color-border-subtle)]">
          <h2 className="text-xl font-semibold tracking-tight-display mb-4">Get in touch</h2>
          <ul className="space-y-2 text-sm">
            <li>
              <span className="text-[var(--color-text-tertiary)] font-mono text-xs uppercase tracking-[0.08em] mr-3">
                Email
              </span>
              <a
                href="mailto:hello@asicify.com"
                className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)]"
              >
                hello@asicify.com
              </a>
            </li>
            <li>
              <span className="text-[var(--color-text-tertiary)] font-mono text-xs uppercase tracking-[0.08em] mr-3">
                GitHub
              </span>
              <a
                href="https://github.com/asicify/asicify"
                target="_blank"
                rel="noreferrer"
                className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)]"
              >
                github.com/asicify/asicify
              </a>
            </li>
            <li>
              <span className="text-[var(--color-text-tertiary)] font-mono text-xs uppercase tracking-[0.08em] mr-3">
                Discord
              </span>
              <a
                href="https://discord.gg/asicify"
                target="_blank"
                rel="noreferrer"
                className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)]"
              >
                discord.gg/asicify
              </a>
            </li>
          </ul>

          <div className="mt-10 flex gap-3">
            <Link
              href="/playground"
              className="inline-flex items-center justify-center h-9 px-4 rounded-[6px] bg-[var(--color-accent)] text-[#0A0B0E] text-sm font-medium hover:brightness-110"
            >
              Try the demo
            </Link>
            <Link
              href="/docs"
              className="inline-flex items-center justify-center h-9 px-4 rounded-[6px] border border-[var(--color-border-default)] text-sm font-medium hover:bg-[var(--color-bg-elevated)]"
            >
              Read the docs
            </Link>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}

function Card({ label, body }: { label: string; body: string }) {
  return (
    <div className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-4">
      <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-2">
        {label}
      </div>
      <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
        {body}
      </p>
    </div>
  );
}
