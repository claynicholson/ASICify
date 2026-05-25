export function CodeSnippet() {
  return (
    <section className="mx-auto max-w-[1200px] px-6 py-24">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
        <div>
          <div className="eyebrow mb-3">CLI</div>
          <h2 className="font-serif text-[clamp(2.25rem,4.5vw,3rem)] leading-[1.05] tracking-serif mb-4">
            Command line
          </h2>
          <p className="text-[var(--color-text-secondary)] leading-relaxed max-w-md text-[16px]">
            ASICify is also available as a CLI and a REST API. It uses the
            same compiler as the web playground, so the outputs and config
            hashes are identical.
          </p>
        </div>

        <div className="relative">
          <div
            className="absolute -inset-2 rounded-[4px]"
            style={{
              background: "var(--color-accent-muted)",
              transform: "rotate(0.7deg)",
            }}
          />
          <div className="relative rounded-[4px] border border-[var(--color-bg-ink)] bg-[var(--color-bg-ink)] overflow-hidden shadow-[0_18px_40px_-22px_rgba(31,27,22,0.4)]">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[rgba(244,239,230,0.12)]">
              <div className="flex gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full bg-[#E78A8A]" />
                <div className="h-2.5 w-2.5 rounded-full bg-[#E6C56A]" />
                <div className="h-2.5 w-2.5 rounded-full bg-[#9ED8A7]" />
              </div>
              <span className="font-mono text-xs text-[rgba(244,239,230,0.5)] ml-2 tracking-[0.1em]">
                ~/asicify
              </span>
            </div>
            <pre className="font-mono text-[13px] leading-[1.65] p-5 overflow-x-auto">
              <code style={{ color: "rgba(244,239,230,0.85)" }}>
                <span style={{ color: "rgba(244,239,230,0.4)" }}>$</span>{" "}
                <span style={{ color: "var(--color-accent)" }}>asicify</span>{" "}
                compile gpt2 \{`\n`}
                {`    `}--quantization int4 \{`\n`}
                {`    `}--sparsity 2:4 \{`\n`}
                {`    `}--target tsmc28,ecp5{`\n\n`}
                <span style={{ color: "#9ED8A7" }}>✓</span> Parsed model graph
                <span style={{ color: "rgba(244,239,230,0.45)" }}>
                  {"  "}(124M params, 12 layers)
                </span>
                {`\n`}
                <span style={{ color: "#9ED8A7" }}>✓</span> Quantized to INT4
                <span style={{ color: "rgba(244,239,230,0.45)" }}>
                  {"      "}(perplexity 24.3 → 25.1)
                </span>
                {`\n`}
                <span style={{ color: "#9ED8A7" }}>✓</span> Applied 2:4 sparsity
                <span style={{ color: "rgba(244,239,230,0.45)" }}>
                  {"    "}(50% zeros)
                </span>
                {`\n`}
                <span style={{ color: "#9ED8A7" }}>✓</span> Generated RTL
                <span style={{ color: "rgba(244,239,230,0.45)" }}>
                  {"          "}(top.v + 47 modules)
                </span>
                {`\n`}
                <span style={{ color: "#9ED8A7" }}>✓</span> Estimated{" "}
                <span style={{ color: "var(--color-accent)" }}>tsmc28</span>
                <span style={{ color: "rgba(244,239,230,0.45)" }}>
                  {"      "}(8.2 mm², $4.10 @ 100K)
                </span>
                {`\n`}
                <span style={{ color: "#9ED8A7" }}>✓</span> Estimated{" "}
                <span style={{ color: "var(--color-accent)" }}>ecp5</span>
                <span style={{ color: "rgba(244,239,230,0.45)" }}>
                  {"        "}(LFE5UM5G-85, 78% LUT util)
                </span>
                {`\n\n`}
                <span style={{ color: "rgba(244,239,230,0.95)" }}>Output:</span>{" "}
                ./build/gpt2-int4-2_4/
              </code>
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
}
