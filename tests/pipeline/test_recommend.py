import numpy as np

from core.bundle import Bundle
from pipeline.recommend import recommend


def _tiny_bundle() -> Bundle:
    ids = ["a", "b", "c", "d", "e"]
    n = len(ids)
    manifest = {
        "bundle_version": "test",
        "default_weights": {"image": 0.5, "text": 0.2, "meta": 0.3},
    }
    catalog = {
        sku: {
            "sku": sku,
            "title": f"Product {sku}",
            "product_type": "earrings",
            "collection": None,
            "materials": [],
            "stones": [],
            "colors": [],
            "price_inr": 1000.0,
            "parent_id": None,
            "in_stock": True,
        }
        for sku in ids
    }
    rng = np.random.default_rng(0)
    S = {}
    Z = {}
    for signal in ("image", "text", "meta"):
        raw = rng.uniform(0, 1, size=(n, n))
        sym = (raw + raw.T) / 2
        np.fill_diagonal(sym, 1.0)
        S[signal] = sym
        mask = ~np.eye(n, dtype=bool)
        Z[signal] = (sym - sym[mask].mean()) / (sym[mask].std() + 1e-8)
    return Bundle(manifest=manifest, catalog=catalog, ids=ids, S=S, Z=Z)


def test_recommend_excludes_self_and_returns_k_items():
    bundle = _tiny_bundle()
    result = recommend(bundle, "a", k=3)
    assert result["query_sku"] == "a"
    skus = [item["sku"] for item in result["items"]]
    assert "a" not in skus
    assert len(skus) == 3


def test_recommend_deterministic_across_repeated_calls():
    bundle = _tiny_bundle()
    runs = {tuple(item["sku"] for item in recommend(bundle, "a", k=4)["items"]) for _ in range(5)}
    assert len(runs) == 1


def test_recommend_every_item_has_breakdown_and_reasons():
    bundle = _tiny_bundle()
    result = recommend(bundle, "b", k=2)
    for item in result["items"]:
        assert set(item["breakdown"].keys()) == {"image", "text", "meta"}
        assert isinstance(item["reasons"], list)
        assert len(item["reasons"]) <= 3
