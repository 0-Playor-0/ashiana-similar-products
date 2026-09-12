"""Load and validate the artifact bundle (§8 Phase 3, §9 API). The API loads
this once at startup and fails fast if it's missing or invalid — a bad bundle
should never surface as a 500 on the first request.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REQUIRED_MANIFEST_KEYS = {
    "bundle_version",
    "catalog_hash",
    "n_items",
    "models",
    "default_weights",
}
SIGNALS = ("image", "text", "meta")


class BundleValidationError(ValueError):
    pass


@dataclass
class Bundle:
    manifest: dict
    catalog: dict[str, dict]  # sku -> display/metadata fields
    ids: list[str]  # row/col order for every matrix below
    S: dict[str, np.ndarray]  # raw per-signal similarity, N×N
    Z: dict[str, np.ndarray]  # off-diagonal z-scored per-signal, N×N

    def index_of(self, sku: str) -> int:
        try:
            return self.ids.index(sku)
        except ValueError as e:
            raise KeyError(f"unknown sku: {sku}") from e


def _load_manifest(artifacts_dir: Path) -> dict:
    path = artifacts_dir / "manifest.json"
    if not path.exists():
        raise BundleValidationError(f"missing {path}")
    manifest = json.loads(path.read_text())
    missing = REQUIRED_MANIFEST_KEYS - manifest.keys()
    if missing:
        raise BundleValidationError(f"manifest.json missing keys: {sorted(missing)}")
    return manifest


def _load_catalog(artifacts_dir: Path) -> dict[str, dict]:
    path = artifacts_dir / "catalog.json"
    if not path.exists():
        raise BundleValidationError(f"missing {path}")
    catalog = json.loads(path.read_text())
    if not isinstance(catalog, dict):
        raise BundleValidationError("catalog.json must be a sku -> product object")
    return catalog


def _load_matrices(
    artifacts_dir: Path,
) -> tuple[list[str], dict[str, np.ndarray], dict[str, np.ndarray]]:
    path = artifacts_dir / "matrices.npz"
    if not path.exists():
        raise BundleValidationError(f"missing {path}")
    npz = np.load(path, allow_pickle=False)
    if "ids" not in npz:
        raise BundleValidationError("matrices.npz missing 'ids'")
    ids = [str(x) for x in npz["ids"]]

    S: dict[str, np.ndarray] = {}
    Z: dict[str, np.ndarray] = {}
    for signal in SIGNALS:
        s_key, z_key = f"S_{signal}", f"Z_{signal}"
        if s_key not in npz or z_key not in npz:
            raise BundleValidationError(f"matrices.npz missing '{s_key}' or '{z_key}'")
        S[signal] = npz[s_key]
        Z[signal] = npz[z_key]
    return ids, S, Z


def load_bundle(artifacts_dir: str | Path) -> Bundle:
    artifacts_dir = Path(artifacts_dir)
    manifest = _load_manifest(artifacts_dir)
    catalog = _load_catalog(artifacts_dir)
    ids, S, Z = _load_matrices(artifacts_dir)

    n = manifest["n_items"]
    if len(ids) != n:
        raise BundleValidationError(
            f"manifest says n_items={n} but matrices.npz has {len(ids)} ids"
        )
    if len(catalog) != n:
        raise BundleValidationError(
            f"manifest says n_items={n} but catalog.json has {len(catalog)} products"
        )
    if set(ids) != set(catalog.keys()):
        raise BundleValidationError("matrices.npz ids and catalog.json skus don't match")
    for signal in SIGNALS:
        for matrix_name, matrix in (("S_" + signal, S[signal]), ("Z_" + signal, Z[signal])):
            if matrix.shape != (n, n):
                raise BundleValidationError(
                    f"{matrix_name} has shape {matrix.shape}, expected ({n}, {n})"
                )

    return Bundle(manifest=manifest, catalog=catalog, ids=ids, S=S, Z=Z)
