import { useEffect, useMemo, useRef, useState } from "react";
import { seededShuffle } from "../lib/shuffle";
import { buildLabelRecords, type LabelMap } from "../lib/labels";
import type {
  LabelPoolEntry,
  Product,
  RelevanceLabel,
} from "../types";
import "./Label.css";

// Fixed per-app-load seed for ordering queries/candidates — stable within a
// session (so refreshing doesn't reshuffle what you've already seen), not
// meant to be cryptographically random.
const SESSION_SEED = "ashiana-label-v1";

function useLabelData() {
  const [pool, setPool] = useState<LabelPoolEntry[] | null>(null);
  const [catalog, setCatalog] = useState<Record<string, Product> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/data/label_pool.json").then((r) => {
        if (!r.ok) throw new Error(`label_pool.json: ${r.status}`);
        return r.json();
      }),
      fetch("/data/catalog.json").then((r) => {
        if (!r.ok) throw new Error(`catalog.json: ${r.status}`);
        return r.json();
      }),
    ])
      .then(([poolData, catalogData]) => {
        setPool(poolData);
        setCatalog(catalogData);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  return { pool, catalog, error };
}

function ProductCard({
  product,
  role,
}: {
  product: Product | undefined;
  role: "query" | "candidate";
}) {
  if (!product) return null;
  return (
    <div className={`card card--${role}`}>
      <img
        src={`/thumbs/${product.sku}.webp`}
        alt={product.title}
        className="card__image"
      />
      <div className="card__title">{product.title}</div>
      <div className="card__meta">
        {product.price_inr != null ? `₹${product.price_inr.toLocaleString("en-IN")}` : ""}
        {product.collection ? ` · ${product.collection}` : ""}
      </div>
    </div>
  );
}

export default function Label() {
  const { pool, catalog, error } = useLabelData();
  const [labels, setLabels] = useState<LabelMap>({});
  const [queryIdx, setQueryIdx] = useState(0);
  const [candidateIdx, setCandidateIdx] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const orderedQueries = useMemo(() => {
    if (!pool) return [];
    return seededShuffle(pool, SESSION_SEED);
  }, [pool]);

  const shuffledCandidatesByQuery = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const entry of orderedQueries) {
      map.set(entry.query_sku, seededShuffle(entry.pool, SESSION_SEED + entry.query_sku));
    }
    return map;
  }, [orderedQueries]);

  const currentQuery = orderedQueries[queryIdx];
  const currentCandidates = currentQuery
    ? shuffledCandidatesByQuery.get(currentQuery.query_sku) ?? []
    : [];
  const currentCandidateSku = currentCandidates[candidateIdx];

  // `autoFocus` on a plain div isn't reliably honored by React/the DOM, and
  // this is the element keyboard shortcuts (0/1/2) listen on — focus it
  // explicitly once data has loaded, so the very first candidate is
  // keyboard-labelable without an extra click.
  useEffect(() => {
    if (currentQuery) containerRef.current?.focus();
  }, [currentQuery]);

  const totalTasks = orderedQueries.reduce((sum, q) => sum + q.pool.length, 0);
  const completedTasks =
    orderedQueries
      .slice(0, queryIdx)
      .reduce((sum, q) => sum + q.pool.length, 0) + candidateIdx;

  const advance = () => {
    if (candidateIdx + 1 < currentCandidates.length) {
      setCandidateIdx(candidateIdx + 1);
    } else if (queryIdx + 1 < orderedQueries.length) {
      setQueryIdx(queryIdx + 1);
      setCandidateIdx(0);
    }
    containerRef.current?.focus();
  };

  const recordLabel = (value: RelevanceLabel) => {
    if (!currentQuery || !currentCandidateSku) return;
    setLabels((prev) => ({
      ...prev,
      [currentQuery.query_sku]: {
        ...prev[currentQuery.query_sku],
        [currentCandidateSku]: value,
      },
    }));
    advance();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "0" || e.key === "1" || e.key === "2") {
      recordLabel(Number(e.key) as RelevanceLabel);
    }
  };

  const downloadLabels = () => {
    const records = buildLabelRecords(orderedQueries, labels);
    const blob = new Blob([JSON.stringify({ labels: records }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "relevance_labels.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  if (error) return <div className="label-page">Couldn't load labeling data: {error}</div>;
  if (!pool || !catalog) return <div className="label-page">Loading…</div>;
  if (!currentQuery) {
    return (
      <div className="label-page">
        <h1>All done</h1>
        <p>
          Labeled {Object.values(labels).reduce((n, m) => n + Object.keys(m).length, 0)} of{" "}
          {totalTasks} candidates.
        </p>
        <button onClick={downloadLabels}>Download labels</button>
      </div>
    );
  }

  const queryProduct = catalog[currentQuery.query_sku];
  const candidateProduct = currentCandidateSku ? catalog[currentCandidateSku] : undefined;
  const currentLabel = labels[currentQuery.query_sku]?.[currentCandidateSku];

  return (
    <div
      className="label-page"
      tabIndex={0}
      ref={containerRef}
      onKeyDown={handleKeyDown}
    >
      <h1 className="srOnly">Relevance labeling tool</h1>
      <div className="label-progress">
        Query {queryIdx + 1}/{orderedQueries.length} · candidate {candidateIdx + 1}/
        {currentCandidates.length} · {completedTasks}/{totalTasks} total
      </div>
      <div className="label-compare">
        <ProductCard product={queryProduct} role="query" />
        <div className="label-vs">vs.</div>
        <ProductCard product={candidateProduct} role="candidate" />
      </div>
      <p className="label-question">
        If a shopper is looking at the query product, would this candidate be a reasonable
        thing to show them as an alternative?
      </p>
      <div className="label-buttons">
        <button
          className={currentLabel === 0 ? "active" : ""}
          onClick={() => recordLabel(0)}
        >
          0 — Wrong / irrelevant
        </button>
        <button
          className={currentLabel === 1 ? "active" : ""}
          onClick={() => recordLabel(1)}
        >
          1 — Acceptable
        </button>
        <button
          className={currentLabel === 2 ? "active" : ""}
          onClick={() => recordLabel(2)}
        >
          2 — I'd happily show this
        </button>
      </div>
      <button className="label-download" onClick={downloadLabels}>
        Download labels ({Object.values(labels).reduce((n, m) => n + Object.keys(m).length, 0)}{" "}
        so far)
      </button>
    </div>
  );
}
