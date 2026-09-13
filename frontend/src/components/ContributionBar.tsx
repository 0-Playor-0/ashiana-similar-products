import type { ItemBreakdown } from "../types";
import styles from "./ContributionBar.module.css";

const SIGNAL_LABEL: Record<keyof ItemBreakdown, string> = {
  image: "Image",
  text: "Description",
  meta: "Details",
};

const SIGNAL_COLOR: Record<keyof ItemBreakdown, string> = {
  image: "var(--signal-image)",
  text: "var(--signal-text)",
  meta: "var(--signal-meta)",
};

// §10.2: "a three-segment contribution bar showing the image/text/meta
// share of the score... raw cosine vs z on hover or focus." Contributions
// (weight * z) can be negative, so the bar's segment widths use each
// signal's positive share of the total positive contribution — the widths
// are a display simplification, the tooltip always shows the real numbers.
export function ContributionBar({ breakdown }: { breakdown: ItemBreakdown }) {
  const signals: (keyof ItemBreakdown)[] = ["image", "text", "meta"];
  const positive = signals.map((s) => Math.max(breakdown[s].contribution, 0));
  const total = positive.reduce((a, b) => a + b, 0);
  const shares = total > 0 ? positive.map((v) => v / total) : signals.map(() => 1 / 3);

  return (
    <div className={styles.bar}>
      {signals.map((signal, i) => {
        const { cosine, z, contribution } = breakdown[signal];
        return (
          <button
            key={signal}
            type="button"
            className={styles.segment}
            style={{ width: `${shares[i] * 100}%`, background: SIGNAL_COLOR[signal] }}
            aria-label={`${SIGNAL_LABEL[signal]} signal: cosine similarity ${cosine.toFixed(2)}, z-score ${z.toFixed(2)}`}
          >
            <span className={styles.tooltip} role="tooltip">
              {SIGNAL_LABEL[signal]}: cosine {cosine.toFixed(2)} · z {z.toFixed(2)} · contribution{" "}
              {contribution.toFixed(2)}
            </span>
          </button>
        );
      })}
    </div>
  );
}
