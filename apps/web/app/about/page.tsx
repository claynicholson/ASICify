import Link from "next/link";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";

export const metadata = {
  title: "About · ASICify",
  description: "An open-source compiler for AI silicon.",
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
          About this project
        </h1>

        <div className="mt-8 space-y-6 text-[var(--color-text-secondary)] leading-relaxed">
          <p>
            ASICify is an open-source compiler that turns trained neural
            networks into hardware-ready specifications. Submit a model and
            get back compressed weights, synthesizable RTL with hardwired
            multipliers, area estimates across foundry nodes, an FPGA
            reference implementation, and a verified Cocotb testbench.
          </p>
          <p>
            Custom AI silicon costs $5 to 30 million per tape-out and takes
            6 to 18 months. Fabrication isn&apos;t the bottleneck. The
            model-to-hardware translation is. Most chip companies and edge-AI
            deployers do that translation by hand today, with specialist
            engineers writing the same boilerplate over and over.
          </p>
          <p>
            ASICify automates the boilerplate so people can focus on
            cell-level and process-level engineering. Cadence and Synopsys
            built EDA for general-purpose chips. ASICify targets one
            workflow: turning a trained inference network into a
            fixed-function accelerator.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card label="License" body="MIT. Free to use, fork, modify, and ship in commercial products." />
          <Card label="Hardware targets" body="Eleven supported, from SkyWater 130 to TSMC 7nm to Lattice and Xilinx FPGAs." />
          <Card label="Status" body="Pre-1.0. The MVP spine is complete; real model parsing and validation are next." />
        </div>

        <div className="mt-16 pt-8 border-t border-[var(--color-border-subtle)]">
          <h2 className="text-xl font-semibold tracking-tight-display mb-4">
            Get involved
          </h2>
          <p className="text-[var(--color-text-secondary)] leading-relaxed mb-6">
            ASICify is community-built. The high-leverage areas right now:
            adding hardware targets with cell-library citations, new
            quantization formats (FP4, FP8, MXFP), new layer kinds (Mamba,
            MoE), and refining cost-model parameters with foundry data
            sheets.
          </p>
          <ul className="space-y-2 text-sm">
            <li className="flex gap-3">
              <span className="text-[var(--color-text-tertiary)] font-mono text-xs uppercase tracking-[0.08em] mt-0.5 w-20 flex-shrink-0">
                Source
              </span>
              <a
                href="https://github.com/claynicholson/asicify"
                target="_blank"
                rel="noreferrer"
                className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)]"
              >
                github.com/claynicholson/asicify
              </a>
            </li>
            <li className="flex gap-3">
              <span className="text-[var(--color-text-tertiary)] font-mono text-xs uppercase tracking-[0.08em] mt-0.5 w-20 flex-shrink-0">
                Issues
              </span>
              <a
                href="https://github.com/claynicholson/asicify/issues"
                target="_blank"
                rel="noreferrer"
                className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)]"
              >
                Bug reports and feature requests
              </a>
            </li>
            <li className="flex gap-3">
              <span className="text-[var(--color-text-tertiary)] font-mono text-xs uppercase tracking-[0.08em] mt-0.5 w-20 flex-shrink-0">
                Discuss
              </span>
              <a
                href="https://github.com/claynicholson/asicify/discussions"
                target="_blank"
                rel="noreferrer"
                className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)]"
              >
                GitHub Discussions for design questions
              </a>
            </li>
            <li className="flex gap-3">
              <span className="text-[var(--color-text-tertiary)] font-mono text-xs uppercase tracking-[0.08em] mt-0.5 w-20 flex-shrink-0">
                Extend
              </span>
              <Link
                href="/docs/internals/extending"
                className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)]"
              >
                Recipes for adding targets, primitives, and stages
              </Link>
            </li>
          </ul>

          <div className="mt-10 flex gap-3">
            <Link
              href="/playground"
              className="inline-flex items-center justify-center h-9 px-4 rounded-[6px] bg-[var(--color-accent)] text-[#0A0B0E] text-sm font-medium hover:brightness-110"
            >
              Open the playground
            </Link>
            <Link
              href="/docs"
              className="inline-flex items-center justify-center h-9 px-4 rounded-[6px] border border-[var(--color-border-default)] text-sm font-medium hover:bg-[var(--color-bg-elevated)]"
            >
              Read the docs
            </Link>
          </div>
        </div>

        <div className="mt-16 pt-8 border-t border-[var(--color-border-subtle)]">
          <h2 className="text-xl font-semibold tracking-tight-display mb-4">
            Acknowledgements
          </h2>
          <p className="text-[var(--color-text-secondary)] leading-relaxed text-sm">
            ASICify stands on a lot of open-source work. Tri Dao and the
            HazyResearch team for Monarch matrices. Matt Venn for
            TinyTapeout. SkyWater and Efabless for the open-PDK movement.
            The Yosys and nextpnr maintainers for the open synthesis flow.
            The Cocotb authors for making hardware verification feel like
            Python.
          </p>
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
