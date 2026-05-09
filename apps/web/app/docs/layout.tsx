import Link from "next/link";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
import { DOC_SECTIONS } from "@/lib/docs";

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Nav />
      <div className="mx-auto max-w-[1400px] px-6 py-10 grid grid-cols-12 gap-8">
        <aside className="hidden lg:block col-span-3">
          <div className="sticky top-20">
            <Link
              href="/docs"
              className="block text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] font-medium mb-4"
            >
              ← Docs index
            </Link>
            <nav className="flex flex-col gap-6">
              {DOC_SECTIONS.map((section) => (
                <div key={section.title}>
                  <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-2">
                    {section.title}
                  </div>
                  <ul className="flex flex-col gap-0.5 border-l border-[var(--color-border-subtle)]">
                    {section.items.map((item) => (
                      <li key={item.slug}>
                        <Link
                          href={`/docs/${item.slug}`}
                          className="block pl-3 -ml-px py-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-l hover:border-[var(--color-text-secondary)] transition-colors"
                        >
                          {item.label}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </nav>
          </div>
        </aside>
        <main className="col-span-12 lg:col-span-9 min-w-0">{children}</main>
      </div>
      <Footer />
    </>
  );
}
