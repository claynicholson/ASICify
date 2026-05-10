// PDF report generator using @react-pdf/renderer.
//
// The route /api/report streams a PDF for a given configuration. The PDF
// summarizes the same numbers the playground shows, so the report is
// reproducible from the URL alone. No server-side state.

import * as React from "react";
import {
  Document,
  Page,
  Text,
  View,
  StyleSheet,
  Font,
} from "@react-pdf/renderer";

import type { CompressionConfig, TargetId } from "@asicify/shared";
import { TARGETS } from "@asicify/shared/targets";
import { quickEstimate } from "@/lib/estimator";
import { MODEL_CATALOG, opsPerInference } from "@/lib/catalog";
import { formatArea, formatCompact, formatUSD } from "@/lib/utils";

const styles = StyleSheet.create({
  page: {
    backgroundColor: "#0A0B0E",
    color: "#F4F5F7",
    fontFamily: "Helvetica",
    fontSize: 10,
    padding: 48,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    borderBottomColor: "#232730",
    borderBottomWidth: 1,
    paddingBottom: 12,
    marginBottom: 24,
  },
  brand: {
    fontSize: 20,
    fontWeight: 700,
    letterSpacing: -0.6,
  },
  brandAccent: {
    color: "#5B8FF9",
  },
  meta: {
    fontSize: 8,
    color: "#A0A6B1",
    textAlign: "right",
  },
  h2: {
    fontSize: 14,
    fontWeight: 700,
    marginTop: 24,
    marginBottom: 8,
    color: "#F4F5F7",
  },
  label: {
    color: "#6B7280",
    fontSize: 8,
    textTransform: "uppercase",
    letterSpacing: 0.6,
    marginBottom: 2,
  },
  metricGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginTop: 4,
  },
  metricCell: {
    width: "33%",
    padding: 8,
    borderColor: "#232730",
    borderWidth: 1,
    marginRight: -1,
    marginBottom: -1,
  },
  metricValue: {
    fontSize: 14,
    fontWeight: 700,
    fontFamily: "Courier",
    color: "#F4F5F7",
  },
  paragraph: {
    color: "#A0A6B1",
    lineHeight: 1.5,
    marginBottom: 6,
  },
  table: {
    marginTop: 8,
    borderTopColor: "#232730",
    borderTopWidth: 1,
  },
  tr: {
    flexDirection: "row",
    borderBottomColor: "#232730",
    borderBottomWidth: 1,
    paddingVertical: 6,
  },
  th: {
    color: "#6B7280",
    fontSize: 8,
    textTransform: "uppercase",
    letterSpacing: 0.6,
    flex: 1,
  },
  td: {
    fontFamily: "Courier",
    flex: 1,
    fontSize: 9,
  },
  footer: {
    position: "absolute",
    bottom: 24,
    left: 48,
    right: 48,
    fontSize: 8,
    color: "#6B7280",
    textAlign: "center",
  },
});

interface ReportInput {
  modelId: string;
  config: CompressionConfig;
  primaryTarget: TargetId;
  comparisonTargets: TargetId[];
  generatedAt: Date;
}

