import Link from "next/link";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

import {
  DOC_SECTIONS,
  formatRelative,
  getAllSlugs,
  getDoc,
} from "@/lib/docs";

interface PageProps {
  params: Promise<{ slug: string[] }>;
}

export async function generateStaticParams() {
  return getAllSlugs().map((s) => ({ slug: s.split("/") }));
}

export async function generateMetadata({ params }: PageProps) {
  const { slug } = await params;
  const doc = await getDoc(slug.join("/"));
  if (!doc) return { title: "Not found — ASICify" };
  return {
    title: `${doc.label} — ASICify Docs`,
  };
}

export default async function DocPage({ params }: PageProps) {
  const { slug } = await params;
  const slugString = slug.join("/");
  const doc = await getDoc(slugString);
  if (!doc) notFound();

  const { prev, next } = neighborLinks(slugString);

  return (
    <article className="max-w-3xl">
      <div className="text-xs text-[var(--color-text-tertiary)] font-mono mb-4">
        <Link href="/docs" className="hover:text-[var(--color-text-secondary)]">
          Docs
        </Link>{" "}
        / {doc.slug}
      </div>

      <div className="prose-asicify">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
          components={{
            // Rewrite internal .md links → site routes
            a: ({ href, children, ...props }) => {
              const rewritten = rewriteHref(href);
              const isExternal = rewritten?.startsWith("http");
              return (
                <a
                  href={rewritten}
                  target={isExternal ? "_blank" : undefined}
                  rel={isExternal ? "noreferrer" : undefined}
                  {...props}
                >
                  {children}
                </a>
              );
            },
          }}
        >
          {doc.body}
        </ReactMarkdown>
      </div>

      <div className="mt-12 pt-6 border-t border-[var(--color-border-subtle)] flex items-center justify-between text-xs text-[var(--color-text-tertiary)] font-mono">
        <span>
          Last updated {formatRelative(doc.lastUpdated)} · {doc.sourcePath}
        </span>
        <a
          href={`https://github.com/asicify/asicify/edit/main/${doc.sourcePath}`}
          target="_blank"
          rel="noreferrer"
          className="hover:text-[var(--color-text-secondary)]"
        >
          Edit on GitHub →
        </a>
      </div>

      <nav className="mt-8 grid grid-cols-2 gap-3">
        {prev ? (
          <Link
            href={`/docs/${prev.slug}`}
            className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-4 hover:border-[var(--color-border-default)] transition-colors"
          >
            <div className="text-[10px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-1">
              ← Previous
            </div>
            <div className="text-sm font-medium">{prev.label}</div>
          </Link>
        ) : (
          <div />
        )}
        {next ? (
          <Link
            href={`/docs/${next.slug}`}
            className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-4 hover:border-[var(--color-border-default)] transition-colors text-right"
          >
            <div className="text-[10px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-1">
              Next →
            </div>
            <div className="text-sm font-medium">{next.label}</div>
          </Link>
        ) : (
          <div />
        )}
      </nav>
    </article>
  );
}

/** Rewrite `../foo.md` and `foo.md` style links into `/docs/foo` site routes. */
function rewriteHref(href: string | undefined): string | undefined {
  if (!href) return href;
  if (href.startsWith("http") || href.startsWith("mailto:") || href.startsWith("#")) {
    return href;
  }

  // Strip leading ../ and ./ segments
  let h = href.replace(/^(\.\.\/)+/, "").replace(/^\.\//, "");

  // Map "docs/foo.md" → "/docs/foo"
  if (h.startsWith("docs/")) h = h.slice(5);

  // Strip .md extension
  h = h.replace(/\.md$/i, "");

  // External-to-docs source files (apps/web/lib/foo.ts) → GitHub link
  if (h.startsWith("apps/") || h.startsWith("packages/") || h.startsWith("infra/")) {
    return `https://github.com/asicify/asicify/blob/main/${h}`;
  }

  // Anything else under the repo root we don't recognize → leave alone
  if (h.includes("/") || /^[a-z][a-z0-9-]*$/.test(h)) {
    // Looks like a docs slug
    return `/docs/${h}`;
  }

  return href;
}

/** Compute prev/next links from the curated DOC_SECTIONS order. */
function neighborLinks(slug: string) {
  const flat = DOC_SECTIONS.flatMap((s) => s.items);
  const idx = flat.findIndex((d) => d.slug === slug);
  return {
    prev: idx > 0 ? flat[idx - 1] : null,
    next: idx >= 0 && idx < flat.length - 1 ? flat[idx + 1] : null,
  };
}
