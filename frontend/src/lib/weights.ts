// Pure helpers for the inspector's weight sliders: clamping/normalizing for
// the live readout, and URL param round-tripping (§10.2: "the weights are
// stored in URL params ... so any state is shareable"). The actual fusion
// math stays server-side (core/fusion.py) — normalizeWeights here is only
// for the client-side live readout, never sent as a pre-normalized value.
import type { Weights } from "../types";

export function clampWeight(value: number): number {
  if (Number.isNaN(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

export function isAllZero(weights: Weights): boolean {
  return weights.image === 0 && weights.text === 0 && weights.meta === 0;
}

/** Normalized shares for the live readout next to each slider. Falls back to
 * equal thirds when all weights are zero, purely so the readout never shows
 * NaN/Infinity while the user is mid-drag — the API is never called with
 * an all-zero request (see isAllZero).
 */
export function normalizeWeights(weights: Weights): Weights {
  const total = weights.image + weights.text + weights.meta;
  if (total <= 0) return { image: 1 / 3, text: 1 / 3, meta: 1 / 3 };
  return {
    image: weights.image / total,
    text: weights.text / total,
    meta: weights.meta / total,
  };
}

const PARAM_KEYS = { image: "wi", text: "wt", meta: "wm" } as const;

export function weightsFromSearchParams(params: URLSearchParams): Weights | null {
  const wi = params.get(PARAM_KEYS.image);
  const wt = params.get(PARAM_KEYS.text);
  const wm = params.get(PARAM_KEYS.meta);
  if (wi === null || wt === null || wm === null) return null;
  const image = Number(wi);
  const text = Number(wt);
  const meta = Number(wm);
  if ([image, text, meta].some((n) => Number.isNaN(n))) return null;
  return { image: clampWeight(image), text: clampWeight(text), meta: clampWeight(meta) };
}

export function weightsToSearchParamEntries(weights: Weights): [string, string][] {
  return [
    [PARAM_KEYS.image, weights.image.toFixed(2)],
    [PARAM_KEYS.text, weights.text.toFixed(2)],
    [PARAM_KEYS.meta, weights.meta.toFixed(2)],
  ];
}

export function sameCategoryFromSearchParams(params: URLSearchParams): boolean {
  const raw = params.get("sc");
  return raw === null ? true : raw !== "0";
}

export function maxPriceRatioFromSearchParams(params: URLSearchParams): number | undefined {
  const raw = params.get("mpr");
  if (raw === null) return undefined;
  const n = Number(raw);
  return Number.isNaN(n) || n <= 1 ? undefined : n;
}
