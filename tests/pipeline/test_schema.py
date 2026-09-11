from pipeline.schema import Product


def test_minimal_product_defaults():
    p = Product(sku="abc", title="Test Earring", product_type="earrings")
    assert p.materials == []
    assert p.stones == []
    assert p.colors == []
    assert p.image_urls == []
    assert p.collection is None
    assert p.price_inr is None


def test_full_product_round_trips_through_json():
    p = Product(
        sku="abc",
        title="Test Earring",
        product_type="earrings",
        collection="kundan",
        materials=["gold"],
        price_inr=999.0,
        image_urls=["https://example.com/a.jpg"],
    )
    reloaded = Product.model_validate_json(p.model_dump_json())
    assert reloaded == p
