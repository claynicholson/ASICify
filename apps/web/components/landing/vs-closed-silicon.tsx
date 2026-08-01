const ROWS: {
  axis: string;
  ours: string;
  theirs: string;
}[] = [
  {
    axis: "Form factor",
    ours: "A compiler binary that you run locally.",
    theirs: "A hosted service that you submit a model to.",
  },
  {
    axis: "Artifacts",
    ours: "Synthesizable Verilog, a Cocotb testbench, and a cost report on disk.",
    theirs: "Whatever the platform chooses to expose.",
  },
  {
    axis: "Targets",
    ours: "Eleven targets, covering both ASIC nodes and FPGAs.",
    theirs: "A single proprietary silicon path.",
  },
  {
    axis: "Cost model",
    ours: "Documented in /docs/methodology with public PDK citations.",
    theirs: "Undisclosed.",
  },
  {
    axis: "License",
    ours: "MIT licensed.",
    theirs: "Closed source.",
  },
  {
    axis: "Lock-in",
    ours: "Switch foundries by changing one flag.",
    theirs: "A single fab and a single vendor.",
  },
  {
    axis: "Time to first output",
    ours: "A few minutes in a local terminal.",
    theirs: "A sales cycle.",
  },
];

export function VsClosedSilicon() {
  return (
    <section id="vs" className="bg-[var(--color-bg-ink)] text-[var(--color-text-on-ink)]">
      <div className="mx-auto max-w-[1200px] px-6 py-20">
        <div className="border-t border-[oklch(1_0_0_/_0.18)] pt-5 mb-12 flex items-baseline gap-6">
          <span className="font-mono text-[13px] tracking-[0.1em] text-[var(--color-accent)]">
            03
          </span>
          <h2 className="display-sub text-[clamp(1.75rem,3.2vw,2.375rem)]">
            Against closed silicon platforms
          </h2>
        </div>

        {/* Column headers */}
        <div className="hidden md:grid grid-cols-12 gap-6 pb-3">
          <div className="col-span-3" />
          <div className="col-span-5 flex items-center gap-3">
            <span className="label-mono !text-[var(--color-accent)]">
              ASICify
            </span>
            <span className="h-px flex-1 bg-[var(--color-accent)]" />
          </div>
          <div className="col-span-4 flex items-center gap-3">
            <span className="label-mono !text-[oklch(1_0_0_/_0.45)]">
              Closed platforms
            </span>
            <span className="h-px flex-1 bg-[oklch(1_0_0_/_0.2)]" />
          </div>
        </div>

        <div className="border-t border-[oklch(1_0_0_/_0.14)]">
          {ROWS.map((row) => (
            <div
              key={row.axis}
              className="grid grid-cols-12 gap-x-6 gap-y-2 py-4 border-b border-[oklch(1_0_0_/_0.1)] items-baseline"
            >
              <div className="col-span-12 md:col-span-3 label-mono !text-[oklch(1_0_0_/_0.45)]">
                {row.axis}
              </div>
              <div className="col-span-6 md:col-span-5 text-[15px] leading-[1.6] text-[oklch(0.97_0.005_80_/_0.95)]">
                {row.ours}
              </div>
              <div className="col-span-6 md:col-span-4 text-[15px] leading-[1.6] text-[oklch(0.97_0.005_80_/_0.5)]">
                {row.theirs}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
