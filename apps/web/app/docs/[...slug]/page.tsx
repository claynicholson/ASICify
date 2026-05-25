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
  if (!doc) return { title: "Not found · ASICify" };
  return {
    title: `${doc.label} · ASICify Docs`,
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
            // Rewrite internal .md links → site routes, relative to the current doc.
            a: ({ href, children, ...props }) => {
              const rewritten = rewriteHref(href, doc.sourcePath);
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
          href={`https://github.com/claynicholson/asicify/edit/main/${doc.sourcePath}`}
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

/**
 * Rewrite a markdown link href into the correct site URL, resolving any
 * `./` and `../` segments against the current doc file's directory.
 *
 * `sourcePath` is the repo-root-relative path of the current markdown file,
 * e.g. "docs/internals/README.md" or "docs/codebase.md".
 *
 * Handles `.md`, `.md#fragment`, and `.md?query` patterns.
 */
function rewriteHref(
  href: string | undefined,
  sourcePath: string,
): string | undefined {
  if (!href) return href;
  if (
    href.startsWith("http") ||
    href.startsWith("mailto:") ||
    href.startsWith("#") ||
    href.startsWith("/")
  ) {
    return href;
  }

  // Split off any #fragment or ?query so the .md stripper still matches.
  const m = /^([^#?]*)([#?].*)?$/.exec(href);
  if (!m) return href;
  let path = m[1];
  const suffix = m[2] ?? "";

  // Compute the current markdown file's directory, relative to docs/.
  // e.g. "docs/internals/README.md" → baseDir = "internals"
  //      "docs/codebase.md"         → baseDir = ""
  let baseDir = "";
  const inDocs = sourcePath.startsWith("docs/")
    ? sourcePath.slice(5)
    : sourcePath;
  const lastSlash = inDocs.lastIndexOf("/");
  if (lastSlash >= 0) baseDir = inDocs.slice(0, lastSlash);

  if (path.startsWith("./")) path = path.slice(2);

  while (path.startsWith("../")) {
    path = path.slice(3);
    baseDir = baseDir.includes("/")
      ? baseDir.slice(0, baseDir.lastIndexOf("/"))
      : "";
  }

  // Absolute repo paths like "docs/foo.md" reset the base.
  if (path.startsWith("docs/")) {
    path = path.slice(5);
    baseDir = "";
  }

  const combined = baseDir ? `${baseDir}/${path}` : path;
  const stripped = combined.replace(/\.md$/i, "");

  // Repo source files → GitHub blob.
  if (
    stripped.startsWith("apps/") ||
    stripped.startsWith("packages/") ||
    stripped.startsWith("infra/")
  ) {
    return `https://github.com/claynicholson/asicify/blob/main/${stripped}${suffix}`;
  }

  // README at repo root → repo home on GitHub.
  if (stripped === "README") {
    return `https://github.com/claynicholson/asicify${suffix}`;
  }

  if (stripped.includes("/") || /^[a-z][a-z0-9-]*$/.test(stripped)) {
    return `/docs/${stripped}${suffix}`;
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
