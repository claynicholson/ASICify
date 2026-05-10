import { NextResponse } from "next/server";
import { renderToStream } from "@react-pdf/renderer";
import { HardwareReport } from "@/lib/report";
import type {
  CompressionConfig,
  Quantization,
  SparsityType,
  DecompositionType,
  TargetId,
} from "@asicify/shared";
import { MODEL_CATALOG } from "@/lib/catalog";

// Server-only route. Renders a PDF for the given playground configuration.
//
//   GET /api/report?model=gpt2-small
//                  &q=int4
//                  &sp=structured_2_4&spr=0.5
//                  &dc=none
//                  &target=tsmc28
//                  &compare=ecp5,sky130
//
// Output is a streaming PDF with Content-Disposition: inline.

export const runtime = "nodejs";

const VALID_QUANTS: Quantization[] = ["fp16", "int8", "int4", "ternary", "binary"];
const VALID_SPARSITY: SparsityType[] = [
  "none",
  "structured_2_4",
  "structured_4_8",
  "block_sparse_16",
  "unstructured",
];
const VALID_DECOMP: DecompositionType[] = ["none", "monarch", "butterfly", "low_rank"];

function pickEnum<T extends string>(value: string | null, allowed: T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback;
}

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const params = url.searchParams;

  const modelId = params.get("model") ?? MODEL_CATALOG[0].id;
  const config: CompressionConfig = {
    quantization: pickEnum(params.get("q"), VALID_QUANTS, "int8"),
    sparsity: {
      type: pickEnum(params.get("sp"), VALID_SPARSITY, "none"),
      ratio: clamp(parseFloat(params.get("spr") ?? "0"), 0, 0.95),
    },
    decomposition: {
      type: pickEnum(params.get("dc"), VALID_DECOMP, "none"),
    },
    fine_tune: false,
    fine_tune_steps: 0,
  };

  const primaryTarget = (params.get("target") ?? "tsmc28") as TargetId;
  const comparisonTargets = (params.get("compare") ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean) as TargetId[];

  const stream = await renderToStream(
    HardwareReport({
      modelId,
      config,
      primaryTarget,
      comparisonTargets,
      generatedAt: new Date(),
    }),
  );

  // The Node-stream from renderToStream is compatible with Response in
  // edge runtime; cast to any to satisfy the TS types.
  return new NextResponse(stream as unknown as ReadableStream, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `inline; filename="asicify-${modelId}-${config.quantization}.pdf"`,
      "Cache-Control": "no-store",
    },
  });
}

function clamp(n: number, lo: number, hi: number): number {
  if (Number.isNaN(n)) return lo;
  return Math.min(hi, Math.max(lo, n));
}
