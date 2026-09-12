import math

import pytest

from core.filters import (
    CandidateMeta,
    category_filter,
    exclude_self_and_parent,
    in_stock_filter,
    lookup_pair_similarity,
    price_ratio_filter,
    price_similarity,
)


def _meta(sku, product_type="earrings", parent_id=None, price=None, in_stock=None):
    return CandidateMeta(
        sku=sku, product_type=product_type, parent_id=parent_id, price_inr=price, in_stock=in_stock
    )


def test_exclude_self_and_parent():
    query = _meta("q", parent_id="P1")
    candidates = [
        _meta("q"),  # the query itself
        _meta("sibling", parent_id="P1"),  # shares parent_id
        _meta("other", parent_id="P2"),
        _meta("no_parent", parent_id=None),
    ]
    result = {c.sku for c in exclude_self_and_parent(candidates, query)}
    assert result == {"other", "no_parent"}


def test_exclude_self_and_parent_no_parent_id_only_excludes_self():
    query = _meta("q", parent_id=None)
    candidates = [_meta("q"), _meta("a", parent_id=None), _meta("b", parent_id=None)]
    result = {c.sku for c in exclude_self_and_parent(candidates, query)}
    assert result == {"a", "b"}


def test_category_filter_no_fallback_when_enough_same_type():
    candidates = [_meta(f"e{i}") for i in range(10)]  # all "earrings"
    scores = {c.sku: 1.0 - i * 0.01 for i, c in enumerate(candidates)}
    result = category_filter(candidates, "earrings", k=6, scores=scores, type_similarity={})
    assert len(result) == 6
    assert all(not is_fallback for _, is_fallback in result)


def test_category_filter_fallback_triggers_exactly_when_same_type_below_k():
    same = [_meta(f"r{i}", product_type="ring") for i in range(3)]
    other = [_meta(f"b{i}", product_type="bangle_bracelet") for i in range(5)]
    scores = {c.sku: 1.0 for c in same + other}
    type_similarity = {"ring|bangle_bracelet": 0.5}

    # k=3: exactly enough same-type candidates -> no fallback
    result_k3 = category_filter(
        same + other, "ring", k=3, scores=scores, type_similarity=type_similarity
    )
    assert all(not is_fallback for _, is_fallback in result_k3)

    # k=4: one short -> fallback kicks in for the backfilled item(s)
    result_k4 = category_filter(
        same + other, "ring", k=4, scores=scores, type_similarity=type_similarity
    )
    fallback_flags = [is_fallback for _, is_fallback in result_k4]
    assert fallback_flags == [False, False, False, True]


def test_category_filter_excludes_zero_similarity_types_from_fallback():
    same = [_meta("r0", product_type="ring")]
    unrelated = [_meta("h0", product_type="home_decor")]  # similarity 0, not in table
    scores = {"r0": 1.0, "h0": 1.0}
    result = category_filter(same + unrelated, "ring", k=5, scores=scores, type_similarity={})
    assert [sku for sku, _ in result] == ["r0"]


def test_category_filter_same_category_false_disables_hard_filter():
    candidates = [_meta("r0", product_type="ring"), _meta("e0", product_type="earrings")]
    scores = {"r0": 0.5, "e0": 0.9}
    result = category_filter(
        candidates, "ring", k=2, scores=scores, type_similarity={}, same_category=False
    )
    assert [sku for sku, is_fb in result] == ["e0", "r0"]
    assert all(not is_fb for _, is_fb in result)


def test_lookup_pair_similarity_symmetric_and_self():
    table = {"antique|oxidised": 0.6}
    assert lookup_pair_similarity(table, "antique", "oxidised") == 0.6
    assert lookup_pair_similarity(table, "oxidised", "antique") == 0.6
    assert lookup_pair_similarity(table, "antique", "antique") == 1.0
    assert lookup_pair_similarity(table, "antique", "kundan") == 0.0


def test_price_similarity_symmetry_property():
    for a, b, tau in [(1000, 2000, math.log(2)), (500, 500, 0.5), (99, 4001, 1.0)]:
        assert price_similarity(a, b, tau) == pytest.approx(price_similarity(b, a, tau))


def test_price_similarity_known_value_at_2x_ratio_and_default_tau():
    tau = math.log(2)
    assert price_similarity(1000, 2000, tau) == pytest.approx(math.e**-1, rel=1e-6)


def test_price_ratio_filter():
    candidates = [
        _meta("cheap", price=100),
        _meta("mid", price=180),
        _meta("expensive", price=1000),
    ]
    result = {c.sku for c in price_ratio_filter(candidates, query_price=150, max_price_ratio=2.0)}
    assert result == {"cheap", "mid"}


def test_price_ratio_filter_noop_when_unset():
    candidates = [_meta("a", price=10), _meta("b", price=10000)]
    assert price_ratio_filter(candidates, query_price=100, max_price_ratio=None) == candidates
    assert price_ratio_filter(candidates, query_price=None, max_price_ratio=2.0) == candidates


def test_in_stock_filter():
    candidates = [
        _meta("in", in_stock=True),
        _meta("out", in_stock=False),
        _meta("unknown", in_stock=None),
    ]
    result = {c.sku for c in in_stock_filter(candidates, require_in_stock=True)}
    assert result == {"in", "unknown"}
    assert in_stock_filter(candidates, require_in_stock=False) == candidates
