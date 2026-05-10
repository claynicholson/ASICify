"use client";
//
// WebGPU inference preview using @huggingface/transformers.
//
// This panel loads a small model in the browser (DistilGPT-2 by default)
// once, then lets the user run text generation locally. WebGPU is used when
// available, with graceful fallback to WASM.
//
// We deliberately use a *small* model (~80M params) so first-load is under
// 10 seconds on a typical connection. The point is to give users a feel for
// the original model's output, not to actually run their target.

import * as React from "react";
import { useEffect, useRef, useState } from "react";

interface Status {
  ready: boolean;
  loading: boolean;
  progress: number;
  message: string;
}

const MODEL_ID = "Xenova/distilgpt2";

export function WebGPUInference() {
  const [status, setStatus] = useState<Status>({
    ready: false,
    loading: false,
    progress: 0,
    message: "Click load to download the in-browser model (~80M params).",
  });
  const [prompt, setPrompt] = useState("The compiler for AI silicon is");
  const [output, setOutput] = useState("");
  const [running, setRunning] = useState(false);
  const generatorRef = useRef<unknown>(null);

  async function loadModel() {
    setStatus({
      ready: false,
      loading: true,
      progress: 0,
      message: "Downloading model files...",
    });
    try {
      const { pipeline, env } = await import("@huggingface/transformers");
      // Cache models in the browser's IndexedDB.
      env.useBrowserCache = true;

      const generator = await pipeline("text-generation", MODEL_ID, {
        progress_callback: (info: {
          status?: string;
          progress?: number;
          file?: string;
        }) => {
          setStatus((s) => ({
            ...s,
            progress: info.progress ?? s.progress,
            message: info.file
              ? `${info.status ?? ""}: ${info.file}`
              : info.status ?? s.message,
          }));
        },
        // Try WebGPU; fallback to WASM if unavailable.
        device: "webgpu",
        dtype: "fp32",
      } as unknown as Parameters<typeof pipeline>[2]);

      generatorRef.current = generator;
      setStatus({
        ready: true,
        loading: false,
        progress: 1,
        message: "Model ready. Cached locally for next time.",
      });
    } catch (err) {
      // WebGPU unavailable: try WASM.
      try {
        const { pipeline } = await import("@huggingface/transformers");
        const generator = await pipeline("text-generation", MODEL_ID);
        generatorRef.current = generator;
        setStatus({
          ready: true,
          loading: false,
          progress: 1,
          message: "Model ready (CPU fallback).",
        });
      } catch (err2) {
        setStatus({
          ready: false,
          loading: false,
          progress: 0,
          message: `Load failed: ${err2 instanceof Error ? err2.message : String(err2)}`,
        });
      }
    }
  }

  async function generate() {
    if (!generatorRef.current) return;
    setRunning(true);
    setOutput("");
    try {
      const generator = generatorRef.current as (
        prompt: string,
        opts: Record<string, unknown>,
      ) => Promise<Array<{ generated_text: string }>>;
      const result = await generator(prompt, {
        max_new_tokens: 40,
        temperature: 0.7,
        do_sample: true,
      });
      const text = Array.isArray(result)
        ? result[0]?.generated_text ?? ""
        : "";
      setOutput(text);
    } catch (err) {
      setOutput(
        `Generation failed: ${err instanceof Error ? err.message : String(err)}`,
      );
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    return () => {
      generatorRef.current = null;
    };
  }, []);

  return (
    <div className="rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold">
          In-browser inference (DistilGPT-2)
        </h3>
        <span className="text-[10px] uppercase tracking-[0.08em] text-[var(--color-text-tertiary)] font-mono">
          {status.ready ? "WebGPU ready" : status.loading ? "loading" : "idle"}
        </span>
      </div>

      {!status.ready && !status.loading && (
        <button
          onClick={loadModel}
          className="w-full h-9 rounded-[6px] bg-[var(--color-accent)] text-[#0A0B0E] font-medium text-sm hover:brightness-110"
        >
          Load model in browser (~80 MB, cached after first load)
        </button>
      )}

      {status.loading && (
        <div>
          <div className="h-1 rounded-full bg-[var(--color-bg-overlay)] overflow-hidden">
            <div
              className="h-full bg-[var(--color-accent)] transition-all"
              style={{ width: `${Math.round(status.progress * 100)}%` }}
            />
          </div>
          <div className="mt-2 text-[11px] text-[var(--color-text-tertiary)] font-mono truncate">
            {status.message}
          </div>
        </div>
      )}

      {status.ready && (
        <>
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="w-full h-9 px-3 rounded-[6px] border border-[var(--color-border-default)] bg-[var(--color-bg-overlay)] text-sm font-mono"
            placeholder="Type a prompt..."
          />
          <button
            onClick={generate}
            disabled={running}
            className="mt-3 w-full h-9 rounded-[6px] bg-[var(--color-accent)] text-[#0A0B0E] font-medium text-sm hover:brightness-110 disabled:opacity-50"
          >
            {running ? "Generating..." : "Generate"}
          </button>
          {output && (
            <div className="mt-4 rounded-[6px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-overlay)] p-3 text-sm font-mono whitespace-pre-wrap">
              {output}
            </div>
          )}
        </>
      )}

      {!status.ready && !status.loading && (
        <p className="text-[11px] text-[var(--color-text-tertiary)] mt-3 leading-relaxed">
          The model runs entirely in your browser. Your prompts never leave
          this device. WebGPU is used when available, with WASM fallback.
        </p>
      )}
    </div>
  );
}
