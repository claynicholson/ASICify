import Link from "next/link";

interface FooterLink {
  href: string;
  label: string;
  external?: boolean;
}

export function Footer() {
  return (
    <footer className="mt-24 border-t border-[var(--color-border-default)]">
      {/* pencil-rule divider */}
      <div className="rule-pencil opacity-70" />

      <div className="mx-auto max-w-[1200px] px-6 py-14 grid grid-cols-2 md:grid-cols-5 gap-8">
        <div className="col-span-2">
          <div className="flex items-center gap-2 mb-3">
            <svg viewBox="0 0 24 24" className="w-5 h-5" aria-hidden>
              <rect
                x="4"
                y="4"
                width="16"
                height="16"
                rx="1.5"
                fill="var(--color-accent-muted)"
                stroke="var(--color-accent)"
                strokeWidth="1.6"
              />
              <circle cx="12" cy="12" r="2.5" fill="var(--color-accent)" />
            </svg>
            <span className="font-serif text-[20px] tracking-serif">
              ASICify
            </span>
          </div>
          <p className="text-sm text-[var(--color-text-secondary)] max-w-xs leading-relaxed">
            ASICify is an open compiler from PyTorch to Verilog.
            <br />
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-[var(--color-text-tertiary)]">
              MIT · v0.1
            </span>
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
            {
              href: "https://github.com/claynicholson/asicify",
              label: "GitHub",
              external: true,
            },
            {
              href: "https://github.com/claynicholson/asicify/issues",
              label: "Issues",
              external: true,
            },
            { href: "/docs/internals/extending", label: "Extending" },
          ]}
        />
      </div>
      <div className="border-t border-[var(--color-border-subtle)]">
        <div className="mx-auto max-w-[1200px] px-6 py-4 flex justify-between text-[11px] font-mono tracking-[0.12em] text-[var(--color-text-tertiary)] uppercase">
          <span>MIT licensed. Free to use, fork, and modify.</span>
          <span>v0.1.0</span>
        </div>
      </div>
    </footer>
  );
}

function FooterCol({ title, links }: { title: string; links: FooterLink[] }) {
  return (
    <div>
      <div className="eyebrow mb-3">{title}</div>
      <ul className="flex flex-col gap-2">
        {links.map((l) =>
          l.external ? (
            <li key={l.href}>
              <a
                href={l.href}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent-deep)] transition-colors"
              >
                {l.label}
              </a>
            </li>
          ) : (
            <li key={l.href}>
              <Link
                href={l.href}
                className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent-deep)] transition-colors"
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
