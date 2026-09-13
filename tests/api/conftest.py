"""Builds a tiny synthetic artifact bundle on disk and points ARTIFACTS_DIR
at it *before* api.app.config (and anything that imports it) is loaded for
the first time — config.py reads the env var at import time, so this has to
happen at module-import time here, not inside a fixture function.

8 products: 6 "earrings" (e1..e6, varied prices/collections) and 2
"necklace_jewelry_set" (n1, n2) — few enough that a same_category query on
the necklace type must backfill from earrings (config/taxonomy.yaml gives
that pair a real nonzero product_type_similarity), exercising the fallback
path against the real taxonomy table rather than a mocked one.
"""

import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

_TMP_DIR = Path(tempfile.mkdtemp(prefix="ashiana-api-test-"))
os.environ["ARTIFACTS_DIR"] = str(_TMP_DIR)

IDS = ["e1", "e2", "e3", "e4", "e5", "e6", "n1", "n2"]
PRODUCT_TYPE = {
    **{f"e{i}": "earrings" for i in range(1, 7)},
    "n1": "necklace_jewelry_set",
    "n2": "necklace_jewelry_set",
}
COLLECTION = {"e1": "kundan", "e2": "kundan"}
PRICE = {
    "e1": 500.0,
    "e2": 520.0,
    "e3": 1000.0,
    "e4": 1500.0,
    "e5": 2000.0,
    "e6": 2500.0,
    "n1": 800.0,
    "n2": 4000.0,
}


def _build_catalog() -> dict:
    catalog = {}
    for sku in IDS:
        catalog[sku] = {
            "sku": sku,
            "title": f"Ashiana Test Product {sku}",
            "product_type": PRODUCT_TYPE[sku],
            "collection": COLLECTION.get(sku),
            "materials": ["gold_plated"] if sku != "e1" else [],
            "stones": ["kundan"] if sku == "e2" else [],
            "colors": ["gold"],
            "price_inr": PRICE[sku],
            "parent_id": None,
            "in_stock": True,
            "description_raw": f"Test description for {sku}.",
            "descriptor_sentence": f"Motifs: test {sku}",
            "attr_provenance": {"materials": "keyword"},
        }
    return catalog


def _build_matrices() -> dict:
    n = len(IDS)
    rng = np.random.default_rng(42)
    out = {"ids": np.array(IDS)}
    for signal in ("image", "text", "meta"):
        raw = rng.uniform(0, 1, size=(n, n))
        sym = (raw + raw.T) / 2
        np.fill_diagonal(sym, 1.0)
        mask = ~np.eye(n, dtype=bool)
        z = (sym - sym[mask].mean()) / (sym[mask].std() + 1e-8)
        out[f"S_{signal}"] = sym
        out[f"Z_{signal}"] = z
    return out


def _write_bundle(artifacts_dir: Path) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "thumbs").mkdir(exist_ok=True)
    (artifacts_dir / "eval").mkdir(exist_ok=True)

    manifest = {
        "bundle_version": "test-bundle-0001",
        "catalog_hash": "test-hash",
        "n_items": len(IDS),
        "models": {"image": "test-image-model", "text": "test-text-model"},
        "default_weights": {"image": 0.5, "text": 0.2, "meta": 0.3},
    }
    (artifacts_dir / "manifest.json").write_text(json.dumps(manifest))
    (artifacts_dir / "catalog.json").write_text(json.dumps(_build_catalog()))
    np.savez(artifacts_dir / "matrices.npz", **_build_matrices())
    (artifacts_dir / "eval" / "report.json").write_text(json.dumps({"n_queries": 0}))

    # One real (tiny) thumbnail file so the /thumbs static mount has
    # something to serve.
    (artifacts_dir / "thumbs" / "e1.webp").write_bytes(b"fake-webp-bytes")


_write_bundle(_TMP_DIR)

# Import only after ARTIFACTS_DIR is set and the fixture bundle exists on
# disk, so the lifespan's load_bundle() call (triggered when TestClient
# enters as a context manager) reads the test bundle, not the real one.
from fastapi.testclient import TestClient  # noqa: E402

from api.app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
