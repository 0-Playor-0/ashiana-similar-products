import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useCategories, useProducts } from "../api/queries";
import { FilterChips } from "../components/FilterChips";
import { ProductCard, ProductCardSkeleton } from "../components/ProductCard";
import { EmptyState, ErrorState } from "../components/StateMessage";
import { describeError } from "../lib/errorMessage";
import styles from "./CatalogPage.module.css";

const SKELETON_COUNT = 12;

export default function CatalogPage() {
  const [productType, setProductType] = useState<string | null>(null);
  const [collection, setCollection] = useState<string | null>(null);
  // Title filter lives in the URL (?q=), driven by the global header search
  // (components/Layout.tsx) — not a local input here, so it works the same
  // way from any page, not just this one.
  const [searchParams, setSearchParams] = useSearchParams();
  const titleFilter = searchParams.get("q") ?? "";

  const categories = useCategories();
  const products = useProducts({
    product_type: productType ?? undefined,
    collection: collection ?? undefined,
  });

  const filtered = useMemo(() => {
    if (!products.data) return [];
    const needle = titleFilter.trim().toLowerCase();
    if (!needle) return products.data;
    return products.data.filter((p) => p.title.toLowerCase().includes(needle));
  }, [products.data, titleFilter]);

  const hasActiveFilters = Boolean(productType || collection || titleFilter.trim());

  const clearFilters = () => {
    setProductType(null);
    setCollection(null);
    const next = new URLSearchParams(searchParams);
    next.delete("q");
    setSearchParams(next, { replace: true });
  };

  return (
    <div>
      <div className={styles.header}>
        <div className={styles.intro}>
          <h1 className={styles.introTitle}>Find your next favourite piece</h1>
          <p className={styles.introSubtitle}>
            Filter by type or collection, or search by name up above.
          </p>
        </div>
        {categories.data && (
          <>
            <FilterChips
              label="Filter by product type"
              options={categories.data.product_types.map((row) => ({
                value: row.product_type,
                count: row.count,
              }))}
              active={productType}
              onSelect={setProductType}
            />
            <FilterChips
              label="Filter by collection"
              options={categories.data.collections.map((row) => ({
                value: row.collection,
                count: row.count,
              }))}
              active={collection}
              onSelect={setCollection}
            />
          </>
        )}
      </div>

      {products.isError && (
        <ErrorState
          message={describeError("the catalog", products.error)}
          onRetry={() => products.refetch()}
        />
      )}

      {products.isPending && !products.isError && (
        <div className={styles.grid}>
          {Array.from({ length: SKELETON_COUNT }, (_, i) => (
            <ProductCardSkeleton key={i} />
          ))}
        </div>
      )}

      {products.isSuccess && filtered.length === 0 && (
        <EmptyState
          message="No pieces match these filters."
          actionLabel={hasActiveFilters ? "Clear filters" : undefined}
          onAction={hasActiveFilters ? clearFilters : undefined}
        />
      )}

      {products.isSuccess && filtered.length > 0 && (
        <>
          <p className={styles.count}>
            {filtered.length} piece{filtered.length === 1 ? "" : "s"}
          </p>
          <div className={styles.grid}>
            {filtered.map((product) => (
              <ProductCard key={product.sku} product={product} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
