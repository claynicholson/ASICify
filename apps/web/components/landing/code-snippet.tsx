import { SectionHeader } from "@/components/landing/section-header";

const DIM = "oklch(0.97 0.005 80 / 0.45)";
const BRIGHT = "oklch(0.97 0.005 80 / 0.95)";
const OK = "oklch(0.82 0.08 150)";

export function CodeSnippet() {
  return (
    <section className="mx-auto max-w-[1200px] px-6 py-24">
      <SectionHeader index="04" title="Command line" />

      <div className="grid grid-cols-1 md:grid-cols-12 gap-10 items-start">
        <p className="md:col-span-4 text-[var(--color-text-secondary)] leading-[1.65] text-[16px] max-w-[44ch]">
          The same compiler drives the CLI, the REST API, and the web
          playground, so outputs and config hashes are identical everywhere.
          Unzip the build directory and run <code className="font-mono text-[14px] text-[var(--color-text-primary)]">make sim</code> or{" "}
          <code className="font-mono text-[14px] text-[var(--color-text-primary)]">make synth-yosys</code>.
        </p>

        <div className="md:col-span-8 rounded-[3px] border border-[var(--color-bg-ink)] bg-[var(--color-bg-ink)] overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-[oklch(1_0_0_/_0.12)] font-mono text-[11px] tracking-[0.08em]">
            <span style={{ color: DIM }}>~/asicify</span>
            <span style={{ color: DIM }}>exit 0 · 4.2 s</span>
          </div>
          <pre className="font-mono text-[13px] leading-[1.7] p-5 overflow-x-auto m-0">
            <code style={{ color: BRIGHT }}>
              <span style={{ color: DIM }}>$</span>{" "}
              <span style={{ color: "var(--color-accent)" }}>asicify</span>{" "}
              compile gpt2 \{`\n`}
              {`    `}--quantization int4 \{`\n`}
              {`    `}--sparsity 2:4 \{`\n`}
              {`    `}--target tsmc28,ecp5{`\n\n`}
              <span style={{ color: OK }}>✓</span> Parsed model graph
              <span style={{ color: DIM }}>{"  "}(124M params, 12 layers)</span>
              {`\n`}
              <span style={{ color: OK }}>✓</span> Quantized to INT4
              <span style={{ color: DIM }}>{"      "}(perplexity 24.3 → 25.1)</span>
              {`\n`}
              <span style={{ color: OK }}>✓</span> Applied 2:4 sparsity
              <span style={{ color: DIM }}>{"    "}(50% zeros)</span>
              {`\n`}
              <span style={{ color: OK }}>✓</span> Generated RTL
              <span style={{ color: DIM }}>{"          "}(top.v + 47 modules)</span>
              {`\n`}
              <span style={{ color: OK }}>✓</span> Estimated{" "}
              <span style={{ color: "var(--color-accent)" }}>tsmc28</span>
              <span style={{ color: DIM }}>{"      "}(8.2 mm², $4.10 @ 100K)</span>
              {`\n`}
              <span style={{ color: OK }}>✓</span> Estimated{" "}
              <span style={{ color: "var(--color-accent)" }}>ecp5</span>
              <span style={{ color: DIM }}>{"        "}(LFE5UM5G-85, 78% LUT util)</span>
              {`\n\n`}
              Output: ./build/gpt2-int4-2_4/
            </code>
          </pre>
        </div>
      </div>
    </section>
  );
}
