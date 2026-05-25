import { InkCheck, InkX } from "@/components/ornaments";

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
    ours:
      "Synthesizable Verilog, a Cocotb testbench, and a cost report on disk.",
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
    ours: "You can switch foundries by changing one flag.",
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
    <section id="vs" className="relative">
      <div className="bg-[var(--color-bg-ink)] text-[var(--color-text-on-ink)]">
        <div className="mx-auto max-w-[1200px] px-6 py-24">
          <div className="max-w-2xl mb-12">
            <div
              className="eyebrow mb-3"
              style={{ color: "rgba(244,239,230,0.55)" }}
            >
              Comparison
            </div>
            <h2 className="font-serif text-[clamp(2.25rem,4.5vw,3rem)] leading-[1.05] tracking-serif">
              ASICify vs. closed silicon platforms
            </h2>
          </div>

          {/* Column headers */}
          <div className="grid grid-cols-12 gap-4 mb-3">
            <div className="col-span-12 md:col-span-3" />
            <div className="col-span-6 md:col-span-4 lg:col-span-5">
              <div className="flex items-center gap-3">
                <span
                  className="font-mono text-[11px] tracking-[0.18em] uppercase"
                  style={{ color: "rgba(244,239,230,0.55)" }}
                >
                  ASICify
                </span>
                <span className="h-px flex-1 bg-[var(--color-accent)] opacity-60" />
              </div>
            </div>
            <div className="col-span-6 md:col-span-5 lg:col-span-4">
              <div className="flex items-center gap-3">
                <span
                  className="font-mono text-[11px] tracking-[0.18em] uppercase"
                  style={{ color: "rgba(244,239,230,0.55)" }}
                >
                  Closed silicon platforms
                </span>
                <span
                  className="h-px flex-1"
                  style={{ background: "rgba(244,239,230,0.18)" }}
                />
              </div>
            </div>
          </div>

          {/* Rows */}
          <div
            className="border-t"
            style={{ borderColor: "rgba(244,239,230,0.12)" }}
          >
            {ROWS.map((row) => (
              <div
                key={row.axis}
                className="grid grid-cols-12 gap-4 py-5 border-b items-start"
                style={{ borderColor: "rgba(244,239,230,0.10)" }}
              >
                <div
                  className="col-span-12 md:col-span-3 font-mono text-[11px] tracking-[0.16em] uppercase pt-1"
                  style={{ color: "rgba(244,239,230,0.50)" }}
                >
                  {row.axis}
                </div>
                <div className="col-span-6 md:col-span-4 lg:col-span-5 flex gap-3 text-[15px] leading-relaxed">
                  <InkCheck className="w-4 h-4 mt-1 flex-shrink-0 text-[var(--color-accent)]" />
                  <span style={{ color: "rgba(244,239,230,0.95)" }}>
                    {row.ours}
                  </span>
                </div>
                <div className="col-span-6 md:col-span-5 lg:col-span-4 flex gap-3 text-[15px] leading-relaxed">
                  <InkX
                    className="w-4 h-4 mt-1 flex-shrink-0"
                    style={{ color: "rgba(244,239,230,0.35)" }}
                  />
                  <span style={{ color: "rgba(244,239,230,0.55)" }}>
                    {row.theirs}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
