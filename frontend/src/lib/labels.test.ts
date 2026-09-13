import { describe, expect, it } from "vitest";
import { buildLabelRecords } from "./labels";
import type { LabelPoolEntry } from "../types";

const queries: LabelPoolEntry[] = [
  {
    query_sku: "q1",
    query_title: "Query 1",
    product_type: "earrings",
    sources: {
      image_only: ["c1", "c2"],
      text_only: ["c2", "c3"],
      fused_default: ["c1"],
    },
    pool: ["c1", "c2", "c3"],
  },
  {
    query_sku: "q2",
    query_title: "Query 2",
    product_type: "ring",
    sources: { image_only: ["c4"] },
    pool: ["c4"],
  },
];

describe("buildLabelRecords", () => {
  it("only emits records for candidates that were actually labeled", () => {
    const records = buildLabelRecords(queries, { q1: { c1: 2 } }, () => "t");
    expect(records).toEqual([
      { query_sku: "q1", candidate_sku: "c1", label: 2, sources: ["image_only", "fused_default"], labeled_at: "t" },
    ]);
  });

  it("attributes sources correctly per candidate", () => {
    const records = buildLabelRecords(
      queries,
      { q1: { c2: 1, c3: 0 } },
      () => "t",
    );
    const bySku = Object.fromEntries(records.map((r) => [r.candidate_sku, r]));
    expect(bySku.c2.sources.sort()).toEqual(["image_only", "text_only"]);
    expect(bySku.c3.sources).toEqual(["text_only"]);
  });

  it("covers multiple queries", () => {
    const records = buildLabelRecords(
      queries,
      { q1: { c1: 2 }, q2: { c4: 0 } },
      () => "t",
    );
    expect(records.map((r) => r.query_sku).sort()).toEqual(["q1", "q2"]);
  });

  it("returns an empty list when nothing has been labeled yet", () => {
    expect(buildLabelRecords(queries, {})).toEqual([]);
  });
});
