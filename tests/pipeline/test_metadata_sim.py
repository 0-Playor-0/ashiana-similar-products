import pytest

from pipeline.metadata_sim import _jaccard, _materials_similarity, gower_similarity
from pipeline.schema import Product


def _product(**kwargs):
    defaults = dict(sku="x", title="t", product_type="earrings")
    defaults.update(kwargs)
    return Product(**defaults)


def test_jaccard_identical_and_disjoint():
    assert _jaccard(["a", "b"], ["a", "b"]) == 1.0
    assert _jaccard(["a"], ["b"]) == 0.0
    assert _jaccard([], ["a"]) is None
    assert _jaccard(["a"], []) is None


def test_materials_similarity_exact_match_is_one():
    table = {}
    assert _materials_similarity(["gold"], ["gold"], table) == 1.0


def test_materials_similarity_uses_table_and_is_symmetric():
    table = {"gold_plated|rose_gold_plated": 0.7}
    a = _materials_similarity(["gold_plated"], ["rose_gold_plated"], table)
    b = _materials_similarity(["rose_gold_plated"], ["gold_plated"], table)
    assert a == pytest.approx(0.7)
    assert a == pytest.approx(b)


def test_materials_similarity_missing_returns_none():
    assert _materials_similarity([], ["gold"], {}) is None


def test_gower_similarity_self_is_one():
    p = _product(
        collection="kundan",
        materials=["gold"],
        stones=["pearl"],
        colors=["gold"],
        price_inr=1000,
    )
    assert gower_similarity(p, p) == pytest.approx(1.0)


def test_gower_similarity_no_shared_fields_is_zero():
    # every field empty/missing on both sides -> nothing to compare
    a = _product(sku="a", product_type="")
    b = _product(sku="b", product_type="")
    assert gower_similarity(a, b) == 0.0


def test_gower_similarity_symmetric():
    a = _product(sku="a", collection="kundan", price_inr=1000, stones=["pearl"])
    b = _product(sku="b", collection="zircon", price_inr=1500, stones=["zircon"])
    assert gower_similarity(a, b) == pytest.approx(gower_similarity(b, a))
