from core.reasons import ProductMeta, build_reasons


def test_visually_similar_and_similar_design_above_threshold():
    breakdown = {
        "image": {"z": 2.0, "contribution": 1.0},
        "text": {"z": 1.5, "contribution": 0.5},
    }
    reasons = build_reasons(
        breakdown, ProductMeta(), ProductMeta(), fallback=False, z_threshold=1.0
    )
    assert reasons == ["Visually similar", "Similar design details"]


def test_below_threshold_signals_omitted():
    breakdown = {"image": {"z": 0.2, "contribution": 1.0}}
    reasons = build_reasons(
        breakdown, ProductMeta(), ProductMeta(), fallback=False, z_threshold=1.0
    )
    assert reasons == []


def test_same_collection_reason():
    query = ProductMeta(collection="kundan")
    candidate = ProductMeta(collection="kundan")
    reasons = build_reasons({}, query, candidate, fallback=False, z_threshold=1.0)
    assert reasons == ["Same collection: Kundan"]


def test_shared_stone_reason():
    query = ProductMeta(stones=["pearl", "zircon"])
    candidate = ProductMeta(stones=["pearl"])
    reasons = build_reasons({}, query, candidate, fallback=False, z_threshold=1.0)
    assert reasons == ["Also features pearl"]


def test_similar_price_reason_within_threshold():
    query = ProductMeta(price_inr=1299)
    candidate = ProductMeta(price_inr=1450)
    reasons = build_reasons({}, query, candidate, fallback=False, z_threshold=1.0)
    assert reasons == ["Similar price (₹1,450 vs ₹1,299)"]


def test_price_reason_omitted_when_too_different():
    query = ProductMeta(price_inr=100)
    candidate = ProductMeta(price_inr=10000)
    reasons = build_reasons({}, query, candidate, fallback=False, z_threshold=1.0)
    assert reasons == []


def test_fallback_reason_always_included():
    breakdown = {"image": {"z": 5.0, "contribution": 10.0}}
    query = ProductMeta(collection="kundan")
    candidate = ProductMeta(collection="kundan")
    reasons = build_reasons(breakdown, query, candidate, fallback=True, z_threshold=1.0)
    assert "From a related category" in reasons


def test_capped_at_three_reasons():
    breakdown = {
        "image": {"z": 5.0, "contribution": 1.0},
        "text": {"z": 5.0, "contribution": 0.9},
    }
    query = ProductMeta(collection="kundan", stones=["pearl"], price_inr=1000)
    candidate = ProductMeta(collection="kundan", stones=["pearl"], price_inr=1050)
    reasons = build_reasons(breakdown, query, candidate, fallback=False, z_threshold=1.0)
    assert len(reasons) == 3


def test_ordered_by_contribution_descending():
    breakdown = {
        "image": {"z": 5.0, "contribution": 0.1},
        "text": {"z": 5.0, "contribution": 5.0},
    }
    reasons = build_reasons(
        breakdown, ProductMeta(), ProductMeta(), fallback=False, z_threshold=1.0
    )
    assert reasons == ["Similar design details", "Visually similar"]
