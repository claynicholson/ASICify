import { FileCode, Cpu, Wrench } from "lucide-react";

const STEPS = [
  {
    icon: FileCode,
    title: "Pick a model",
    description:
      "PyTorch checkpoint, HuggingFace ID, or one of the curated catalog. ASICify parses the compute graph in seconds.",
  },
  {
    icon: Wrench,
    title: "Compress and validate",
    description:
      "Quantization, structured sparsity, Monarch decomposition, optional hardware-aware fine-tuning. Quality is checked on a held-out benchmark.",
  },
  {
    icon: Cpu,
    title: "Get the RTL",
    description:
      "Synthesizable Verilog with hardwired weights, Cocotb testbench, area and cost estimates across every target you selected.",
  },
];

export function HowItWorks() {
  return (
    <section className="mx-auto max-w-[1200px] px-6 py-24">
      <div className="max-w-2xl mb-12">
        <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
          How it works
        </div>
        <h2 className="text-[2.5rem] font-bold tracking-tight-display leading-[1.1]">
          From checkpoint to silicon in three steps.
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[var(--color-border-subtle)] rounded-[6px] overflow-hidden border border-[var(--color-border-subtle)]">
        {STEPS.map((step, i) => {
          const Icon = step.icon;
          return (
            <div
              key={step.title}
              className="bg-[var(--color-bg-elevated)] p-8"
            >
              <div className="flex items-center justify-between mb-6">
                <div className="h-10 w-10 rounded-[6px] bg-[var(--color-accent-muted)] text-[var(--color-accent)] flex items-center justify-center">
                  <Icon className="h-5 w-5" />
                </div>
                <span className="font-mono text-xs text-[var(--color-text-tertiary)]">
                  0{i + 1}
                </span>
              </div>
              <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
              <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                {step.description}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
