import numpy as np

from core.bundle import Bundle
from pipeline.label_pool import pool_for_query


def _bundle_with_types(type_counts: dict[str, int]) -> Bundle:
    ids = []
    catalog = {}
    for product_type, count in type_counts.items():
        for i in range(count):
            sku = f"{product_type}_{i}"
            ids.append(sku)
            catalog[sku] = {
                "sku": sku,
                "title": f"{product_type} {i}",
                "product_type": product_type,
                "collection": None,
                "materials": [],
                "stones": [],
                "colors": [],
                "price_inr": 100.0 + i * 10,
                "parent_id": None,
                "in_stock": True,
            }
    n = len(ids)
    rng = np.random.default_rng(0)
    S, Z = {}, {}
    for signal in ("image", "text", "meta"):
        raw = rng.uniform(0, 1, size=(n, n))
        sym = (raw + raw.T) / 2
        np.fill_diagonal(sym, 1.0)
        S[signal] = sym
        mask = ~np.eye(n, dtype=bool)
        Z[signal] = (sym - sym[mask].mean()) / (sym[mask].std() + 1e-8)
    manifest = {
        "bundle_version": "test",
        "default_weights": {"image": 0.5, "text": 0.2, "meta": 0.3},
    }
    return Bundle(manifest=manifest, catalog=catalog, ids=ids, S=S, Z=Z)


def test_pool_for_query_has_all_six_sources_and_deduped_pool():
    bundle = _bundle_with_types({"earrings": 12})
    entry = pool_for_query(bundle, "earrings_0")
    assert set(entry["sources"].keys()) == {
        "image_only",
        "text_only",
        "meta_only",
        "fused_default",
        "random_within_type",
        "same_type_nearest_price",
    }
    assert len(entry["pool"]) == len(set(entry["pool"]))
    assert "earrings_0" not in entry["pool"]


def test_same_type_nearest_price_baseline_is_in_pool_and_sorted_by_price():
    bundle = _bundle_with_types({"ring": 10})
    entry = pool_for_query(bundle, "ring_0")
    nearest = entry["sources"]["same_type_nearest_price"]
    prices = [bundle.catalog[sku]["price_inr"] for sku in nearest]
    assert prices == sorted(prices)
