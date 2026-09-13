import type { Weights } from "../types";
import { isAllZero, normalizeWeights } from "../lib/weights";
import styles from "./Inspector.module.css";

const SLIDERS: { key: keyof Weights; label: string }[] = [
  { key: "image", label: "How much looks matter" },
  { key: "text", label: "How much the description matters" },
  { key: "meta", label: "How much details matter" },
];

export function Inspector({
  weights,
  onWeightsChange,
  sameCategory,
  onSameCategoryChange,
  maxPriceRatio,
  onMaxPriceRatioChange,
}: {
  weights: Weights;
  onWeightsChange: (next: Weights) => void;
  sameCategory: boolean;
  onSameCategoryChange: (next: boolean) => void;
  maxPriceRatio: number | undefined;
  onMaxPriceRatioChange: (next: number | undefined) => void;
}) {
  const normalized = normalizeWeights(weights);

  return (
    <div className={styles.panel}>
      <h2 className={styles.heading}>Inspector</h2>
      {SLIDERS.map(({ key, label }) => (
        <div className={styles.sliderRow} key={key}>
          <div className={styles.sliderLabel}>
            <label htmlFor={`weight-${key}`}>{label}</label>
            <span className={styles.sliderReadout}>{normalized[key].toFixed(2)}</span>
          </div>
          <input
            id={`weight-${key}`}
            className={styles.slider}
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={weights[key]}
            onChange={(e) => onWeightsChange({ ...weights, [key]: Number(e.target.value) })}
          />
        </div>
      ))}
      {isAllZero(weights) && (
        <p className={styles.hint}>Move at least one slider above zero to see recommendations.</p>
      )}

      <div className={styles.row}>
        <label className={styles.checkboxLabel} htmlFor="same-category">
          <input
            id="same-category"
            type="checkbox"
            checked={sameCategory}
            onChange={(e) => onSameCategoryChange(e.target.checked)}
          />
          Same category only
        </label>
      </div>

      <div className={styles.row}>
        <label htmlFor="max-price-ratio">Max price ratio</label>
        <input
          id="max-price-ratio"
          className={styles.priceInput}
          type="number"
          min={1.1}
          step={0.1}
          placeholder="none"
          value={maxPriceRatio ?? ""}
          onChange={(e) => {
            const raw = e.target.value;
            if (raw === "") {
              onMaxPriceRatioChange(undefined);
              return;
            }
            const n = Number(raw);
            onMaxPriceRatioChange(Number.isNaN(n) || n <= 1 ? undefined : n);
          }}
        />
      </div>
    </div>
  );
}
