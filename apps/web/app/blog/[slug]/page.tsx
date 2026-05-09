import Link from "next/link";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";

export const metadata = {
  title: "Post — ASICify",
};

export default async function BlogPost({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[720px] px-6 py-16">
        <Link
          href="/blog"
          className="text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] font-mono mb-6 inline-block"
        >
          ← Back to blog
        </Link>

        <div className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-8 text-center">
          <div className="font-mono text-xs text-[var(--color-text-tertiary)] mb-3">
            /blog/{slug}
          </div>
          <h1 className="text-2xl font-bold tracking-tight-display mb-3">
            Post not yet published
          </h1>
          <p className="text-sm text-[var(--color-text-secondary)] max-w-sm mx-auto">
            This post is in draft. Posts will be sourced from{" "}
            <code className="font-mono text-xs bg-[var(--color-bg-overlay)] px-1.5 py-0.5 rounded">
              content/blog/{slug}.md
            </code>{" "}
            once the blog goes live.
          </p>
          <div className="mt-6">
            <Link
              href="/blog"
              className="inline-flex items-center gap-2 text-sm text-[var(--color-accent)] hover:text-[var(--color-accent-hover)]"
            >
              ← Other posts
            </Link>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
