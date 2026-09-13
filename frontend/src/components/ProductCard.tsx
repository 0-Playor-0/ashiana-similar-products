import { Link } from "react-router-dom";
import type { ProductSummary } from "../types";
import { resolveThumbUrl } from "../api/client";
import { formatPrice } from "../lib/format";
import styles from "./ProductCard.module.css";

export function ProductCard({
  product,
  reasons,
  fallback,
  contributionBar,
}: {
  product: ProductSummary;
  reasons?: string[];
  fallback?: boolean;
  contributionBar?: React.ReactNode;
}) {
  return (
    <Link to={`/p/${encodeURIComponent(product.sku)}`} className={styles.card}>
      <div className={styles.imageWrap}>
        <img
          src={resolveThumbUrl(product.thumb_url)}
          alt={product.title}
          className={styles.image}
          loading="lazy"
        />
      </div>
      {contributionBar}
      <div className={styles.body}>
        <div className={styles.title}>{product.title}</div>
        <div className={styles.price}>{formatPrice(product.price_inr)}</div>
        {reasons && reasons.length > 0 && (
          <ul className={styles.reasons}>
            {reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        )}
        {fallback && <span className={styles.badge}>From a related category</span>}
      </div>
    </Link>
  );
}

export function ProductCardSkeleton() {
  return (
    <div className={styles.skeleton} aria-hidden="true">
      <div className={styles.skeletonImage} />
      <div className={styles.skeletonLine} />
      <div className={styles.skeletonLine} />
    </div>
  );
}
