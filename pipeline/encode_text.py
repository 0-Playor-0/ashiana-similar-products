"""Phase 2: encode each product's descriptor_sentence with bge-small-en-v1.5.

No query instruction prefix (LOCKED, §3) — symmetric item-to-item similarity,
not asymmetric query/passage retrieval.
"""

import json
import os

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from pipeline.paths import ARTIFACTS_DIR, DATA_DIR
from pipeline.schema import Product

MODEL_ID = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384
EMBEDDINGS_DIR = ARTIFACTS_DIR / "embeddings"


def _resolve_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _load_catalog() -> list[Product]:
    with (DATA_DIR / "catalog.jsonl").open() as f:
        return [Product.model_validate_json(line) for line in f]


def encode(products: list[Product], device: str) -> tuple[list[str], np.ndarray]:
    model = SentenceTransformer(MODEL_ID, device=device)
    skus = [p.sku for p in products]
    sentences = [p.descriptor_sentence or p.title for p in products]
    embeddings = model.encode(
        sentences,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    return skus, embeddings.astype(np.float32)


def main() -> None:
    products = [p for p in _load_catalog() if p.descriptor_sentence]
    if not products:
        raise RuntimeError(
            "No products have descriptor_sentence yet — run pipeline.describe first."
        )
    device = _resolve_device()
    print(f"encoding {len(products)} descriptors on device={device}")

    skus, embeddings = encode(products, device)

    norms = np.linalg.norm(embeddings, axis=1)
    print(
        f"embedding shape: {embeddings.shape}, "
        f"norm mean={norms.mean():.4f} std={norms.std():.4f}"
    )

    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_DIR / "E_text.npy", embeddings)
    (EMBEDDINGS_DIR / "ids_text.json").write_text(json.dumps(skus))
    print(f"wrote {EMBEDDINGS_DIR / 'E_text.npy'} and ids_text.json")


if __name__ == "__main__":
    main()
