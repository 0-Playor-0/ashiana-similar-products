"""Phase 4 baselines (§8 Phase 4): random-within-type and same-type +
nearest-price. Used both for the label pool (this session) and later by
evaluate.py's metrics comparison — kept here, not duplicated, so both stay
consistent.
"""

import random

from core.bundle import Bundle


def _same_type_pool(bundle: Bundle, query_sku: str) -> list[str]:
    query_type = bundle.catalog[query_sku]["product_type"]
    return [
        sku
        for sku in bundle.ids
        if sku != query_sku and bundle.catalog[sku]["product_type"] == query_type
    ]


def random_within_type(bundle: Bundle, query_sku: str, k: int, seed: int) -> list[str]:
    pool = _same_type_pool(bundle, query_sku)
    rng = random.Random(seed)
    return rng.sample(pool, min(k, len(pool)))


def same_type_nearest_price(bundle: Bundle, query_sku: str, k: int) -> list[str]:
    pool = _same_type_pool(bundle, query_sku)
    query_price = bundle.catalog[query_sku].get("price_inr")
    if query_price is None:
        # No price to compare against — fall back to sku order (deterministic,
        # not meaningful, but this baseline degrades gracefully rather than
        # crashing on the rare product with no price).
        return sorted(pool)[:k]

    def price_gap(sku: str) -> float:
        price = bundle.catalog[sku].get("price_inr")
        return abs(price - query_price) if price is not None else float("inf")

    ranked = sorted(pool, key=lambda sku: (price_gap(sku), sku))
    return ranked[:k]
