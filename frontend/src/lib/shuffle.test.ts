import { describe, expect, it } from "vitest";
import { seededShuffle } from "./shuffle";

describe("seededShuffle", () => {
  it("is deterministic for the same seed", () => {
    const items = ["a", "b", "c", "d", "e"];
    const first = seededShuffle(items, "query-1");
    const second = seededShuffle(items, "query-1");
    expect(first).toEqual(second);
  });

  it("differs across seeds (in general)", () => {
    const items = ["a", "b", "c", "d", "e", "f", "g", "h"];
    const a = seededShuffle(items, "query-1");
    const b = seededShuffle(items, "query-2");
    expect(a).not.toEqual(b);
  });

  it("preserves the same set of items", () => {
    const items = [1, 2, 3, 4, 5];
    const shuffled = seededShuffle(items, "seed");
    expect([...shuffled].sort()).toEqual([...items].sort());
  });

  it("does not mutate the input array", () => {
    const items = ["a", "b", "c"];
    const copy = [...items];
    seededShuffle(items, "seed");
    expect(items).toEqual(copy);
  });
});
