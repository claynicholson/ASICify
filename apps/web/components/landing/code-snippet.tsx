export function CodeSnippet() {
  return (
    <section className="mx-auto max-w-[1200px] px-6 py-24">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
        <div>
          <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
            CLI
          </div>
          <h2 className="text-[2.5rem] font-bold tracking-tight-display leading-[1.1] mb-4">
            Same compiler, scriptable.
          </h2>
          <p className="text-[var(--color-text-secondary)] leading-relaxed mb-6">
            The web playground is for exploration. Production pipelines use
            the CLI or REST API. Same compiler underneath.
          </p>
          <ul className="space-y-3 text-sm">
            <li className="flex gap-3">
              <span className="text-[var(--color-success)] mt-1">▸</span>
              <span className="text-[var(--color-text-secondary)]">
                Reproducible: every artifact pinned to a config hash
              </span>
            </li>
            <li className="flex gap-3">
              <span className="text-[var(--color-success)] mt-1">▸</span>
              <span className="text-[var(--color-text-secondary)]">
                Hooks for hardware-aware fine-tuning in your training loop
              </span>
            </li>
            <li className="flex gap-3">
              <span className="text-[var(--color-success)] mt-1">▸</span>
              <span className="text-[var(--color-text-secondary)]">
                CI-friendly: synthesize on push, fail on quality regressions
              </span>
            </li>
          </ul>
        </div>

        <div className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[var(--color-border-subtle)]">
            <div className="flex gap-1.5">
              <div className="h-2.5 w-2.5 rounded-full bg-[var(--color-border-default)]" />
              <div className="h-2.5 w-2.5 rounded-full bg-[var(--color-border-default)]" />
              <div className="h-2.5 w-2.5 rounded-full bg-[var(--color-border-default)]" />
            </div>
            <span className="font-mono text-xs text-[var(--color-text-tertiary)] ml-2">
              terminal
            </span>
          </div>
          <pre className="font-mono text-[13px] leading-relaxed p-5 overflow-x-auto">
            <code className="text-[var(--color-text-secondary)]">
{`$ asicify compile gpt2 \\
    --quantization int4 \\
    --sparsity 2:4 \\
    --target tsmc28,ecp5

`}<span className="text-[var(--color-success)]">{`✓`}</span>{` Parsed model graph (124M params, 12 layers)
`}<span className="text-[var(--color-success)]">{`✓`}</span>{` Quantized to INT4   `}<span className="text-[var(--color-text-tertiary)]">{`(perplexity 24.3 to 25.1)`}</span>{`
`}<span className="text-[var(--color-success)]">{`✓`}</span>{` Applied 2:4 sparsity `}<span className="text-[var(--color-text-tertiary)]">{`(50% zeros)`}</span>{`
`}<span className="text-[var(--color-success)]">{`✓`}</span>{` Generated RTL       `}<span className="text-[var(--color-text-tertiary)]">{`(top.v + 47 modules)`}</span>{`
`}<span className="text-[var(--color-success)]">{`✓`}</span>{` Estimated `}<span className="text-[var(--color-accent)]">{`tsmc28`}</span>{`     `}<span className="text-[var(--color-text-tertiary)]">{`(8.2 mm², $4.10 @ 100K)`}</span>{`
`}<span className="text-[var(--color-success)]">{`✓`}</span>{` Estimated `}<span className="text-[var(--color-accent)]">{`ecp5`}</span>{`       `}<span className="text-[var(--color-text-tertiary)]">{`(LFE5UM5G-85, 78% LUT util)`}</span>{`

`}<span className="text-[var(--color-text-primary)]">Output:</span>{` ./build/gpt2-int4-2_4/`}
            </code>
          </pre>
        </div>
      </div>
    </section>
  );
}
