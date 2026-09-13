"""Phase 3: assemble the artifact bundle (§8 Phase 3 build.py, §9 API contract).

Loads the three per-signal embeddings/matrices Phase 1-3 already produced
(E_image, E_text, S_meta), turns the embeddings into cosine-similarity
matrices, z-scores every signal off-diagonal (core.fusion), and writes the
bundle core.bundle.load_bundle expects: manifest.json, catalog.json,
matrices.npz.
"""

import hashlib
import json
import subprocess
from datetime import UTC, datetime

import numpy as np
import yaml

from core.fusion import offdiag_zscore
from pipeline.paths import ARTIFACTS_DIR, CONFIG_DIR, DATA_DIR
from pipeline.schema import Product

SETTINGS = yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text())
EMBEDDINGS_DIR = ARTIFACTS_DIR / "embeddings"


def _load_catalog() -> list[Product]:
    with (DATA_DIR / "catalog.jsonl").open() as f:
        return [Product.model_validate_json(line) for line in f]


def _sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=DATA_DIR.parent,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _load_signal_matrix(name: str, catalog_ids: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Returns (S, Z) for one signal, aligned to catalog_ids order.

    image/text are stored as L2-normalized embeddings (cosine similarity is
    then just E @ E.T); meta is already a precomputed similarity matrix.
    """
    ids_filename = {"image": "ids.json", "text": "ids_text.json", "meta": "ids_meta.json"}

    if name in ("image", "text"):
        E = np.load(EMBEDDINGS_DIR / f"E_{name}.npy")
        ids = json.loads((EMBEDDINGS_DIR / ids_filename[name]).read_text())
        E = _reorder(E, ids, catalog_ids)
        S = E @ E.T
    elif name == "meta":
        S = np.load(EMBEDDINGS_DIR / "S_meta.npy")
        ids = json.loads((EMBEDDINGS_DIR / "ids_meta.json").read_text())
        S = _reorder_matrix(S, ids, catalog_ids)
    else:
        raise ValueError(name)

    Z = offdiag_zscore(S)
    return S.astype(np.float32), Z.astype(np.float32)


def _reorder(E: np.ndarray, ids: list[str], target_ids: list[str]) -> np.ndarray:
    if ids == target_ids:
        return E
    index = {sku: i for i, sku in enumerate(ids)}
    order = [index[sku] for sku in target_ids]
    return E[order]


def _reorder_matrix(S: np.ndarray, ids: list[str], target_ids: list[str]) -> np.ndarray:
    if ids == target_ids:
        return S
    index = {sku: i for i, sku in enumerate(ids)}
    order = [index[sku] for sku in target_ids]
    return S[np.ix_(order, order)]


def _catalog_json(products: list[Product]) -> dict:
    return {p.sku: json.loads(p.model_dump_json()) for p in products}


def build() -> None:
    products = _load_catalog()
    catalog_ids = [p.sku for p in products]
    n = len(products)

    S_image, Z_image = _load_signal_matrix("image", catalog_ids)
    S_text, Z_text = _load_signal_matrix("text", catalog_ids)
    S_meta, Z_meta = _load_signal_matrix("meta", catalog_ids)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(
        ARTIFACTS_DIR / "matrices.npz",
        ids=np.array(catalog_ids),
        S_image=S_image,
        Z_image=Z_image,
        S_text=S_text,
        Z_text=Z_text,
        S_meta=S_meta,
        Z_meta=Z_meta,
    )

    catalog_path = DATA_DIR / "catalog.jsonl"
    taxonomy_path = CONFIG_DIR / "taxonomy.yaml"
    catalog_hash = _sha256_file(catalog_path)
    taxonomy_hash = _sha256_file(taxonomy_path)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    manifest = {
        "bundle_version": f"{timestamp}-{catalog_hash[:8]}",
        "catalog_hash": catalog_hash,
        "taxonomy_hash": taxonomy_hash,
        "n_items": n,
        "git_commit": _git_commit(),
        "models": {
            "image": "facebook/dinov2-small",
            "text": "BAAI/bge-small-en-v1.5",
            "llm": "openai/gpt-oss-20b",
            "prompt_version": SETTINGS["llm"]["prompt_version"],
        },
        "default_weights": SETTINGS["fusion"]["default_weights"],
    }
    (ARTIFACTS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (ARTIFACTS_DIR / "catalog.json").write_text(json.dumps(_catalog_json(products), indent=2))

    print(f"wrote matrices.npz {S_image.shape}, manifest.json, catalog.json ({n} products)")
    print(f"bundle_version={manifest['bundle_version']}")


if __name__ == "__main__":
    build()
