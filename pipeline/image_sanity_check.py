"""Phase 1 acceptance check: augmentation sanity test.

For a random sample of products, build a horizontally-flipped + 90%-center-cropped
copy of the packshot, run it through the same preprocessing + DINOv2 encoding as
the real pipeline, and check whether it retrieves the *original* product's
embedding at rank 1 among all N products. Passes if this holds for >=9/10.
"""

import json
import os
import random

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import numpy as np
import torch
import yaml
from PIL import Image, ImageOps
from transformers import AutoImageProcessor, AutoModel

from pipeline.encode_image import MODEL_ID, _resolve_device
from pipeline.images import PAD_COLOR, _pad_to_square
from pipeline.paths import ARTIFACTS_DIR, CONFIG_DIR, DATA_DIR

SETTINGS = yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text())
MODEL_SIZE = SETTINGS["images"]["model_size"]
N_SAMPLES = 10
SEED = 0


def _augment(img: Image.Image) -> Image.Image:
    img = ImageOps.mirror(img.convert("RGB"))
    w, h = img.size
    cw, ch = int(w * 0.9), int(h * 0.9)
    left, top = (w - cw) // 2, (h - ch) // 2
    return img.crop((left, top, left + cw, top + ch))


def _preprocess(img: Image.Image) -> Image.Image:
    squared = _pad_to_square(img, PAD_COLOR)
    return squared.resize((MODEL_SIZE, MODEL_SIZE), Image.BICUBIC)


def main() -> None:
    embeddings = np.load(ARTIFACTS_DIR / "embeddings" / "E_image.npy")
    ids = json.loads((ARTIFACTS_DIR / "embeddings" / "ids.json").read_text())
    sku_to_idx = {sku: i for i, sku in enumerate(ids)}

    device = _resolve_device()
    processor = AutoImageProcessor.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID).to(device).eval()

    random.seed(SEED)
    sample_skus = random.sample(ids, N_SAMPLES)

    hits = 0
    rows = []
    with torch.inference_mode():
        for sku in sample_skus:
            candidates = list((DATA_DIR / "images" / sku).glob("0.*"))
            img = Image.open(candidates[0])

            aug = _augment(img)
            aug_input = _preprocess(aug)

            inputs = processor(
                images=[aug_input], return_tensors="pt", do_resize=False, do_center_crop=False
            ).to(device)
            out = model(**inputs).pooler_output
            aug_emb = torch.nn.functional.normalize(out, p=2, dim=1).cpu().numpy()[0]

            sims = embeddings @ aug_emb
            ranked = np.argsort(-sims)
            rank1_sku = ids[ranked[0]]
            is_hit = rank1_sku == sku
            hits += is_hit
            rows.append(
                {
                    "sku": sku,
                    "rank1_sku": rank1_sku,
                    "hit": bool(is_hit),
                    "sim": float(sims[sku_to_idx[sku]]),
                }
            )

    result = {
        "n_samples": N_SAMPLES,
        "hits": hits,
        "pass": hits >= 9,
        "detail": rows,
    }
    out_path = ARTIFACTS_DIR / "eval" / "image_sanity_check.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
