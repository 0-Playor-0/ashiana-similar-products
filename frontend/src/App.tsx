export default function App() {
  return (
    <div style={{ fontFamily: "sans-serif", padding: 24 }}>
      <h1>Ashiana similar pieces — a prototype</h1>
      <p>The shopper-facing catalog isn't built yet (Phase 6).</p>
      {import.meta.env.VITE_ENABLE_LABELING === "true" && (
        <p>
          <a href="/label">Go to the relevance labeling tool</a>
        </p>
      )}
    </div>
  );
}
