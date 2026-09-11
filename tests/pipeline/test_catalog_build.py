"""Regression check on the committed raw snapshot + clean.py output."""

import json

from pipeline.ingest.merge_raw import merge
from pipeline.paths import DATA_DIR


def test_merge_raw_matches_committed_catalog():
    raw_root = DATA_DIR / "raw"
    snapshot_dir = sorted(p for p in raw_root.iterdir() if p.is_dir())[-1]
    catalog = merge(snapshot_dir)

    assert len(catalog) >= 30, "Phase 0 acceptance: catalog.jsonl needs >=30 products"

    products = [json.loads(line) for line in (DATA_DIR / "catalog.jsonl").open()]
    committed_skus = {p["sku"] for p in products}
    assert committed_skus == set(catalog.keys())

    for p in products:
        assert p["title"]
        assert p["product_type"]
        assert p["image_urls"]
