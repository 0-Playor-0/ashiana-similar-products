"""Human-readable reasons from a score breakdown + metadata overlap
(§8 Phase 3). Capped at 3, ordered by contribution — a fallback reason is
always included when it applies (transparency about it matters more than an
extra minor reason competing on raw contribution).
"""

from dataclasses import dataclass, field

_FALLBACK_PRIORITY = float("inf")


@dataclass
class ProductMeta:
    collection: str | None = None
    materials: list[str] = field(default_factory=list)
    stones: list[str] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)
    price_inr: float | None = None


def build_reasons(
    breakdown: dict[str, dict],
    query: ProductMeta,
    candidate: ProductMeta,
    fallback: bool,
    z_threshold: float,
    max_reasons: int = 3,
) -> list[str]:
    scored: list[tuple[float, str]] = []

    image = breakdown.get("image")
    if image and image.get("z", float("-inf")) >= z_threshold:
        scored.append((image.get("contribution", 0.0), "Visually similar"))

    text = breakdown.get("text")
    if text and text.get("z", float("-inf")) >= z_threshold:
        scored.append((text.get("contribution", 0.0), "Similar design details"))

    meta_contribution = breakdown.get("meta", {}).get("contribution", 0.0)

    if query.collection and query.collection == candidate.collection:
        scored.append((meta_contribution, f"Same collection: {candidate.collection.title()}"))

    for field_name, label in (("stones", "features"), ("materials", "is made of")):
        shared = set(getattr(query, field_name)) & set(getattr(candidate, field_name))
        for value in sorted(shared):
            scored.append((meta_contribution, f"Also {label} {value}"))

    if query.price_inr and candidate.price_inr:
        prices = (query.price_inr, candidate.price_inr)
        if max(prices) / min(prices) <= 1.5:
            scored.append(
                (
                    meta_contribution,
                    f"Similar price (₹{candidate.price_inr:,.0f} vs ₹{query.price_inr:,.0f})",
                )
            )

    if fallback:
        scored.append((_FALLBACK_PRIORITY, "From a related category"))

    scored.sort(key=lambda pair: -pair[0])
    return [text for _, text in scored[:max_reasons]]
