"""Candidate filtering and category fallback (§3 LOCKED, §8 Phase 3).
numpy-free, pure Python — imported by both the offline pipeline and the API.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateMeta:
    sku: str
    product_type: str
    parent_id: str | None = None
    price_inr: float | None = None
    in_stock: bool | None = None


def lookup_pair_similarity(table: dict[str, float], a: str, b: str) -> float:
    """Symmetric lookup into a flat "a|b" -> float taxonomy table (§8 Phase 3:
    "symmetric; unlisted pairs = 0; self = 1").
    """
    if a == b:
        return 1.0
    return table.get(f"{a}|{b}", table.get(f"{b}|{a}", 0.0))


def price_similarity(price_a: float, price_b: float, tau: float) -> float:
    """exp(-|ln(p_a/p_b)| / tau) — §8 Phase 3. Symmetric in a/b by construction
    (|ln(a/b)| == |ln(b/a)|); a 2x price ratio at the roadmap's default
    tau = ln(2) gives similarity e^-1 ≈ 0.37.
    """
    return math.exp(-abs(math.log(price_a / price_b)) / tau)


def exclude_self_and_parent(
    candidates: list[CandidateMeta], query: CandidateMeta
) -> list[CandidateMeta]:
    """Drop the query item itself, and — when query.parent_id is set — every
    other item sharing that parent_id (variants of the same design).
    """
    return [
        c
        for c in candidates
        if c.sku != query.sku
        and not (query.parent_id is not None and c.parent_id == query.parent_id)
    ]


def rank_by_score(candidates: list[CandidateMeta], scores: dict[str, float]) -> list[CandidateMeta]:
    """Score descending, sku ascending on ties (§3 LOCKED tie-break)."""
    return sorted(candidates, key=lambda c: (-scores[c.sku], c.sku))


def category_filter(
    candidates: list[CandidateMeta],
    query_type: str,
    k: int,
    scores: dict[str, float],
    type_similarity: dict[str, float],
    same_category: bool = True,
) -> list[tuple[str, bool]]:
    """Hard-filter to query_type; if fewer than k remain, backfill from other
    types ranked by (type similarity desc, fused score desc, sku asc), each
    flagged fallback=True (§3 LOCKED). same_category=False disables the hard
    filter entirely and just ranks everything by score.

    Returns up to k (sku, is_fallback) pairs.
    """
    if not same_category:
        ranked = rank_by_score(candidates, scores)
        return [(c.sku, False) for c in ranked[:k]]

    same_type = [c for c in candidates if c.product_type == query_type]
    ranked_same = rank_by_score(same_type, scores)

    if len(same_type) >= k:
        return [(c.sku, False) for c in ranked_same[:k]]

    other = [c for c in candidates if c.product_type != query_type]

    def type_sim(c: CandidateMeta) -> float:
        return lookup_pair_similarity(type_similarity, query_type, c.product_type)

    eligible_other = [c for c in other if type_sim(c) > 0]
    ranked_other = sorted(eligible_other, key=lambda c: (-type_sim(c), -scores[c.sku], c.sku))

    combined = [(c.sku, False) for c in ranked_same] + [(c.sku, True) for c in ranked_other]
    return combined[:k]


def price_ratio_filter(
    candidates: list[CandidateMeta], query_price: float | None, max_price_ratio: float | None
) -> list[CandidateMeta]:
    """Optional: drop candidates whose price differs from the query's by more
    than max_price_ratio. No-op if either price is missing or the filter is
    unset (§8 Phase 3: "Optional max_price_ratio filter").
    """
    if max_price_ratio is None or query_price is None:
        return candidates
    return [
        c
        for c in candidates
        if c.price_inr is None
        or (1 / max_price_ratio) <= (c.price_inr / query_price) <= max_price_ratio
    ]


def in_stock_filter(candidates: list[CandidateMeta], require_in_stock: bool) -> list[CandidateMeta]:
    """Optional: drop candidates known to be out of stock. A None (unknown)
    in_stock value passes through — §8 Phase 3 only asks to filter "when
    that field exists".
    """
    if not require_in_stock:
        return candidates
    return [c for c in candidates if c.in_stock is not False]
