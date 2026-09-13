import { describe, expect, it } from "vitest";
import {
  clampWeight,
  isAllZero,
  maxPriceRatioFromSearchParams,
  normalizeWeights,
  sameCategoryFromSearchParams,
  weightsFromSearchParams,
  weightsToSearchParamEntries,
} from "./weights";

describe("clampWeight", () => {
  it("clamps below 0 up to 0", () => {
    expect(clampWeight(-0.5)).toBe(0);
  });

  it("clamps above 1 down to 1", () => {
    expect(clampWeight(1.5)).toBe(1);
  });

  it("passes through in-range values", () => {
    expect(clampWeight(0.42)).toBe(0.42);
  });

  it("treats NaN as 0", () => {
    expect(clampWeight(Number.NaN)).toBe(0);
  });
});

describe("isAllZero", () => {
  it("is true only when every weight is exactly zero", () => {
    expect(isAllZero({ image: 0, text: 0, meta: 0 })).toBe(true);
    expect(isAllZero({ image: 0.1, text: 0, meta: 0 })).toBe(false);
  });
});

describe("normalizeWeights", () => {
  it("normalizes to sum to 1", () => {
    const result = normalizeWeights({ image: 2, text: 1, meta: 1 });
    expect(result.image + result.text + result.meta).toBeCloseTo(1);
    expect(result).toEqual({ image: 0.5, text: 0.25, meta: 0.25 });
  });

  it("falls back to equal thirds when all weights are zero", () => {
    const result = normalizeWeights({ image: 0, text: 0, meta: 0 });
    expect(result.image).toBeCloseTo(1 / 3);
    expect(result.text).toBeCloseTo(1 / 3);
    expect(result.meta).toBeCloseTo(1 / 3);
  });

  it("is a no-op on already-normalized weights", () => {
    const result = normalizeWeights({ image: 0.6, text: 0.1, meta: 0.3 });
    expect(result).toEqual({ image: 0.6, text: 0.1, meta: 0.3 });
  });
});

describe("weight URL param round-tripping", () => {
  it("round-trips through search params exactly", () => {
    const weights = { image: 0.7, text: 0.1, meta: 0.2 };
    const params = new URLSearchParams(weightsToSearchParamEntries(weights));
    expect(params.get("wi")).toBe("0.70");
    expect(params.get("wt")).toBe("0.10");
    expect(params.get("wm")).toBe("0.20");
    expect(weightsFromSearchParams(params)).toEqual(weights);
  });

  it("returns null when any of wi/wt/wm is missing", () => {
    const params = new URLSearchParams("wi=0.5&wt=0.3");
    expect(weightsFromSearchParams(params)).toBeNull();
  });

  it("returns null for non-numeric values instead of throwing", () => {
    const params = new URLSearchParams("wi=abc&wt=0.3&wm=0.2");
    expect(weightsFromSearchParams(params)).toBeNull();
  });

  it("clamps out-of-range values read back from a hand-edited URL", () => {
    const params = new URLSearchParams("wi=5&wt=-1&wm=0.2");
    expect(weightsFromSearchParams(params)).toEqual({ image: 1, text: 0, meta: 0.2 });
  });
});

describe("sameCategoryFromSearchParams", () => {
  it("defaults to true when absent", () => {
    expect(sameCategoryFromSearchParams(new URLSearchParams())).toBe(true);
  });

  it("is false only when sc=0", () => {
    expect(sameCategoryFromSearchParams(new URLSearchParams("sc=0"))).toBe(false);
    expect(sameCategoryFromSearchParams(new URLSearchParams("sc=1"))).toBe(true);
  });
});

describe("maxPriceRatioFromSearchParams", () => {
  it("is undefined when absent", () => {
    expect(maxPriceRatioFromSearchParams(new URLSearchParams())).toBeUndefined();
  });

  it("parses a valid ratio", () => {
    expect(maxPriceRatioFromSearchParams(new URLSearchParams("mpr=2.5"))).toBe(2.5);
  });

  it("rejects a ratio that wouldn't pass the API's gt=1 constraint", () => {
    expect(maxPriceRatioFromSearchParams(new URLSearchParams("mpr=1"))).toBeUndefined();
    expect(maxPriceRatioFromSearchParams(new URLSearchParams("mpr=abc"))).toBeUndefined();
  });
});
