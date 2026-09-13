"""Orchestrates core/ ranking primitives against the loaded bundle (§9
implementation notes). Ranking logic itself lives only in core/ (rule 4) —
this module just shapes bundle data into API responses, the same split
pipeline/recommend.py uses for the offline preview, kept as a separate
implementation (not a shared import) so the API stays decoupled from the
pipeline package and its requirements (rule 5).

The bundle is loaded once at startup (FastAPI lifespan calls `configure`)
and held in a module-level global — there's exactly one process, one bundle,
for the API's lifetime, so a global is simpler than threading it through
every call. `_cached_similar` is the hot path (§9: "wrap the similarity
computation in functools.lru_cache, keyed by (sku, rounded weights, k,
filters)"); `configure` clears it so a reconfigured bundle (a real restart,
or a test swapping in a fixture bundle) can never serve a stale entry keyed
on the same tuple.
"""

import json
from functools import lru_cache

from api.app.config import ARTIFACTS_DIR, TAXONOMY, Z_THRESHOLD
from core.bundle import Bundle
from core.filters import (
    CandidateMeta,
    category_filter,
    exclude_self_and_parent,
    price_ratio_filter,
)
from core.fusion import fuse_row, normalize_weights
from core.reasons import ProductMeta, build_reasons

_bundle: Bundle | None = None


class NotLoadedError(RuntimeError):
    pass


def configure(bundle: Bundle) -> None:
    global _bundle
    _bundle = bundle
    _cached_similar.cache_clear()


def get_bundle() -> Bundle:
    if _bundle is None:
        raise NotLoadedError("bundle not loaded")
    return _bundle


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


def product_summary(bundle: Bundle, sku: str) -> dict:
    p = bundle.catalog[sku]
    return {
        "sku": sku,
        "title": p["title"],
        "product_type": p["product_type"],
        "collection": p.get("collection"),
        "price_inr": p.get("price_inr"),
        "thumb_url": f"/thumbs/{sku}.webp",
    }


def product_detail(bundle: Bundle, sku: str) -> dict:
    p = bundle.catalog[sku]
    return {
        **product_summary(bundle, sku),
        "descriptor_sentence": p.get("descriptor_sentence"),
        "materials": p.get("materials") or [],
        "stones": p.get("stones") or [],
        "colors": p.get("colors") or [],
        "in_stock": p.get("in_stock"),
        "attr_provenance": p.get("attr_provenance") or {},
    }


@lru_cache(maxsize=4096)
def _cached_similar(
    sku: str,
    w_image: float,
    w_text: float,
    w_meta: float,
    k: int,
    same_category: bool,
    max_price_ratio: float | None,
) -> dict:
    bundle = get_bundle()
    weights = normalize_weights({"image": w_image, "text": w_text, "meta": w_meta})
    q = bundle.index_of(sku)
    fused = fuse_row(bundle.Z, q, weights)

    all_meta = [_candidate_meta(bundle, s) for s in bundle.ids]
    query_meta = _candidate_meta(bundle, sku)
    candidates = exclude_self_and_parent(all_meta, query_meta)
    candidates = price_ratio_filter(candidates, query_meta.price_inr, max_price_ratio)

    scores = {s: float(fused[bundle.index_of(s)]) for s in bundle.ids}
    query_type = bundle.catalog[sku]["product_type"]
    ranked = category_filter(
        candidates,
        query_type,
        k,
        scores,
        TAXONOMY["product_type_similarity"],
        same_category=same_category,
    )

    query_pm = _product_meta(bundle, sku)
    items = []
    for rsku, is_fallback in ranked:
        idx = bundle.index_of(rsku)
        breakdown = {
            signal: {
                "cosine": float(bundle.S[signal][q, idx]),
                "z": float(bundle.Z[signal][q, idx]),
                "contribution": weights[signal] * float(bundle.Z[signal][q, idx]),
            }
            for signal in ("image", "text", "meta")
        }
        reasons = build_reasons(
            breakdown, query_pm, _product_meta(bundle, rsku), is_fallback, Z_THRESHOLD
        )
        items.append(
            {
                "sku": rsku,
                "score": scores[rsku],
                "breakdown": breakdown,
                "reasons": reasons,
                "fallback": is_fallback,
            }
        )
    return {"weights": weights, "items": items}


def get_similar(
    sku: str,
    k: int,
    w_image: float,
    w_text: float,
    w_meta: float,
    same_category: bool,
    max_price_ratio: float | None,
) -> dict:
    """Raises KeyError for an unknown sku, ValueError for invalid weights
    (both are the caller's job to turn into 404/422 — this stays a plain
    Python function so it's testable without FastAPI in the loop).
    """
    bundle = get_bundle()
    if sku not in bundle.catalog:
        raise KeyError(sku)

    rounded = (round(w_image, 3), round(w_text, 3), round(w_meta, 3))
    result = _cached_similar(sku, *rounded, k, same_category, max_price_ratio)
    weights, items = result["weights"], result["items"]

    full_items = [
        {
            "product": product_summary(bundle, it["sku"]),
            "score": it["score"],
            "breakdown": it["breakdown"],
            "reasons": it["reasons"],
            "fallback": it["fallback"],
        }
        for it in items
    ]
    return {
        "query_sku": sku,
        "bundle_version": bundle.manifest["bundle_version"],
        "weights_used": weights,
        "fallback_used": any(it["fallback"] for it in items),
        "items": full_items,
    }


@lru_cache(maxsize=1)
def get_eval_report() -> dict:
    """Contents of artifacts/eval/report.json (§9 GET /eval/report). Cached
    since it's static for the life of the process, same as the bundle.
    """
    path = ARTIFACTS_DIR / "eval" / "report.json"
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text())