export function HardwareReport(input: ReportInput) {
  const model =
    MODEL_CATALOG.find((m) => m.id === input.modelId) ?? MODEL_CATALOG[0];
  const baseline = model.task === "language_modeling" ? 9.2 : 1;

  const primary = quickEstimate({
    param_count: model.parameters,
    ops_per_token: opsPerInference(model.parameters),
    config: input.config,
    target: input.primaryTarget,
    baseline_metric: baseline,
  });

  const comparisons = input.comparisonTargets
    .filter((t) => t !== input.primaryTarget)
    .map((t) =>
      quickEstimate({
        param_count: model.parameters,
        ops_per_token: opsPerInference(model.parameters),
        config: input.config,
        target: t,
        baseline_metric: baseline,
      }),
    );

  return (
    <Document
      title={`ASICify report — ${model.display_name}`}
      author="ASICify"
      subject="Hardware feasibility report"
    >
      <Page size="LETTER" style={styles.page}>
        <View style={styles.header} fixed>
          <Text style={styles.brand}>
            ASIC<Text style={styles.brandAccent}>|</Text>fy
          </Text>
          <Text style={styles.meta}>
            Hardware report · {input.generatedAt.toISOString().slice(0, 10)}
            {"\n"}
            github.com/claynicholson/asicify
          </Text>
        </View>

        <Text style={styles.h2}>Configuration</Text>
        <View style={styles.table}>
          <Row label="Model" value={model.display_name} />
          <Row
            label="Parameters"
            value={formatCompact(model.parameters, 1)}
          />
          <Row label="Quantization" value={input.config.quantization} />
          <Row
            label="Sparsity"
            value={`${input.config.sparsity.type} (${(input.config.sparsity.ratio * 100).toFixed(0)}%)`}
          />
          <Row
            label="Decomposition"
            value={input.config.decomposition.type}
          />
          <Row
            label="Primary target"
            value={TARGETS[input.primaryTarget].display_name}
          />
        </View>

        <Text style={styles.h2}>Headline numbers ({input.primaryTarget})</Text>
        <View style={styles.metricGrid}>
          <Metric label="Die area" value={formatArea(primary.area_mm2)} />
          <Metric
            label="Throughput"
            value={`${formatCompact(primary.throughput_per_sec, 1)}/s`}
          />
          <Metric
            label="Cost @ 100K"
            value={formatUSD(primary.cost_per_chip["100000"])}
          />
          <Metric
            label="Max clock"
            value={`${primary.max_clock_mhz} MHz`}
          />
          <Metric
            label="Energy / op"
            value={`${primary.energy_per_op_pj.toFixed(2)} pJ`}
          />
          <Metric
            label="Effective bits/weight"
            value={primary.bits_per_weight.toFixed(2)}
          />
        </View>

        <Text style={styles.h2}>Cost vs volume</Text>
        <View style={styles.table}>
          <View style={styles.tr}>
            <Text style={styles.th}>Volume</Text>
            <Text style={styles.th}>Cost per chip</Text>
            <Text style={styles.th}>Total BOM</Text>
          </View>
          {(["1000", "100000", "1000000"] as const).map((vol) => {
            const cost = primary.cost_per_chip[vol];
            const total = cost * Number(vol);
            return (
              <View key={vol} style={styles.tr}>
                <Text style={styles.td}>{Number(vol).toLocaleString()}</Text>
                <Text style={styles.td}>{formatUSD(cost)}</Text>
                <Text style={styles.td}>{formatUSD(total)}</Text>
              </View>
            );
          })}
        </View>

        {comparisons.length > 0 && (
          <>
            <Text style={styles.h2}>Comparison vs other targets</Text>
            <View style={styles.table}>
              <View style={styles.tr}>
                <Text style={styles.th}>Target</Text>
                <Text style={styles.th}>Area (mm²)</Text>
                <Text style={styles.th}>Cost @ 100K</Text>
                <Text style={styles.th}>Throughput</Text>
              </View>
              {[primary, ...comparisons].map((e) => (
                <View key={e.target} style={styles.tr}>
                  <Text style={styles.td}>{TARGETS[e.target].display_name}</Text>
                  <Text style={styles.td}>{e.area_mm2.toFixed(2)}</Text>
                  <Text style={styles.td}>
                    {formatUSD(e.cost_per_chip["100000"])}
                  </Text>
                  <Text style={styles.td}>
                    {formatCompact(e.throughput_per_sec, 1)}/s
                  </Text>
                </View>
              ))}
            </View>
          </>
        )}

        <Text style={styles.h2}>Methodology</Text>
        <Text style={styles.paragraph}>
          Numbers are first-order estimates derived from published cell-library
          data plus Murphy yield models. Confidence is{" "}
          {(primary.confidence * 100).toFixed(0)}%. Refine with foundry data
          for production decisions.
        </Text>
        <Text style={styles.paragraph}>
          Compression: INT8 symmetric per-output-channel weights, bit-packed
          and hardwired into the generated Verilog as `localparam` constants.
          Sparsity prunes before quantization so zeros propagate.
        </Text>

        <Text style={styles.footer} fixed>
          Generated by ASICify · MIT licensed · This report is reproducible
          from a config hash
        </Text>
      </Page>
    </Document>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metricCell}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.tr}>
      <Text style={[styles.th, { flex: 1 }]}>{label}</Text>
      <Text style={[styles.td, { flex: 2 }]}>{value}</Text>
    </View>
  );
}
