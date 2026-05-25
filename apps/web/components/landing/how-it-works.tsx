import { FileCode, Cpu, Wrench } from "lucide-react";

const STEPS = [
  {
    icon: FileCode,
    title: "Input",
    description:
      "You provide a PyTorch checkpoint, a HuggingFace ID, or a model from the curated catalog. ASICify parses the compute graph and prepares it for compression.",
  },
  {
    icon: Wrench,
    title: "Compression",
    description:
      "ASICify applies INT4 or INT8 quantization, structured sparsity, Monarch decomposition, and optional hardware-aware fine-tuning. Quality is measured on a held-out benchmark before any artifact is written.",
  },
  {
    icon: Cpu,
    title: "Output",
    description:
      "The compiler emits synthesizable Verilog with hardwired weights, a Cocotb testbench, and an area-and-cost report for every selected target. Each artifact is pinned to a config hash so the run is reproducible.",
  },
];

export function HowItWorks() {
  return (
    <section className="relative mx-auto max-w-[1200px] px-6 py-24">
      <div className="max-w-2xl mb-12">
        <div className="eyebrow mb-3">The workflow</div>
        <h2 className="font-serif text-[clamp(2.25rem,4.5vw,3rem)] leading-[1.05] tracking-serif">
          How it works
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {STEPS.map((step, i) => {
          const Icon = step.icon;
          return (
            <div
              key={step.title}
              className="relative sticker rounded-[3px] p-7"
            >
              <div className="flex items-center justify-between mb-5">
                <div className="h-10 w-10 rounded-[3px] bg-[var(--color-accent-muted)] text-[var(--color-accent-deep)] flex items-center justify-center border border-[var(--color-accent)]">
                  <Icon className="h-5 w-5" />
                </div>
                <span className="font-mono text-[11px] text-[var(--color-text-tertiary)] tracking-[0.2em]">
                  0{i + 1}
                </span>
              </div>
              <h3 className="font-serif text-[1.625rem] leading-[1.1] mb-2 text-[var(--color-text-primary)] tracking-serif">
                {step.title}
              </h3>
              <p className="text-[15px] text-[var(--color-text-secondary)] leading-relaxed">
                {step.description}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
