from pipeline.clean import _match_vocab, _pick_collection

SYNONYMS = {
    "cz": "zircon",
    "cubic zirconia": "zircon",
    "gold plated": "gold_plated",
}


def test_match_vocab_finds_synonym_and_direct_terms():
    text = "This gold plated ring has a cubic zirconia stone"
    materials = _match_vocab(text, ["gold_plated", "silver"], SYNONYMS)
    stones = _match_vocab(text, ["zircon", "pearl"], SYNONYMS)
    assert materials == ["gold_plated"]
    assert stones == ["zircon"]


def test_match_vocab_no_match_returns_empty():
    assert _match_vocab("a plain brass ring", ["zircon", "pearl"], SYNONYMS) == []


def test_pick_collection_priority_order():
    assert _pick_collection(["contemporary", "antique"]) == "antique"
    assert _pick_collection(["zircon", "kundan"]) == "kundan"
    assert _pick_collection([]) is None
    assert _pick_collection(["some_unlisted_value"]) == "some_unlisted_value"
