import Link from "next/link";
import { Nav } from "@/components/nav";

export default function SignInPage() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-md px-6 py-24 text-center">
        <h1 className="text-2xl font-semibold tracking-tight-display mb-4">
          Sign in
        </h1>
        <p className="text-sm text-[var(--color-text-secondary)] mb-6">
          Sign-in is handled by Clerk. Configure{" "}
          <code className="font-mono text-xs bg-[var(--color-bg-elevated)] px-1.5 py-0.5 rounded">
            NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
          </code>{" "}
          in your environment, then wrap this app with{" "}
          <code className="font-mono text-xs bg-[var(--color-bg-elevated)] px-1.5 py-0.5 rounded">
            ClerkProvider
          </code>{" "}
          and replace this stub with{" "}
          <code className="font-mono text-xs bg-[var(--color-bg-elevated)] px-1.5 py-0.5 rounded">
            &lt;SignIn /&gt;
          </code>
          .
        </p>
        <Link
          href="/"
          className="text-sm text-[var(--color-accent)] hover:text-[var(--color-accent-hover)]"
        >
          ← Back home
        </Link>
      </main>
    </>
  );
}
