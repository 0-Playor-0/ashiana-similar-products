"""Phase 3: Gower-style weighted metadata similarity (§8 Phase 3).

Reuses core.filters for the field-level math (rule 4: ranking/similarity
logic lives in one place) rather than reimplementing price similarity or
taxonomy-table lookups here.
"""

import json

import numpy as np
import yaml
from tqdm import tqdm

from core.filters import lookup_pair_similarity, price_similarity
from pipeline.paths import ARTIFACTS_DIR, CONFIG_DIR, DATA_DIR
from pipeline.schema import Product

SETTINGS = yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text())
TAXONOMY = yaml.safe_load((CONFIG_DIR / "taxonomy.yaml").read_text())

FIELD_WEIGHTS = SETTINGS["metadata"]["field_weights"]
PRICE_TAU = SETTINGS["metadata"]["price_tau"]


def _materials_similarity(a: list[str], b: list[str], table: dict[str, float]) -> float | None:
    """Soft set similarity: 0.5*(mean_a max_b sim(a,b) + mean_b max_a sim(b,a))."""
    if not a or not b:
        return None

    def one_way(xs: list[str], ys: list[str]) -> float:
        return sum(max(lookup_pair_similarity(table, x, y) for y in ys) for x in xs) / len(xs)

    return 0.5 * (one_way(a, b) + one_way(b, a))


def _jaccard(a: list[str], b: list[str]) -> float | None:
    if not a or not b:
        return None
    sa, sb = set(a), set(b)
    union = sa | sb
    return len(sa & sb) / len(union) if union else None


def field_similarity(a: Product, b: Product, field: str) -> float | None:
    """One field's similarity, or None if missing on either item (§8 Phase 3:
    "skip any field missing on either item and renormalize the weights").
    """
    if field == "product_type":
        if not a.product_type or not b.product_type:
            return None
        table = TAXONOMY["product_type_similarity"]
        return lookup_pair_similarity(table, a.product_type, b.product_type)
    if field == "collection":
        if not a.collection or not b.collection:
            return None
        return lookup_pair_similarity(TAXONOMY["collection_similarity"], a.collection, b.collection)
    if field == "materials":
        return _materials_similarity(a.materials, b.materials, TAXONOMY["material_similarity"])
    if field == "stones":
        return _jaccard(a.stones, b.stones)
    if field == "colors":
        return _jaccard(a.colors, b.colors)
    if field == "price":
        if a.price_inr is None or b.price_inr is None:
            return None
        return price_similarity(a.price_inr, b.price_inr, PRICE_TAU)
    raise ValueError(f"unknown metadata field: {field}")


def gower_similarity(a: Product, b: Product) -> float:
    """Weighted average of present field similarities, renormalized over the
    fields that are actually present on both items. 0.0 if none are present.
    """
    total_weight = 0.0
    weighted_sum = 0.0
    for field, weight in FIELD_WEIGHTS.items():
        s = field_similarity(a, b, field)
        if s is None:
            continue
        total_weight += weight
        weighted_sum += weight * s
    return weighted_sum / total_weight if total_weight > 0 else 0.0


def _load_catalog() -> list[Product]:
    with (DATA_DIR / "catalog.jsonl").open() as f:
        return [Product.model_validate_json(line) for line in f]


def build_matrix(products: list[Product]) -> tuple[list[str], np.ndarray]:
    n = len(products)
    ids = [p.sku for p in products]
    S = np.zeros((n, n), dtype=np.float32)
    for i in tqdm(range(n), desc="metadata similarity"):
        S[i, i] = 1.0
        for j in range(i + 1, n):
            s = gower_similarity(products[i], products[j])
            S[i, j] = s
            S[j, i] = s
    return ids, S


def main() -> None:
    products = _load_catalog()
    ids, S = build_matrix(products)

    embeddings_dir = ARTIFACTS_DIR / "embeddings"
    embeddings_dir.mkdir(parents=True, exist_ok=True)
    np.save(embeddings_dir / "S_meta.npy", S)
    (embeddings_dir / "ids_meta.json").write_text(json.dumps(ids))
    print(f"wrote S_meta {S.shape}, mean off-diagonal similarity={_offdiag_mean(S):.4f}")


def _offdiag_mean(S: np.ndarray) -> float:
    mask = ~np.eye(len(S), dtype=bool)
    return float(S[mask].mean())


if __name__ == "__main__":
    main()
