"""Phase 3 checkpoint: run the actual recommendation logic (core/) against the
real bundle, for every product, and save it — §8 Phase 3's "recommendations
grid (query + top-6) saved for every product" acceptance criterion.

This previews what the Phase 5 API will do; it is not the API. Kept in
pipeline/ (not core/) because it orchestrates I/O (loading the bundle,
writing a report) rather than being pure ranking logic itself — it calls
core.fusion / core.filters / core.reasons for all of that.
"""

import json

import yaml

from core.bundle import Bundle, load_bundle
from core.filters import CandidateMeta, category_filter, exclude_self_and_parent
from core.fusion import fuse_row, normalize_weights
from core.reasons import ProductMeta, build_reasons
from pipeline.paths import ARTIFACTS_DIR, CONFIG_DIR

SETTINGS = yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text())
TAXONOMY = yaml.safe_load((CONFIG_DIR / "taxonomy.yaml").read_text())
Z_THRESHOLD = SETTINGS["reasons"]["z_threshold"]


def _candidate_meta(bundle: Bundle, sku: str) -> CandidateMeta:
    p = bundle.catalog[sku]
    return CandidateMeta(
        sku=sku,
        product_type=p["product_type"],
        parent_id=p.get("parent_id"),
        price_inr=p.get("price_inr"),
        in_stock=p.get("in_stock"),
    )


def _product_meta(bundle: Bundle, sku: str) -> ProductMeta:
    p = bundle.catalog[sku]
    return ProductMeta(
        collection=p.get("collection"),
        materials=p.get("materials") or [],
        stones=p.get("stones") or [],
        colors=p.get("colors") or [],
        price_inr=p.get("price_inr"),
    )


def recommend(
    bundle: Bundle,
    query_sku: str,
    k: int = 6,
    weights: dict[str, float] | None = None,
    same_category: bool = True,
) -> dict:
    weights = normalize_weights(weights or bundle.manifest["default_weights"])
    q = bundle.index_of(query_sku)
    fused = fuse_row(bundle.Z, q, weights)

    all_meta = [_candidate_meta(bundle, sku) for sku in bundle.ids]
    query_candidate = _candidate_meta(bundle, query_sku)
    candidates = exclude_self_and_parent(all_meta, query_candidate)

    scores = {sku: float(fused[bundle.index_of(sku)]) for sku in bundle.ids}
    query_type = bundle.catalog[query_sku]["product_type"]
    ranked = category_filter(
        candidates,
        query_type,
        k,
        scores,
        TAXONOMY["product_type_similarity"],
        same_category=same_category,
    )

    query_pm = _product_meta(bundle, query_sku)
    items = []
    for sku, is_fallback in ranked:
        idx = bundle.index_of(sku)
        breakdown = {
            signal: {
                "cosine": float(bundle.S[signal][q, idx]),
                "z": float(bundle.Z[signal][q, idx]),
                "contribution": weights[signal] * float(bundle.Z[signal][q, idx]),
            }
            for signal in ("image", "text", "meta")
        }
        reasons = build_reasons(
            breakdown, query_pm, _product_meta(bundle, sku), is_fallback, Z_THRESHOLD
        )
        items.append(
            {
                "sku": sku,
                "title": bundle.catalog[sku]["title"],
                "score": scores[sku],
                "breakdown": breakdown,
                "reasons": reasons,
                "fallback": is_fallback,
            }
        )

    return {
        "query_sku": query_sku,
        "bundle_version": bundle.manifest["bundle_version"],
        "weights_used": weights,
        "items": items,
    }


def main() -> None:
    bundle = load_bundle(ARTIFACTS_DIR)
    results = {sku: recommend(bundle, sku) for sku in bundle.ids}

    out_path = ARTIFACTS_DIR / "eval" / "recommendations.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    n_fallback = sum(
        1 for r in results.values() for item in r["items"] if item["fallback"]
    )
    n_short = sum(1 for r in results.values() if len(r["items"]) < 6)
    print(f"wrote {out_path} ({len(results)} queries)")
    print(f"fallback items across all recommendations: {n_fallback}")
    print(f"queries with fewer than 6 results: {n_short}")


if __name__ == "__main__":
    main()
