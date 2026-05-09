import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

const TIERS = [
  {
    name: "Free",
    price: "$0",
    cadence: "forever",
    description: "Open-source core, hosted free.",
    features: [
      "All compression methods",
      "Up to 3 projects",
      "Models up to 1B parameters",
      "Public projects",
      "Community Discord support",
    ],
    cta: "Start free",
  },
  {
    name: "Pro",
    price: "$49",
    cadence: "per month",
    description: "For individuals and small teams.",
    features: [
      "Unlimited projects",
      "Models up to 10B parameters",
      "Private projects",
      "API access (rate limited)",
      "White-label reports",
      "Email support",
    ],
    cta: "Upgrade to Pro",
    highlight: true,
  },
  {
    name: "Team",
    price: "$299",
    cadence: "per month",
    description: "5 seats, priority queue.",
    features: [
      "Everything in Pro",
      "5 seats included",
      "Models up to 70B parameters",
      "Higher API rate limits",
      "Slack support",
      "Priority compute queue",
    ],
    cta: "Start team trial",
  },
  {
    name: "Enterprise",
    price: "Custom",
    cadence: "annual",
    description: "Self-hosted, SOC2, custom PDKs.",
    features: [
      "Self-hosted deployment",
      "SOC2-compliant",
      "Custom proprietary PDKs",
      "Dedicated support engineer",
      "SLA-backed uptime",
    ],
    cta: "Contact sales",
  },
];

export default function PricingPage() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-[1200px] px-6 py-16">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h1 className="text-[2.5rem] font-bold tracking-tight-display">
            Open core. Hosted convenience.
          </h1>
          <p className="mt-3 text-[var(--color-text-secondary)]">
            The compiler is free. You pay for compute, multi-target backends,
            and the tools that wrap it.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className={cn(
                "rounded-[6px] border bg-[var(--color-bg-elevated)] p-6 flex flex-col",
                tier.highlight
                  ? "border-[var(--color-accent)] ring-1 ring-[var(--color-accent)]/30"
                  : "border-[var(--color-border-subtle)]",
              )}
            >
              <div className="mb-4">
                <div className="text-sm font-semibold">{tier.name}</div>
                <div className="mt-3 flex items-baseline gap-1">
                  <span className="font-mono text-3xl font-semibold tracking-tight-display">
                    {tier.price}
                  </span>
                  <span className="text-xs text-[var(--color-text-tertiary)]">
                    {tier.cadence}
                  </span>
                </div>
                <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
                  {tier.description}
                </p>
              </div>

              <ul className="space-y-2 mb-6 flex-1">
                {tier.features.map((f) => (
                  <li key={f} className="flex gap-2 text-sm">
                    <Check className="h-4 w-4 text-[var(--color-success)] mt-0.5 flex-shrink-0" />
                    <span className="text-[var(--color-text-secondary)]">
                      {f}
                    </span>
                  </li>
                ))}
              </ul>

              <Button
                variant={tier.highlight ? "primary" : "secondary"}
                className="w-full"
              >
                {tier.cta}
              </Button>
            </div>
          ))}
        </div>

        <div className="mt-16 text-center text-sm text-[var(--color-text-tertiary)]">
          Premium hardware targets (TSMC 16/7nm, Samsung leading-edge nodes) are
          available on Pro and above. Open-source core supports SkyWater 130,
          GF22FDX, ECP5, Artix-7.
        </div>
      </main>
      <Footer />
    </>
  );
}
