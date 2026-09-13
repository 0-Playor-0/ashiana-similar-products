import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { MotionConfig, motion } from "motion/react";
import { useProduct, useSimilar, useVersion } from "../api/queries";
import { resolveThumbUrl } from "../api/client";
import { ContributionBar } from "../components/ContributionBar";
import { Inspector } from "../components/Inspector";
import { ProductCard, ProductCardSkeleton } from "../components/ProductCard";
import { EmptyState, ErrorState } from "../components/StateMessage";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { describeError } from "../lib/errorMessage";
import { formatPrice } from "../lib/format";
import type { Weights } from "../types";
import {
  isAllZero,
  maxPriceRatioFromSearchParams,
  sameCategoryFromSearchParams,
  weightsFromSearchParams,
  weightsToSearchParamEntries,
} from "../lib/weights";
import styles from "./ProductPage.module.css";

const K = 6;
const DEBOUNCE_MS = 250;

export default function ProductPage() {
  const { sku } = useParams<{ sku: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const version = useVersion();
  const product = useProduct(sku);

  const [weights, setWeights] = useState<Weights | null>(() =>
    weightsFromSearchParams(searchParams),
  );
  const [sameCategory, setSameCategory] = useState(() =>
    sameCategoryFromSearchParams(searchParams),
  );
  const [maxPriceRatio, setMaxPriceRatio] = useState<number | undefined>(() =>
    maxPriceRatioFromSearchParams(searchParams),
  );

  // Seed the sliders from the bundle's tuned defaults once /version loads,
  // if the URL didn't already specify weights (§10.2: URL params are the
  // source of truth when present; the server default otherwise).
  useEffect(() => {
    if (weights === null && version.data) {
      setWeights(version.data.default_weights);
    }
  }, [version.data, weights]);

  const debouncedWeights = useDebouncedValue(weights, DEBOUNCE_MS);

  useEffect(() => {
    if (!debouncedWeights) return;
    const next = new URLSearchParams();
    for (const [key, value] of weightsToSearchParamEntries(debouncedWeights)) {
      next.set(key, value);
    }
    next.set("sc", sameCategory ? "1" : "0");
    if (maxPriceRatio !== undefined) next.set("mpr", String(maxPriceRatio));
    setSearchParams(next, { replace: true });
    // setSearchParams intentionally excluded: it's stable per React Router
    // but including searchParams itself here would create an update loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedWeights, sameCategory, maxPriceRatio]);

  const canQuerySimilar = debouncedWeights !== null && !isAllZero(debouncedWeights);
  const similar = useSimilar(canQuerySimilar ? sku : undefined, {
    k: K,
    w_image: debouncedWeights?.image,
    w_text: debouncedWeights?.text,
    w_meta: debouncedWeights?.meta,
    same_category: sameCategory,
    max_price_ratio: maxPriceRatio,
  });

  if (product.isPending) {
    return (
      <div>
        <span className={styles.back}>← Back to catalog</span>
        <div className={styles.hero}>
          <div className={styles.imageWrap} aria-hidden="true" />
          <ProductCardSkeleton />
        </div>
      </div>
    );
  }

  if (product.isError) {
    return (
      <div>
        <Link to="/" className={styles.back}>
          ← Back to catalog
        </Link>
        <ErrorState
          message={describeError("this piece", product.error)}
          onRetry={() => product.refetch()}
        />
      </div>
    );
  }

  const p = product.data;

  return (
    <div>
      <Link to="/" className={styles.back}>
        ← Back to catalog
      </Link>

      <div className={styles.hero}>
        <div className={styles.imageWrap}>
          <img
            src={resolveThumbUrl(p.thumb_url)}
            alt={p.title}
            className={styles.image}
          />
        </div>
        <div className={styles.details}>
          <h1 className={styles.title}>{p.title}</h1>
          <p className={styles.meta}>
            {formatPrice(p.price_inr)}
            {p.collection ? ` · ${p.collection} collection` : ""}
          </p>
          {p.descriptor_sentence && <p className={styles.description}>{p.descriptor_sentence}</p>}

          {weights && (
            <Inspector
              weights={weights}
              onWeightsChange={setWeights}
              sameCategory={sameCategory}
              onSameCategoryChange={setSameCategory}
              maxPriceRatio={maxPriceRatio}
              onMaxPriceRatioChange={setMaxPriceRatio}
            />
          )}
        </div>
      </div>

      <div className={styles.similarSection}>
        <h2 className={styles.sectionTitle}>Similar pieces</h2>

        {similar.isError && (
          <ErrorState
            message={describeError("similar pieces", similar.error)}
            onRetry={() => similar.refetch()}
          />
        )}

        {(similar.isPending || !canQuerySimilar) && !similar.isError && (
          <div className={styles.grid}>
            {Array.from({ length: K }, (_, i) => (
              <ProductCardSkeleton key={i} />
            ))}
          </div>
        )}

        {similar.isSuccess && similar.data.items.length === 0 && (
          <EmptyState
            message="No similar pieces match these filters."
            actionLabel="Reset filters"
            onAction={() => {
              setSameCategory(true);
              setMaxPriceRatio(undefined);
            }}
          />
        )}

        {similar.isSuccess && similar.data.items.length > 0 && (
          <MotionConfig reducedMotion="user">
            <div className={styles.grid}>
              {similar.data.items.map((item) => (
                <motion.div
                  key={item.product.sku}
                  layout
                  transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                >
                  <ProductCard
                    product={item.product}
                    reasons={item.reasons}
                    fallback={item.fallback}
                    contributionBar={<ContributionBar breakdown={item.breakdown} />}
                  />
                </motion.div>
              ))}
            </div>
          </MotionConfig>
        )}
      </div>
    </div>
  );
}
