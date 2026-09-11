"""Phase 1: encode each product's preprocessed packshot with DINOv2-small.

Reads data/images/{sku}/model_input.png (already RGB, padded to a square with
the configured pad color, resized to 224x224 with no crop — see
pipeline/images.py). We disable the processor's own resize/crop (it would
otherwise center-crop, which is exactly what the padding was done to avoid)
and let it only rescale + normalize with the model's own mean/std.
"""

import json
import os

# DINOv2's position-embedding interpolation uses an op MPS doesn't implement
# yet (aten::upsample_bicubic2d); fall back to CPU for just that op. Must be
# set before torch touches MPS.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import numpy as np
import torch
import yaml
from PIL import Image
from tqdm import tqdm
from transformers import AutoImageProcessor, AutoModel

from pipeline.paths import ARTIFACTS_DIR, CONFIG_DIR, DATA_DIR

SETTINGS = yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text())
MODEL_ID = "facebook/dinov2-small"
EMBED_DIM = 384
BATCH_SIZE = 16

EMBEDDINGS_DIR = ARTIFACTS_DIR / "embeddings"


def _resolve_device() -> torch.device:
    cfg = SETTINGS["images"]["device"]
    if cfg != "auto":
        return torch.device(cfg)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _load_catalog_skus() -> list[str]:
    with (DATA_DIR / "catalog.jsonl").open() as f:
        return [json.loads(line)["sku"] for line in f]


def encode(skus: list[str], device: torch.device) -> np.ndarray:
    processor = AutoImageProcessor.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID).to(device).eval()

    embeddings = np.zeros((len(skus), EMBED_DIM), dtype=np.float32)

    with torch.inference_mode():
        for start in tqdm(range(0, len(skus), BATCH_SIZE), desc="encoding images"):
            batch_skus = skus[start : start + BATCH_SIZE]
            images = [
                Image.open(DATA_DIR / "images" / sku / "model_input.png").convert("RGB")
                for sku in batch_skus
            ]
            inputs = processor(
                images=images,
                return_tensors="pt",
                do_resize=False,
                do_center_crop=False,
            ).to(device)
            outputs = model(**inputs)
            pooled = outputs.pooler_output  # (B, 384), CLS token after layernorm
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
            embeddings[start : start + len(batch_skus)] = pooled.cpu().numpy()

    return embeddings


def main() -> None:
    skus = _load_catalog_skus()
    device = _resolve_device()
    print(f"encoding {len(skus)} images on device={device}")

    embeddings = encode(skus, device)

    norms = np.linalg.norm(embeddings, axis=1)
    print(
        f"embedding shape: {embeddings.shape}, "
        f"norm mean={norms.mean():.4f} std={norms.std():.4f}"
    )

    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_DIR / "E_image.npy", embeddings)
    (EMBEDDINGS_DIR / "ids.json").write_text(json.dumps(skus))
    print(f"wrote {EMBEDDINGS_DIR / 'E_image.npy'} and ids.json")


if __name__ == "__main__":
    main()
