import Link from "next/link";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
import { Button } from "@/components/ui/button";

const TABS = ["Overview", "Compression", "Hardware", "RTL", "Verification", "Report"] as const;

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[1200px] px-6 py-8">
        <Link
          href="/projects"
          className="text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] font-mono"
        >
          ← projects
        </Link>

        <div className="mt-3 flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-bold tracking-tight-display">
              TinyLlama 1.1B → TSMC 28nm
            </h1>
            <div className="mt-2 font-mono text-xs text-[var(--color-text-tertiary)]">
              {id} · INT4 · 2:4 sparsity · 50% reduction
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              Re-run
            </Button>
            <Button size="sm">Download package (zip)</Button>
          </div>
        </div>

        <nav className="mt-8 flex gap-1 border-b border-[var(--color-border-subtle)]">
          {TABS.map((tab, i) => (
            <button
              key={tab}
              className={`px-4 py-2.5 text-sm transition-colors border-b-2 ${
                i === 0
                  ? "border-[var(--color-accent)] text-[var(--color-text-primary)]"
                  : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>

        <div className="mt-8 grid grid-cols-12 gap-6">
          <section className="col-span-8 space-y-6">
            <div className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-6">
              <h2 className="text-base font-semibold mb-4">Pipeline status</h2>
              <ol className="space-y-3">
                {[
                  { name: "Parse model graph", time: "2.1s", done: true },
                  { name: "Quantize to INT4", time: "45s", done: true },
                  { name: "Apply 2:4 sparsity", time: "12s", done: true },
                  { name: "Validate quality", time: "3m 18s", done: true },
                  { name: "Generate RTL", time: "28s", done: true },
                  { name: "Estimate hardware", time: "1.4s", done: true },
                ].map((s) => (
                  <li key={s.name} className="flex justify-between text-sm">
                    <div className="flex items-center gap-2.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-success)]" />
                      <span>{s.name}</span>
                    </div>
                    <span className="font-mono text-xs text-[var(--color-text-tertiary)]">
                      {s.time}
                    </span>
                  </li>
                ))}
              </ol>
            </div>

            <div className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-6">
              <h2 className="text-base font-semibold mb-4">Quality metrics</h2>
              <dl className="grid grid-cols-3 gap-6">
                <Stat label="Baseline ppl" value="9.20" />
                <Stat label="Compressed ppl" value="9.71" />
                <Stat label="Δ" value="+5.5%" tone="warn" />
              </dl>
            </div>
          </section>

          <aside className="col-span-4 space-y-6">
            <div className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-5">
              <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
                Quick metrics
              </div>
              <dl className="space-y-3">
                <Row label="Area" value="12.4 mm²" />
                <Row label="Max clock" value="1000 MHz" />
                <Row label="Throughput" value="142 tok/s" />
                <Row label="Energy / tok" value="3.8 mJ" />
                <Row label="Cost @ 100K" value="$2.40" />
              </dl>
            </div>
          </aside>
        </div>
      </main>
      <Footer />
    </>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "warn";
}) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-1">
        {label}
      </dt>
      <dd
        className="font-mono text-2xl font-semibold"
        style={
          tone === "warn"
            ? { color: "var(--color-warning)" }
            : undefined
        }
      >
        {value}
      </dd>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <dt className="text-[var(--color-text-secondary)]">{label}</dt>
      <dd className="font-mono">{value}</dd>
    </div>
  );
}
