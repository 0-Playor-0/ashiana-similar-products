import type { LabelPoolEntry, RelevanceLabel } from "../types";

export type LabelMap = Record<string, Record<string, RelevanceLabel>>; // query_sku -> candidate_sku -> label

export interface LabelExportRecord {
  query_sku: string;
  candidate_sku: string;
  label: RelevanceLabel;
  sources: string[];
  labeled_at: string;
}

export function buildLabelRecords(
  queries: LabelPoolEntry[],
  labels: LabelMap,
  now: () => string = () => new Date().toISOString(),
): LabelExportRecord[] {
  const records: LabelExportRecord[] = [];
  for (const entry of queries) {
    const queryLabels = labels[entry.query_sku] ?? {};
    for (const [candidateSku, label] of Object.entries(queryLabels)) {
      records.push({
        query_sku: entry.query_sku,
        candidate_sku: candidateSku,
        label,
        sources: Object.entries(entry.sources ?? {})
          .filter(([, skus]) => skus.includes(candidateSku))
          .map(([method]) => method),
        labeled_at: now(),
      });
    }
  }
  return records;
}
