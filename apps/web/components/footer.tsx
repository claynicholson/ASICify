import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-[var(--color-border-subtle)] mt-24">
      <div className="mx-auto max-w-[1200px] px-6 py-12 grid grid-cols-2 md:grid-cols-5 gap-8">
        <div className="col-span-2">
          <div className="font-mono text-base font-semibold tracking-tight-display mb-3">
            ASIC<span className="text-[var(--color-accent)]">|</span>fy
          </div>
          <p className="text-sm text-[var(--color-text-secondary)] max-w-xs">
            The compiler for AI silicon. Open-source core. MIT licensed.
          </p>
        </div>
        <FooterCol
          title="Product"
          links={[
            { href: "/playground", label: "Playground" },
            { href: "/pricing", label: "Pricing" },
            { href: "/docs", label: "Documentation" },
          ]}
        />
        <FooterCol
          title="Resources"
          links={[
            { href: "/docs/methodology", label: "Methodology" },
            { href: "/docs/architecture", label: "Architecture" },
            { href: "/blog", label: "Blog" },
          ]}
        />
        <FooterCol
          title="Community"
          links={[
            { href: "https://github.com/asicify/asicify", label: "GitHub" },
            { href: "https://discord.gg/asicify", label: "Discord" },
            { href: "mailto:hello@asicify.com", label: "Contact" },
          ]}
        />
      </div>
      <div className="border-t border-[var(--color-border-subtle)]">
        <div className="mx-auto max-w-[1200px] px-6 py-4 flex justify-between text-xs text-[var(--color-text-tertiary)]">
          <span>© 2026 ASICify. MIT licensed.</span>
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
  links: { href: string; label: string }[];
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
        {title}
      </div>
      <ul className="flex flex-col gap-2">
        {links.map((l) => (
          <li key={l.href}>
            <Link
              href={l.href}
              className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
            >
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
