"""Endpoint contract tests (§9, §11 "API: endpoint contract tests, parameter
validation, 404/422 paths, the no-torch import test, and a check that the
bundle-version header is present"). Uses the tiny 8-product fixture bundle
built in conftest.py.
"""


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_every_response_carries_bundle_version_header(client):
    for path in ("/health", "/version", "/categories", "/products"):
        resp = client.get(path)
        assert resp.headers["x-bundle-version"] == "test-bundle-0001", path


def test_version(client):
    resp = client.get("/version")
    body = resp.json()
    assert body["bundle_version"] == "test-bundle-0001"
    assert body["n_items"] == 8
    assert body["default_weights"] == {"image": 0.5, "text": 0.2, "meta": 0.3}
    assert "image" in body["models"]


def test_categories(client):
    resp = client.get("/categories")
    body = resp.json()
    types = {row["product_type"]: row["count"] for row in body["product_types"]}
    assert types == {"earrings": 6, "necklace_jewelry_set": 2}
    collections = {row["collection"]: row["count"] for row in body["collections"]}
    assert collections == {"kundan": 2}  # only e1/e2 have a collection tag


def test_products_list_and_filter(client):
    resp = client.get("/products")
    assert resp.status_code == 200
    assert len(resp.json()) == 8

    resp = client.get("/products", params={"product_type": "necklace_jewelry_set"})
    skus = {p["sku"] for p in resp.json()}
    assert skus == {"n1", "n2"}

    resp = client.get("/products", params={"collection": "kundan"})
    skus = {p["sku"] for p in resp.json()}
    assert skus == {"e1", "e2"}


def test_get_product_detail(client):
    resp = client.get("/products/e2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sku"] == "e2"
    assert body["thumb_url"] == "/thumbs/e2.webp"
    assert body["stones"] == ["kundan"]
    assert body["descriptor_sentence"] == "Motifs: test e2"


def test_get_product_detail_404(client):
    resp = client.get("/products/does-not-exist")
    assert resp.status_code == 404
    assert "does-not-exist" in resp.json()["detail"]


def test_similar_default_weights_and_shape(client):
    resp = client.get("/products/e1/similar")
    assert resp.status_code == 200
    body = resp.json()
    assert body["query_sku"] == "e1"
    assert body["bundle_version"] == "test-bundle-0001"
    assert body["weights_used"] == {"image": 0.5, "text": 0.2, "meta": 0.3}
    # k_default (6) exceeds the 5 other earrings, so this also exercises the
    # fallback backfill (1 item pulled from necklace_jewelry_set).
    assert len(body["items"]) == 6
    assert body["fallback_used"] is True

    for item in body["items"]:
        assert item["product"]["sku"] != "e1"
        assert set(item["breakdown"].keys()) == {"image", "text", "meta"}
        for signal in ("image", "text", "meta"):
            assert set(item["breakdown"][signal].keys()) == {"cosine", "z", "contribution"}
        assert isinstance(item["reasons"], list)
        assert len(item["reasons"]) <= 3
        assert isinstance(item["fallback"], bool)


def test_similar_404_unknown_sku(client):
    resp = client.get("/products/nope/similar")
    assert resp.status_code == 404


def test_similar_k_out_of_range_is_422(client):
    resp = client.get("/products/e1/similar", params={"k": 0})
    assert resp.status_code == 422
    resp = client.get("/products/e1/similar", params={"k": 999})
    assert resp.status_code == 422


def test_similar_negative_weight_is_422(client):
    resp = client.get("/products/e1/similar", params={"w_image": -1})
    assert resp.status_code == 422


def test_similar_all_zero_weights_is_422(client):
    resp = client.get(
        "/products/e1/similar",
        params={"w_image": 0, "w_text": 0, "w_meta": 0},
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_similar_weights_are_normalized_server_side(client):
    resp = client.get(
        "/products/e1/similar",
        params={"w_image": 2, "w_text": 0, "w_meta": 2},
    )
    assert resp.status_code == 200
    weights = resp.json()["weights_used"]
    assert weights == {"image": 0.5, "text": 0.0, "meta": 0.5}


def test_similar_max_price_ratio_filters_candidates(client):
    # e1 is 500; within a 1.2x ratio only e2 (520) qualifies among earrings.
    resp = client.get(
        "/products/e1/similar",
        params={"k": 5, "max_price_ratio": 1.2, "same_category": True},
    )
    assert resp.status_code == 200
    skus = [item["product"]["sku"] for item in resp.json()["items"]]
    assert skus == ["e2"]


def test_similar_category_fallback(client):
    # Only 2 necklace_jewelry_set items exist; k=4 same_category=True must
    # backfill from earrings (nonzero product_type_similarity in
    # config/taxonomy.yaml) and flag those as fallback.
    resp = client.get("/products/n1/similar", params={"k": 4})
    assert resp.status_code == 200
    body = resp.json()
    assert body["fallback_used"] is True
    fallback_flags = [item["fallback"] for item in body["items"]]
    assert fallback_flags[0] is False  # n2, the one other same-type item, ranks first
    assert any(fallback_flags[1:])


def test_similar_same_category_false_disables_hard_filter(client):
    resp = client.get("/products/n1/similar", params={"k": 4, "same_category": False})
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["fallback"] is False for item in body["items"])


def test_eval_report(client):
    resp = client.get("/eval/report")
    assert resp.status_code == 200
    assert resp.json() == {"n_queries": 0}


def test_thumbs_static_file(client):
    resp = client.get("/thumbs/e1.webp")
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "public, max-age=86400"


def test_thumbs_missing_file_404(client):
    resp = client.get("/thumbs/does-not-exist.webp")
    assert resp.status_code == 404


def test_docs_renders(client):
    resp = client.get("/docs")
    assert resp.status_code == 200
