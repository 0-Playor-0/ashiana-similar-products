import styles from "./FilterChips.module.css";

export function FilterChips({
  label,
  options,
  active,
  onSelect,
}: {
  label: string;
  options: { value: string; count: number }[];
  active: string | null;
  onSelect: (value: string | null) => void;
}) {
  return (
    <div className={styles.row} role="group" aria-label={label}>
      {options.map((option) => {
        const isActive = active === option.value;
        return (
          <button
            key={option.value}
            type="button"
            className={isActive ? styles.chipActive : styles.chip}
            aria-pressed={isActive}
            onClick={() => onSelect(isActive ? null : option.value)}
          >
            {option.value} ({option.count})
          </button>
        );
      })}
    </div>
  );
}
