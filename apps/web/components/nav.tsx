import Link from "next/link";
import { Button } from "@/components/ui/button";

export function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-base)]/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-[1200px] items-center justify-between px-6">
        <Link
          href="/"
          className="font-mono text-base font-semibold tracking-tight-display"
        >
          ASIC<span className="text-[var(--color-accent)]">|</span>fy
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
          <Button asChild variant="secondary" size="sm">
            <a
              href="https://github.com/asicify/asicify"
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
