import Link from "next/link";
import { ChipMark } from "@/components/nav";

interface FooterLink {
  href: string;
  label: string;
  external?: boolean;
}

export function Footer() {
  return (
    <footer className="mt-24 border-t border-[var(--color-border-default)]">
      <div className="mx-auto max-w-[1200px] px-6 py-14 grid grid-cols-2 md:grid-cols-5 gap-8">
        <div className="col-span-2">
          <div className="flex items-center gap-2.5 mb-4 text-[var(--color-text-primary)]">
            <ChipMark />
            <span className="display-sub text-[17px] leading-none tracking-[-0.01em]">
              ASICify
            </span>
          </div>
          <p className="text-sm text-[var(--color-text-secondary)] max-w-xs leading-relaxed m-0">
            An open compiler from PyTorch to Verilog.
          </p>
          <p className="mt-3 font-mono text-[11px] tracking-[0.14em] uppercase text-[var(--color-text-tertiary)] m-0">
            MIT · v0.1
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
        <div className="mx-auto max-w-[1200px] px-6 py-4 flex justify-between font-mono text-[11px] tracking-[0.12em] text-[var(--color-text-tertiary)] uppercase">
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
      <div className="label-mono mb-4">{title}</div>
      <ul className="flex flex-col gap-2 m-0 p-0 list-none">
        {links.map((l) => (
          <li key={l.href}>
            {l.external ? (
              <a
                href={l.href}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent-deep)] transition-colors"
              >
                {l.label}
              </a>
            ) : (
              <Link
                href={l.href}
                className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent-deep)] transition-colors"
              >
                {l.label}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
