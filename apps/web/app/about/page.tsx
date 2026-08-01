import Link from "next/link";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
import { Button } from "@/components/ui/button";

export const metadata = {
  title: "About · ASICify",
  description: "An open compiler from PyTorch to Verilog.",
};

const FACTS = [
  {
    label: "License",
    body: "MIT. Use, fork, modify, and ship it.",
  },
  {
    label: "Hardware targets",
    body: "SkyWater 130 · GF22FDX · TSMC 28 / 16 / 7 · Lattice ECP5 · CrossLink-NX · Xilinx Artix-7 · Kria · TinyTapeout · chipIgnite",
  },
  {
    label: "Status",
    body: "v0.1, pre-1.0. The compiler spine is complete.",
  },
];

export default function AboutPage() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[760px] px-6 py-16">
        <h1 className="display text-[clamp(2.5rem,5.5vw,3.5rem)]">About</h1>

        <div className="mt-8 space-y-6 text-[var(--color-text-secondary)] leading-[1.65] text-[17px]">
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

        <dl className="mt-12 border-t border-[var(--color-border-default)]">
          {FACTS.map((f) => (
            <div
              key={f.label}
              className="grid grid-cols-12 gap-4 py-4 border-b border-[var(--color-border-subtle)]"
            >
              <dt className="col-span-12 sm:col-span-4 label-mono pt-1">
                {f.label}
              </dt>
              <dd className="col-span-12 sm:col-span-8 m-0 text-[15px] text-[var(--color-text-primary)] leading-[1.6]">
                {f.body}
              </dd>
            </div>
          ))}
        </dl>

        <div className="mt-16">
          <h2 className="display-sub text-[1.75rem] mb-4">Get involved</h2>
          <p className="text-[var(--color-text-secondary)] leading-[1.65] mb-6 text-[16px]">
            The highest-leverage contributions right now are adding hardware
            targets with cell-library citations, adding new quantization
            formats such as FP4, FP8, and MXFP, adding new layer kinds such
            as Mamba and MoE, and refining cost-model parameters using
            foundry data sheets.
          </p>
          <ul className="space-y-2.5 text-sm m-0 p-0 list-none">
            <li className="flex gap-3 items-baseline">
              <span className="label-mono w-20 flex-shrink-0">Source</span>
              <a
                href="https://github.com/claynicholson/asicify"
                target="_blank"
                rel="noreferrer"
                className="text-[var(--color-accent-deep)] border-b border-[var(--color-accent)] hover:bg-[var(--color-accent-muted)]"
              >
                github.com/claynicholson/asicify
              </a>
            </li>
            <li className="flex gap-3 items-baseline">
              <span className="label-mono w-20 flex-shrink-0">Issues</span>
              <a
                href="https://github.com/claynicholson/asicify/issues"
                target="_blank"
                rel="noreferrer"
                className="text-[var(--color-accent-deep)] border-b border-[var(--color-accent)] hover:bg-[var(--color-accent-muted)]"
              >
                Bug reports and feature requests
              </a>
            </li>
            <li className="flex gap-3 items-baseline">
              <span className="label-mono w-20 flex-shrink-0">Extend</span>
              <Link
                href="/docs/internals/extending"
                className="text-[var(--color-accent-deep)] border-b border-[var(--color-accent)] hover:bg-[var(--color-accent-muted)]"
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
          <h2 className="display-sub text-[1.75rem] mb-4">Acknowledgements</h2>
          <p className="text-[var(--color-text-secondary)] leading-[1.65] text-[15px]">
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
