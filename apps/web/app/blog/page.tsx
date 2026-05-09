import Link from "next/link";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";

export const metadata = {
  title: "Blog — ASICify",
  description: "Technical writing on AI silicon, compression, and hardware-aware ML.",
};

// Placeholder until the blog has real posts. Each post will live as a markdown
// file under content/blog/<slug>.md and be rendered by /blog/[slug]/page.tsx.
const PLANNED_POSTS = [
  {
    slug: "why-asicify",
    title: "Why we're building ASICify",
    excerpt:
      "Custom silicon for AI inference is becoming mainstream. The bottleneck isn't fabrication — it's the model-to-hardware translation. Here's the case for a horizontal compiler underneath every chip company.",
    date: "Coming soon",
  },
  {
    slug: "ternary-revisited",
    title: "Ternary networks, revisited for hardware",
    excerpt:
      "Ternary weights {-α, 0, +α} collapse multipliers into sign-flip muxes — ~3 LUTs per MAC. Recent results on TinyLlama suggest the quality cost is smaller than the conventional wisdom says.",
    date: "Coming soon",
  },
  {
    slug: "monarch-on-silicon",
    title: "Monarch matrices on silicon",
    excerpt:
      "Block-diagonal factorization gets you O((m+n)·sqrt(mn)) parameters. Mapping that into a layer-pipelined Verilog design — what's hard, what's not.",
    date: "Coming soon",
  },
];

export default function BlogIndex() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[800px] px-6 py-16">
        <div className="mb-12">
          <h1 className="text-[2.5rem] font-bold tracking-tight-display">Blog</h1>
          <p className="mt-3 text-[var(--color-text-secondary)]">
            Build logs, technical deep dives, and field notes from the
            hardware-software boundary.
          </p>
        </div>

        <div className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-5 mb-10">
          <div className="flex items-center gap-2 text-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-warning)]" />
            <span className="text-[var(--color-text-secondary)]">
              The blog is in draft. Subscribe to be notified when posts go live.
            </span>
          </div>
        </div>

        <ul className="space-y-1">
          {PLANNED_POSTS.map((post) => (
            <li key={post.slug}>
              <Link
                href={`/blog/${post.slug}`}
                className="block group rounded-[6px] -mx-4 px-4 py-5 hover:bg-[var(--color-bg-elevated)] transition-colors"
              >
                <div className="flex items-baseline justify-between gap-4 mb-1">
                  <h2 className="text-lg font-semibold group-hover:text-[var(--color-accent)]">
                    {post.title}
                  </h2>
                  <span className="font-mono text-[10px] text-[var(--color-text-tertiary)] uppercase tracking-[0.08em] flex-shrink-0">
                    {post.date}
                  </span>
                </div>
                <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                  {post.excerpt}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      </main>
      <Footer />
    </>
  );
}
