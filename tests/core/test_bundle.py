import json

import numpy as np
import pytest

from core.bundle import BundleValidationError, load_bundle

SKUS = ["a", "b", "c"]


def _write_valid_bundle(tmp_path, n=3):
    manifest = {
        "bundle_version": "test",
        "catalog_hash": "deadbeef",
        "n_items": n,
        "models": {"image": "x", "text": "y"},
        "default_weights": {"image": 0.5, "text": 0.2, "meta": 0.3},
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    catalog = {sku: {"title": sku} for sku in SKUS[:n]}
    (tmp_path / "catalog.json").write_text(json.dumps(catalog))

    arrays = {"ids": np.array(SKUS[:n])}
    for signal in ("image", "text", "meta"):
        arrays[f"S_{signal}"] = np.eye(n)
        arrays[f"Z_{signal}"] = np.zeros((n, n))
    np.savez(tmp_path / "matrices.npz", **arrays)
    return tmp_path


def test_load_valid_bundle(tmp_path):
    _write_valid_bundle(tmp_path)
    bundle = load_bundle(tmp_path)
    assert bundle.ids == SKUS
    assert bundle.manifest["n_items"] == 3
    assert bundle.S["image"].shape == (3, 3)
    assert bundle.index_of("b") == 1


def test_missing_manifest_fails_fast(tmp_path):
    with pytest.raises(BundleValidationError, match="manifest.json"):
        load_bundle(tmp_path)


def test_missing_required_manifest_key(tmp_path):
    _write_valid_bundle(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    del manifest["n_items"]
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(BundleValidationError, match="missing keys"):
        load_bundle(tmp_path)


def test_shape_mismatch_between_manifest_and_matrices(tmp_path):
    _write_valid_bundle(tmp_path, n=3)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    manifest["n_items"] = 5
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(BundleValidationError, match="n_items"):
        load_bundle(tmp_path)


def test_catalog_ids_mismatch(tmp_path):
    _write_valid_bundle(tmp_path)
    catalog = json.loads((tmp_path / "catalog.json").read_text())
    catalog["not_a_real_sku"] = catalog.pop("a")
    (tmp_path / "catalog.json").write_text(json.dumps(catalog))
    with pytest.raises(BundleValidationError, match="don't match"):
        load_bundle(tmp_path)


def test_index_of_unknown_sku_raises_keyerror(tmp_path):
    _write_valid_bundle(tmp_path)
    bundle = load_bundle(tmp_path)
    with pytest.raises(KeyError):
        bundle.index_of("nonexistent")
