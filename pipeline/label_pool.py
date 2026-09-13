"""Phase 4: pick 25 query SKUs stratified by product_type, pool the union of
top-8 from image-only / text-only / meta-only / fused-default / the two
baselines for each, and write artifacts/eval/label_pool.json (§8 Phase 4).
"""

import json
import random

from core.bundle import load_bundle
from pipeline.baselines import random_within_type, same_type_nearest_price
from pipeline.paths import ARTIFACTS_DIR
from pipeline.recommend import recommend

POOL_K = 8
STRATIFICATION_SEED = 0
BASELINE_SEED = 0

# Allocation across the catalog's 7 product types, weighted by sqrt(count) so
# the 338-product earrings category doesn't crowd out the smaller ones (10
# each for bangle_bracelet/home_decor/ring, 9 for brooch) — every type still
# gets at least 2 of the 25 queries. Computed once from
# artifacts/eval/data_report.json's counts, not guessed:
#   earrings 338, necklace_jewelry_set 78, hair_accessory 17, home_decor 10,
#   bangle_bracelet 10, ring 10, brooch 9 -> sqrt-weighted shares of 25.
QUERIES_PER_TYPE = {
    "earrings": 10,
    "necklace_jewelry_set": 5,
    "hair_accessory": 2,
    "home_decor": 2,
    "bangle_bracelet": 2,
    "ring": 2,
    "brooch": 2,
}


def choose_query_skus(bundle) -> list[str]:
    by_type: dict[str, list[str]] = {}
    for sku in bundle.ids:
        by_type.setdefault(bundle.catalog[sku]["product_type"], []).append(sku)

    rng = random.Random(STRATIFICATION_SEED)
    chosen = []
    for product_type, n in QUERIES_PER_TYPE.items():
        pool = by_type.get(product_type, [])
        chosen.extend(rng.sample(pool, min(n, len(pool))))
    return sorted(chosen)


def _skus(bundle, query_sku: str, weights: dict[str, float]) -> list[str]:
    result = recommend(bundle, query_sku, k=POOL_K, weights=weights)
    return [item["sku"] for item in result["items"]]


def pool_for_query(bundle, query_sku: str) -> dict:
    sources = {
        "image_only": _skus(bundle, query_sku, {"image": 1.0, "text": 0.0, "meta": 0.0}),
        "text_only": _skus(bundle, query_sku, {"image": 0.0, "text": 1.0, "meta": 0.0}),
        "meta_only": _skus(bundle, query_sku, {"image": 0.0, "text": 0.0, "meta": 1.0}),
        "fused_default": _skus(bundle, query_sku, bundle.manifest["default_weights"]),
        "random_within_type": random_within_type(bundle, query_sku, POOL_K, BASELINE_SEED),
        "same_type_nearest_price": same_type_nearest_price(bundle, query_sku, POOL_K),
    }

    pooled_skus: list[str] = []
    for skus in sources.values():
        for sku in skus:
            if sku not in pooled_skus:
                pooled_skus.append(sku)

    return {
        "query_sku": query_sku,
        "query_title": bundle.catalog[query_sku]["title"],
        "product_type": bundle.catalog[query_sku]["product_type"],
        "sources": sources,
        "pool": pooled_skus,
    }


def main() -> None:
    bundle = load_bundle(ARTIFACTS_DIR)
    query_skus = choose_query_skus(bundle)

    pools = [pool_for_query(bundle, sku) for sku in query_skus]

    counts_by_type: dict[str, int] = {}
    for entry in pools:
        counts_by_type[entry["product_type"]] = counts_by_type.get(entry["product_type"], 0) + 1

    out_path = ARTIFACTS_DIR / "eval" / "label_pool.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(pools, indent=2, ensure_ascii=False))

    total_candidates = sum(len(e["pool"]) for e in pools)
    print(f"wrote {out_path}: {len(pools)} queries, {total_candidates} total pooled candidates")
    print(f"queries by product_type: {counts_by_type}")


if __name__ == "__main__":
    main()
