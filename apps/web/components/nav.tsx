import Link from "next/link";
import { Button } from "@/components/ui/button";

export function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-base)]/85 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-[1200px] items-center justify-between px-6">
        <Link
          href="/"
          className="flex items-center gap-2 group"
          aria-label="ASICify, home"
        >
          {/* tiny chip-mark logo */}
          <svg
            viewBox="0 0 24 24"
            className="w-5 h-5"
            aria-hidden
          >
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
            <line x1="2" y1="9" x2="4" y2="9" stroke="var(--color-text-primary)" strokeWidth="1.4" strokeLinecap="round" />
            <line x1="2" y1="15" x2="4" y2="15" stroke="var(--color-text-primary)" strokeWidth="1.4" strokeLinecap="round" />
            <line x1="20" y1="9" x2="22" y2="9" stroke="var(--color-text-primary)" strokeWidth="1.4" strokeLinecap="round" />
            <line x1="20" y1="15" x2="22" y2="15" stroke="var(--color-text-primary)" strokeWidth="1.4" strokeLinecap="round" />
            <circle cx="12" cy="12" r="2.5" fill="var(--color-accent)" />
          </svg>
          <span className="font-serif text-[20px] tracking-serif text-[var(--color-text-primary)] leading-none">
            ASICify
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          <Button asChild variant="ghost" size="sm">
            <Link href="/playground">Playground</Link>
          </Button>
          <Button asChild variant="ghost" size="sm">
            <Link href="/docs">Docs</Link>
          </Button>
          <Button asChild variant="ghost" size="sm">
            <Link href="/about">About</Link>
          </Button>
          <Button asChild variant="ink" size="sm">
            <a
              href="https://github.com/claynicholson/asicify"
              target="_blank"
              rel="noreferrer"
            >
              GitHub →
            </a>
          </Button>
        </nav>
      </div>
    </header>
  );
}
