import { useHealthPing } from "../hooks/useHealthPing";
import styles from "./ColdStartBanner.module.css";

// §10.3 "Cold start": a non-blocking banner shown when /health hasn't
// answered within 3s — rendered once at the app shell so it applies across
// every route that talks to the API.
export default function ColdStartBanner() {
  const { showBanner } = useHealthPing();
  if (!showBanner) return null;

  return (
    <div className={styles.banner} role="status">
      <span className={styles.spinner} aria-hidden="true" />
      Starting the recommendation server. Free hosting sleeps when idle; this takes about a
      minute.
    </div>
  );
}
