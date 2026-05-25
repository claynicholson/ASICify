"use client";

import type {
  CompressionConfig,
  Quantization,
  TargetId,
} from "@asicify/shared";
import { TARGET_LIST } from "@asicify/shared";
import { MODEL_CATALOG } from "@/lib/catalog";
import { cn } from "@/lib/utils";

const QUANT_OPTIONS: { value: Quantization; label: string; bits: string }[] = [
  { value: "fp16", label: "FP16", bits: "16 bit" },
  { value: "int8", label: "INT8", bits: "8 bit" },
  { value: "int4", label: "INT4", bits: "4 bit" },
  { value: "ternary", label: "Ternary", bits: "1.6 bit" },
  { value: "binary", label: "Binary", bits: "1 bit" },
];

interface Props {
  modelId: string;
  setModelId: (id: string) => void;
  config: CompressionConfig;
  setConfig: (c: CompressionConfig) => void;
  target: TargetId;
  setTarget: (t: TargetId) => void;
}

export function ConfigPanel({
  modelId,
  setModelId,
  config,
  setConfig,
  target,
  setTarget,
}: Props) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <SectionLabel>Model</SectionLabel>
        <select
          value={modelId}
          onChange={(e) => setModelId(e.target.value)}
          className="w-full h-10 px-3 rounded-[6px] border border-[var(--color-border-default)] bg-[var(--color-bg-elevated)] text-sm font-mono focus:outline-none focus:border-[var(--color-accent)]"
        >
          {MODEL_CATALOG.map((m) => (
            <option key={m.id} value={m.id}>
              {m.display_name} ({(m.parameters / 1e6).toFixed(0)}M)
            </option>
          ))}
        </select>
      </div>

      <div>
        <SectionLabel>Quantization</SectionLabel>
        <div className="grid grid-cols-5 gap-1">
          {QUANT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() =>
                setConfig({ ...config, quantization: opt.value })
              }
              className={cn(
                "h-14 rounded-[6px] border flex flex-col items-center justify-center transition-colors",
                config.quantization === opt.value
                  ? "border-[var(--color-accent)] bg-[var(--color-accent-muted)]"
                  : "border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] hover:border-[var(--color-border-default)]",
              )}
            >
              <span className="font-mono text-xs font-semibold">
                {opt.label}
              </span>
              <span className="font-mono text-[10px] text-[var(--color-text-tertiary)] mt-0.5">
                {opt.bits}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="flex justify-between items-baseline mb-2">
          <SectionLabel className="mb-0">Sparsity</SectionLabel>
          <span className="font-mono text-xs text-[var(--color-text-tertiary)]">
            {Math.round(config.sparsity.ratio * 100)}%
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={90}
          step={5}
          value={config.sparsity.ratio * 100}
          onChange={(e) => {
            const ratio = Number(e.target.value) / 100;
            setConfig({
              ...config,
              sparsity: {
                type: ratio === 0 ? "none" : "structured_2_4",
                ratio,
              },
            });
          }}
          className="w-full accent-[var(--color-accent)]"
        />
        <div className="flex justify-between mt-1 font-mono text-[10px] text-[var(--color-text-tertiary)]">
          <span>0%</span>
          <span>50%</span>
          <span>90%</span>
        </div>
      </div>

      <div>
        <SectionLabel>Decomposition</SectionLabel>
        <div className="grid grid-cols-3 gap-1">
          {(["none", "monarch", "butterfly"] as const).map((type) => (
            <button
              key={type}
              onClick={() =>
                setConfig({
                  ...config,
                  decomposition: { type, rank: 64 },
                })
              }
              className={cn(
                "h-9 rounded-[6px] border text-xs font-medium transition-colors",
                config.decomposition.type === type
                  ? "border-[var(--color-accent)] bg-[var(--color-accent-muted)]"
                  : "border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] hover:border-[var(--color-border-default)]",
              )}
            >
              {type === "none"
                ? "None"
                : type === "monarch"
                  ? "Monarch"
                  : "Butterfly"}
            </button>
          ))}
        </div>
      </div>

      <div>
        <SectionLabel>Target hardware</SectionLabel>
        <select
          value={target}
          onChange={(e) => setTarget(e.target.value as TargetId)}
          className="w-full h-10 px-3 rounded-[6px] border border-[var(--color-border-default)] bg-[var(--color-bg-elevated)] text-sm font-mono focus:outline-none focus:border-[var(--color-accent)]"
        >
          {TARGET_LIST.map((t) => (
            <option key={t.id} value={t.id}>
              {t.display_name}
            </option>
          ))}
        </select>
        <p className="mt-2 text-xs text-[var(--color-text-tertiary)]">
          {TARGET_LIST.find((t) => t.id === target)?.description}
        </p>
      </div>

      <a
        href="/docs/quickstart"
        className="h-11 rounded-[4px] bg-[var(--color-accent)] text-[var(--color-accent-ink)] border border-[var(--color-accent-deep)] font-semibold text-sm hover:bg-[var(--color-accent-hover)] transition-colors flex items-center justify-center"
      >
        Compile via CLI →
      </a>
      <p className="text-[11px] text-[var(--color-text-tertiary)] -mt-3 leading-relaxed">
        Estimates above run in your browser. To generate real RTL, run the
        CLI. The quickstart has the command.
      </p>
    </div>
  );
}

function SectionLabel({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-medium mb-2",
        className,
      )}
    >
      {children}
    </div>
  );
}
