import Link from "next/link";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
import { Button } from "@/components/ui/button";

export const metadata = {
  title: "About · ASICify",
  description: "An open compiler from PyTorch to Verilog.",
};

export default function AboutPage() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[760px] px-6 py-16">
        <div className="eyebrow mb-3">About</div>
        <h1 className="font-serif text-[clamp(2.5rem,5.5vw,3.5rem)] tracking-serif leading-[1.05]">
          About
        </h1>

        <div className="mt-8 space-y-6 text-[var(--color-text-secondary)] leading-relaxed text-[17px]">
          <p>
            ASICify is an open compiler that turns trained PyTorch models into
            hardware-ready specifications. It produces compressed weights,
            synthesizable RTL with hardwired multipliers, area estimates
            across foundry nodes, an FPGA reference implementation, and a
            Cocotb testbench.
          </p>
          <p>
            Custom silicon costs between $5 million and $30 million per
            tape-out and takes six to eighteen months. The bottleneck is not
            fabrication; the bottleneck is the translation from a trained
            model to working hardware. Most chip teams do that translation by
            hand, with specialist engineers writing the same boilerplate over
            and over.
          </p>
          <p>
            ASICify automates the boilerplate. Cadence and Synopsys built EDA
            tools for general-purpose chips, while ASICify targets one
            workflow: turning a trained inference model into a fixed-function
            accelerator.
          </p>
          <p>
            The compiler is the product, and the artifacts belong to whoever
            runs it. The supply chain is whoever the user already trusts. The
            project is MIT licensed.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card
            label="License"
            body="MIT licensed, so you can use, fork, modify, and ship it."
          />
          <Card
            label="Hardware targets"
            body="Eleven targets: SkyWater 130, GF22FDX, TSMC 28 / 16 / 7, Lattice ECP5, CrossLink-NX, Xilinx Artix-7, Kria, TinyTapeout, and chipIgnite."
          />
          <Card
            label="Status"
            body="Version 0.1, pre-1.0. The compiler spine is complete."
          />
        </div>

        <div className="mt-16 pt-8 border-t border-[var(--color-border-subtle)]">
          <h2 className="font-serif text-[1.875rem] tracking-serif mb-4">
            Get involved
          </h2>
          <p className="text-[var(--color-text-secondary)] leading-relaxed mb-6 text-[16px]">
            The highest-leverage contributions right now are adding hardware
            targets with cell-library citations, adding new quantization
            formats such as FP4, FP8, and MXFP, adding new layer kinds such
            as Mamba and MoE, and refining cost-model parameters using
            foundry data sheets.
          </p>
          <ul className="space-y-2 text-sm">
            <li className="flex gap-3">
              <span className="text-[var(--color-text-tertiary)] font-mono text-[11px] uppercase tracking-[0.14em] mt-1 w-20 flex-shrink-0">
                Source
              </span>
              <a
                href="https://github.com/claynicholson/asicify"
                target="_blank"
                rel="noreferrer"
                className="text-[var(--color-accent-deep)] hover:text-[var(--color-accent)] border-b border-[var(--color-accent)]"
              >
                github.com/claynicholson/asicify
              </a>
            </li>
            <li className="flex gap-3">
              <span className="text-[var(--color-text-tertiary)] font-mono text-[11px] uppercase tracking-[0.14em] mt-1 w-20 flex-shrink-0">
                Issues
              </span>
              <a
                href="https://github.com/claynicholson/asicify/issues"
                target="_blank"
                rel="noreferrer"
                className="text-[var(--color-accent-deep)] hover:text-[var(--color-accent)] border-b border-[var(--color-accent)]"
              >
                Bug reports and feature requests
              </a>
            </li>
            <li className="flex gap-3">
              <span className="text-[var(--color-text-tertiary)] font-mono text-[11px] uppercase tracking-[0.14em] mt-1 w-20 flex-shrink-0">
                Extend
              </span>
              <Link
                href="/docs/internals/extending"
                className="text-[var(--color-accent-deep)] hover:text-[var(--color-accent)] border-b border-[var(--color-accent)]"
              >
                Recipes for adding targets, primitives, and stages
              </Link>
            </li>
          </ul>

          <div className="mt-10 flex gap-3">
            <Button asChild size="md">
              <Link href="/playground">Open the playground</Link>
            </Button>
            <Button asChild variant="outline" size="md">
              <Link href="/docs">Read the docs</Link>
            </Button>
          </div>
        </div>

        <div className="mt-16 pt-8 border-t border-[var(--color-border-subtle)]">
          <h2 className="font-serif text-[1.875rem] tracking-serif mb-4">
            Acknowledgements
          </h2>
          <p className="text-[var(--color-text-secondary)] leading-relaxed text-[15px]">
            Thanks to Tri Dao and the HazyResearch team for Monarch matrices,
            Matt Venn for TinyTapeout, SkyWater and Efabless for the open-PDK
            movement, the Yosys and nextpnr maintainers for the open
            synthesis flow, and the Cocotb authors for making hardware
            verification feel like Python.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}

function Card({ label, body }: { label: string; body: string }) {
  return (
    <div className="sticker rounded-[3px] p-4">
      <div className="eyebrow mb-2">{label}</div>
      <p className="text-[14px] text-[var(--color-text-secondary)] leading-relaxed">
        {body}
      </p>
    </div>
  );
}
