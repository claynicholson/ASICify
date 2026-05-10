import fs from "node:fs/promises";
import path from "node:path";

/**
 * Docs are sourced from the repo-root /docs directory at runtime.
 *
 * Slug ↔ file mapping:
 *   /docs/quickstart           → docs/quickstart.md
 *   /docs/internals/web        → docs/internals/web.md
 *   /docs/internals            → docs/internals/README.md  (folder index)
 */

const DOCS_ROOT = path.resolve(process.cwd(), "..", "..", "docs");

/** Curated structure shown in the sidebar + index page. */
export interface DocSection {
  title: string;
  items: DocLink[];
}

export interface DocLink {
  slug: string; // e.g. "quickstart" or "internals/web"
  label: string;
  description?: string;
}

export const DOC_SECTIONS: DocSection[] = [
  {
    title: "Getting started",
    items: [
      { slug: "quickstart", label: "Quickstart", description: "Compile your first model in 5 minutes." },
      { slug: "deployment", label: "Deployment", description: "Build and run the Docker image." },
    ],
  },
  {
    title: "Concepts",
    items: [
      { slug: "architecture", label: "Architecture", description: "How the compiler is structured." },
      { slug: "methodology", label: "Methodology", description: "Why our cost models work." },
      { slug: "rtl-generation", label: "RTL generation", description: "Verilog templates and multiplier strategies." },
      { slug: "roadmap", label: "Roadmap", description: "What's shipped, what's next." },
    ],
  },
  {
    title: "Contributor docs",
    items: [
      { slug: "codebase", label: "Codebase tour", description: "Read this first." },
      { slug: "internals", label: "Internals overview", description: "Map of the contributor docs." },
      { slug: "internals/web", label: "Frontend internals", description: "Next.js, playground, client estimator." },
      { slug: "internals/api", label: "API internals", description: "FastAPI, auth, queue, WebSocket." },
      { slug: "internals/worker", label: "Worker internals", description: "Pipeline, RTL gen, hardware estimator." },
      { slug: "internals/data-flow", label: "Data flow", description: "End-to-end traces." },
      { slug: "internals/extending", label: "Extending", description: "Recipes for adding targets, primitives, stages." },
      { slug: "internals/conventions", label: "Conventions", description: "Code style, naming, structure." },
      { slug: "internals/glossary", label: "Glossary", description: "ML, silicon, EDA terminology." },
    ],
  },
];

/** Flat list of all known doc slugs. Used for static params and 404. */
export function getAllSlugs(): string[] {
  return DOC_SECTIONS.flatMap((s) => s.items.map((i) => i.slug));
}

/** Find a doc's metadata in DOC_SECTIONS by slug. */
export function findDoc(slug: string): DocLink | null {
  for (const s of DOC_SECTIONS) {
    const item = s.items.find((i) => i.slug === slug);
    if (item) return item;
  }
  return null;
}

/** Resolve a slug to an absolute path on disk. */
function resolveSlugPath(slug: string): string {
  // Allow slugs like "internals" → look for internals/README.md or internals.md
  return path.join(DOCS_ROOT, slug);
}

export interface DocContent {
  slug: string;
  label: string;
  body: string;
  lastUpdated: Date;
  sourcePath: string;
}

/** Read a doc by slug. Returns null if it doesn't exist on disk. */
export async function getDoc(slug: string): Promise<DocContent | null> {
  const meta = findDoc(slug);
  if (!meta) return null;

  const candidates = [
    resolveSlugPath(slug) + ".md",
    path.join(resolveSlugPath(slug), "README.md"),
  ];

  for (const candidate of candidates) {
    try {
      const stat = await fs.stat(candidate);
      const body = await fs.readFile(candidate, "utf-8");
      return {
        slug,
        label: meta.label,
        body,
        lastUpdated: stat.mtime,
        sourcePath: path.relative(path.resolve(process.cwd(), "..", ".."), candidate),
      };
    } catch {
      // try next candidate
    }
  }

  return null;
}

/** Last-updated timestamp lookup for the index page. */
export async function getLastUpdated(slug: string): Promise<Date | null> {
  const candidates = [
    resolveSlugPath(slug) + ".md",
    path.join(resolveSlugPath(slug), "README.md"),
  ];
  for (const candidate of candidates) {
    try {
      const stat = await fs.stat(candidate);
      return stat.mtime;
    } catch {
      // continue
    }
  }
  return null;
}

/** Format like "2h ago", "3d ago", or "Mar 12" for index display. */
export function formatRelative(d: Date): string {
  const diffMs = Date.now() - d.getTime();
  const min = Math.floor(diffMs / 60_000);
  const hr = Math.floor(min / 60);
  const day = Math.floor(hr / 24);

  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  if (hr < 24) return `${hr}h ago`;
  if (day < 7) return `${day}d ago`;

  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: d.getFullYear() === new Date().getFullYear() ? undefined : "numeric",
  });
}
