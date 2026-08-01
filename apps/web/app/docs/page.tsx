import Link from "next/link";
import { DOC_SECTIONS, getLastUpdated, formatRelative } from "@/lib/docs";

export const metadata = {
  title: "Documentation · ASICify",
  description: "Compile PyTorch models to hardware-ready specifications.",
};

export default async function DocsIndexPage() {
  // Resolve last-updated for every linked doc in parallel.
  const sections = await Promise.all(
    DOC_SECTIONS.map(async (section) => ({
      ...section,
      items: await Promise.all(
        section.items.map(async (item) => ({
          ...item,
          updated: await getLastUpdated(item.slug),
        })),
      ),
    })),
  );

  return (
    <div>
      <h1 className="display text-[2.5rem]">Documentation</h1>
      <p className="mt-3 text-[var(--color-text-secondary)] max-w-2xl">
        Everything you need to compile a model into hardware-ready Verilog,
        interpret the cost estimates, and ship the result to your fab.
      </p>

      <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-x-10 gap-y-12">
        {sections.map((section) => (
          <div key={section.title}>
            <h2 className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-4">
              {section.title}
            </h2>
            <ul className="space-y-1">
              {section.items.map((item) => (
                <li key={item.slug}>
                  <Link
                    href={`/docs/${item.slug}`}
                    className="block group rounded-[6px] -mx-3 px-3 py-2.5 hover:bg-[var(--color-bg-elevated)] transition-colors"
                  >
                    <div className="flex justify-between items-baseline gap-3">
                      <span className="text-sm font-medium group-hover:text-[var(--color-accent)]">
                        {item.label}
                      </span>
                      {item.updated && (
                        <span className="font-mono text-[10px] text-[var(--color-text-tertiary)] flex-shrink-0">
                          {formatRelative(item.updated)}
                        </span>
                      )}
                    </div>
                    {item.description && (
                      <div className="text-xs text-[var(--color-text-tertiary)] mt-1">
                        {item.description}
                      </div>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="mt-16 pt-8 border-t border-[var(--color-border-subtle)]">
        <h2 className="text-base font-semibold mb-3">Looking for something else?</h2>
        <ul className="space-y-2 text-sm text-[var(--color-text-secondary)]">
          <li>
            <a
              href="https://github.com/claynicholson/asicify"
              target="_blank"
              rel="noreferrer"
              className="hover:text-[var(--color-accent)]"
            >
              → Source code on GitHub
            </a>
          </li>
          <li>
            <Link href="/playground" className="hover:text-[var(--color-accent)]">
              → Interactive playground
            </Link>
          </li>
          <li>
            <a
              href="https://github.com/claynicholson/asicify/issues"
              target="_blank"
              rel="noreferrer"
              className="hover:text-[var(--color-accent)]"
            >
              → File an issue
            </a>
          </li>
        </ul>
      </div>
    </div>
  );
}
