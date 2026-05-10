import Link from "next/link";

interface FooterLink {
  href: string;
  label: string;
  external?: boolean;
}

export function Footer() {
  return (
    <footer className="border-t border-[var(--color-border-subtle)] mt-24">
      <div className="mx-auto max-w-[1200px] px-6 py-12 grid grid-cols-2 md:grid-cols-5 gap-8">
        <div className="col-span-2">
          <div className="font-mono text-base font-semibold tracking-tight-display mb-3">
            ASIC<span className="text-[var(--color-accent)]">|</span>fy
          </div>
          <p className="text-sm text-[var(--color-text-secondary)] max-w-xs">
            An open-source compiler for AI silicon. MIT licensed.
          </p>
        </div>
        <FooterCol
          title="Project"
          links={[
            { href: "/playground", label: "Playground" },
            { href: "/docs", label: "Documentation" },
            { href: "/about", label: "About" },
          ]}
        />
        <FooterCol
          title="Read"
          links={[
            { href: "/docs/architecture", label: "Architecture" },
            { href: "/docs/methodology", label: "Methodology" },
            { href: "/docs/codebase", label: "Codebase tour" },
            { href: "/docs/roadmap", label: "Roadmap" },
          ]}
        />
        <FooterCol
          title="Contribute"
          links={[
            { href: "https://github.com/asicify/asicify", label: "GitHub", external: true },
            { href: "https://github.com/asicify/asicify/issues", label: "Issues", external: true },
            { href: "https://github.com/asicify/asicify/discussions", label: "Discussions", external: true },
            { href: "/docs/internals/extending", label: "Extending" },
          ]}
        />
      </div>
      <div className="border-t border-[var(--color-border-subtle)]">
        <div className="mx-auto max-w-[1200px] px-6 py-4 flex justify-between text-xs text-[var(--color-text-tertiary)]">
          <span>MIT licensed. Free to use, fork, and modify.</span>
          <span className="font-mono">v0.1.0</span>
        </div>
      </div>
    </footer>
  );
}

function FooterCol({
  title,
  links,
}: {
  title: string;
  links: FooterLink[];
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
        {title}
      </div>
      <ul className="flex flex-col gap-2">
        {links.map((l) =>
          l.external ? (
            <li key={l.href}>
              <a
                href={l.href}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                {l.label}
              </a>
            </li>
          ) : (
            <li key={l.href}>
              <Link
                href={l.href}
                className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                {l.label}
              </Link>
            </li>
          ),
        )}
      </ul>
    </div>
  );
}
