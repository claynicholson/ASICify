import Link from "next/link";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

// Placeholder projects — wire up to /api/projects when auth is connected.
const PLACEHOLDER_PROJECTS = [
  {
    id: "p_demo_1",
    name: "TinyLlama 1.1B → TSMC 28nm",
    status: "complete" as const,
    updated: "2 hours ago",
    quantization: "INT4",
    target: "tsmc28",
    cost: "$2.40",
    area: "12.4 mm²",
  },
  {
    id: "p_demo_2",
    name: "DistilBERT → ECP5",
    status: "running" as const,
    updated: "12 minutes ago",
    quantization: "INT8",
    target: "ecp5",
    cost: "—",
    area: "—",
  },
  {
    id: "p_demo_3",
    name: "MobileNet V3 → TinyTapeout",
    status: "complete" as const,
    updated: "yesterday",
    quantization: "Ternary",
    target: "tinytapeout",
    cost: "$300",
    area: "0.16 mm²",
  },
];

export default function ProjectsPage() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[1200px] px-6 py-12">
        <div className="flex justify-between items-end mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight-display">
              Projects
            </h1>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              Each project pins one model to one compression config and one set
              of targets.
            </p>
          </div>
          <Button asChild>
            <Link href="/playground">+ New project</Link>
          </Button>
        </div>

        <div className="space-y-3">
          {PLACEHOLDER_PROJECTS.map((p) => (
            <Card
              key={p.id}
              className="hover:border-[var(--color-border-default)] transition-colors"
            >
              <Link href={`/projects/${p.id}`}>
                <CardContent className="p-5 flex items-center justify-between">
                  <div className="flex items-center gap-4 flex-1">
                    <StatusDot status={p.status} />
                    <div>
                      <div className="font-medium">{p.name}</div>
                      <div className="font-mono text-xs text-[var(--color-text-tertiary)] mt-0.5">
                        {p.id} · updated {p.updated}
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-4 gap-8 text-right">
                    <Stat label="Quant" value={p.quantization} />
                    <Stat label="Target" value={p.target} mono />
                    <Stat label="Area" value={p.area} mono />
                    <Stat label="Cost @ 100K" value={p.cost} mono />
                  </div>
                </CardContent>
              </Link>
            </Card>
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}

function StatusDot({ status }: { status: "complete" | "running" | "failed" }) {
  const color =
    status === "complete"
      ? "var(--color-success)"
      : status === "running"
        ? "var(--color-warning)"
        : "var(--color-error)";
  return (
    <div className="flex items-center gap-2">
      <span
        className="h-2 w-2 rounded-full"
        style={{
          backgroundColor: color,
          boxShadow: status === "running" ? `0 0 8px ${color}` : undefined,
        }}
      />
    </div>
  );
}

function Stat({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-1">
        {label}
      </div>
      <div className={mono ? "font-mono text-sm" : "text-sm"}>{value}</div>
    </div>
  );
}
