"use client";

const SAMPLE_PROMPT = "The future of AI inference will run on";

const ORIGINAL_OUTPUT =
  " custom silicon designed specifically for transformer workloads, with hardware optimized for sparse attention and low-precision arithmetic.";

const COMPRESSED_OUTPUT_BY_QUANT: Record<string, string> = {
  fp16:
    " custom silicon designed specifically for transformer workloads, with hardware optimized for sparse attention and low-precision arithmetic.",
  int8:
    " custom silicon designed specifically for transformer workloads, with hardware optimized for sparse attention and low-precision arithmetic.",
  int4:
    " custom silicon built for transformer workloads, with hardware optimized for sparse attention and low-precision arithmetic.",
  ternary:
    " custom hardware built for transformer workloads, where precision and throughput are balanced for inference.",
  binary:
    " specialized hardware where weights are encoded in single bits and computation is dominated by XNOR operations.",
};

export function InferenceComparison({
  quantization,
}: {
  quantization: string;
}) {
  const compressed =
    COMPRESSED_OUTPUT_BY_QUANT[quantization] ?? COMPRESSED_OUTPUT_BY_QUANT.int4;

  return (
    <div className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-overlay)] p-4">
      <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-3">
        Sample inference (preview)
      </div>
      <div className="font-mono text-xs space-y-3">
        <div>
          <div className="text-[var(--color-text-tertiary)] mb-1">prompt</div>
          <div className="text-[var(--color-text-primary)]">
            {SAMPLE_PROMPT}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-text-tertiary)]" />
              <span className="text-[var(--color-text-tertiary)]">
                original (fp16)
              </span>
            </div>
            <div className="text-[var(--color-text-secondary)] leading-relaxed">
              {ORIGINAL_OUTPUT}
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />
              <span className="text-[var(--color-accent)]">
                compressed ({quantization})
              </span>
            </div>
            <div className="text-[var(--color-text-secondary)] leading-relaxed">
              {compressed}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
