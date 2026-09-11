from pipeline.describe import (
    ExtractedAttrs,
    LLMDescriptor,
    _apply_grounding_check,
    _build_descriptor_sentence,
    _split_sentences,
    _strip_json_fences,
    _strip_taxonomy_words,
    strip_boilerplate,
)
from pipeline.schema import Product

SYNONYMS = {"cz": "zircon", "cubic zirconia": "zircon"}


def test_split_sentences_basic():
    text = "This is great! Perfect gift for a Diva. Made from brass?"
    assert _split_sentences(text) == [
        "This is great!",
        "Perfect gift for a Diva.",
        "Made from brass?",
    ]


def test_split_sentences_empty():
    assert _split_sentences("") == []
    assert _split_sentences("   ") == []


def test_strip_boilerplate_removes_sentence_over_threshold():
    # 10 products so a sentence unique to one product (1/10 = 10%) stays safely
    # under the 20% boilerplate_min_share threshold, while the shared sentence
    # (10/10 = 100%) is well over it.
    products = [
        Product(
            sku=f"s{i}",
            title="t",
            product_type="earrings",
            description_raw=f"Perfect gift for a Diva! Unique detail {i}.",
        )
        for i in range(10)
    ]
    cleaned, report = strip_boilerplate(products)
    assert "perfect gift for a diva" not in cleaned["s0"].lower()
    assert "unique detail 0" in cleaned["s0"].lower()
    assert report["removed_sentences"][0]["n_products"] == 10


def test_strip_boilerplate_collapses_product_noun_variants():
    # Each individual noun variant is unique to one product (1/10 = 10%, under
    # the 20% threshold on its own) — only collapsing earring/ring/necklace/...
    # to a shared placeholder before frequency-counting pushes the combined
    # template over threshold (10/10 = 100%).
    nouns = [
        "earring",
        "ring",
        "necklace",
        "bracelet",
        "brooch",
        "cuff",
        "watch",
        "pendant",
        "jhumka",
        "bangle",
    ]
    products = [
        Product(
            sku=f"s{i}",
            title="t",
            product_type="earrings",
            description_raw=f"This latest trendy and stylish {noun} makes a statement.",
        )
        for i, noun in enumerate(nouns)
    ]
    cleaned, report = strip_boilerplate(products)
    assert cleaned["s0"] == ""
    assert cleaned["s1"] == ""
    assert report["removed_sentences"][0]["n_products"] == 10


def test_strip_json_fences():
    assert _strip_json_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _strip_json_fences('{"a": 1}') == '{"a": 1}'


def test_grounding_check_drops_ungrounded_extracted_terms():
    descriptor = LLMDescriptor(
        motifs=["peacock"],
        extracted=ExtractedAttrs(materials=["gold"], stones=["ruby"]),
    )
    source_text = "Gold plated peacock earring with cz stones"
    descriptor, log = _apply_grounding_check(descriptor, source_text, SYNONYMS)
    assert descriptor.extracted.materials == ["gold"]
    assert descriptor.extracted.stones == []
    assert log["dropped_extracted"]["stones"] == ["ruby"]


def test_grounding_check_flags_but_keeps_ungrounded_style_terms():
    descriptor = LLMDescriptor(style=["temple"], motifs=[])
    source_text = "A plain gold earring"
    descriptor, log = _apply_grounding_check(descriptor, source_text, SYNONYMS)
    assert descriptor.style == ["temple"]
    assert {"field": "style", "term": "temple"} in log["flagged_ungrounded_not_dropped"]


def test_build_descriptor_sentence_uses_template_when_populated():
    descriptor = LLMDescriptor(motifs=["peacock"], style=["temple"])
    sentence = _build_descriptor_sentence(descriptor, "Some Title", taxonomy={})
    assert sentence == "Motifs: peacock Style: temple"


def test_build_descriptor_sentence_falls_back_to_stripped_title():
    descriptor = LLMDescriptor()
    taxonomy = {
        "materials_vocab": ["gold"],
        "stones_vocab": [],
        "colors_vocab": [],
        "product_type_map": {"Earrings": "earrings"},
        "collection_map": {},
    }
    sentence = _build_descriptor_sentence(descriptor, "Gold Earrings for Women", taxonomy)
    assert "gold" not in sentence.lower()
    assert "for women" in sentence.lower()


def test_strip_taxonomy_words():
    taxonomy = {
        "materials_vocab": ["gold_plated"],
        "stones_vocab": ["zircon"],
        "colors_vocab": ["red"],
        "product_type_map": {"Earrings": "earrings"},
        "collection_map": {"Kundan Jewellery": "kundan"},
    }
    result = _strip_taxonomy_words("Red Gold Plated Zircon Kundan Earrings", taxonomy)
    assert result.lower() not in ("red gold plated zircon kundan earrings",)
    assert "red" not in result.lower()
    assert "zircon" not in result.lower()
