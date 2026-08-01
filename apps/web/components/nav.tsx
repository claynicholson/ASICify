import Link from "next/link";
import { Button } from "@/components/ui/button";

export function ChipMark({ className = "w-[18px] h-[18px]" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden>
      <rect
        x="5"
        y="5"
        width="14"
        height="14"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      {[8.5, 12, 15.5].map((p) => (
        <g key={p} stroke="currentColor" strokeWidth="1.3" strokeLinecap="square">
          <line x1={p} y1="2.5" x2={p} y2="5" />
          <line x1={p} y1="19" x2={p} y2="21.5" />
          <line x1="2.5" y1={p} x2="5" y2={p} />
          <line x1="19" y1={p} x2="21.5" y2={p} />
        </g>
      ))}
      <rect x="9" y="9" width="6" height="6" fill="var(--color-accent)" />
    </svg>
  );
}

const LINKS = [
  { href: "/playground", label: "Playground" },
  { href: "/docs", label: "Docs" },
  { href: "/about", label: "About" },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-base)]/90 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-[1200px] items-center justify-between px-4 sm:px-6">
        <Link
          href="/"
          className="flex items-center gap-2.5 text-[var(--color-text-primary)]"
          aria-label="ASICify, home"
        >
          <ChipMark />
          <span className="display-sub text-[17px] leading-none tracking-[-0.01em]">
            ASICify
          </span>
        </Link>
        <nav className="flex items-center gap-1 sm:gap-5">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="px-1.5 sm:px-0 text-[13px] sm:text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
            >
              {l.label}
            </Link>
          ))}
          <Button asChild variant="ink" size="sm" className="ml-2">
            <a
              href="https://github.com/claynicholson/asicify"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </a>
          </Button>
        </nav>
      </div>
    </header>
  );
}
