"""Regression test for a real deploy bug: artifacts/thumbs/ is gitignored
(D3) and genuinely doesn't exist on Render's fresh clone (no image pipeline
runs there). A request to /thumbs/{sku}.webp must 404 cleanly, not 500.

This needs a subprocess with its own fresh ARTIFACTS_DIR that never had a
thumbs/ subdirectory created — the shared tests/api/conftest.py fixture
bundle always pre-creates one (to test normal thumb serving), which would
never exercise this exact "directory doesn't exist yet" code path since
api.app.main is only imported once per test session.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def test_missing_thumbs_directory_404s_instead_of_500():
    with tempfile.TemporaryDirectory(prefix="ashiana-thumbs-regression-") as tmp:
        artifacts_dir = Path(tmp)
        ids = ["a", "b"]
        manifest = {
            "bundle_version": "regression-test",
            "catalog_hash": "x",
            "n_items": len(ids),
            "models": {},
            "default_weights": {"image": 0.5, "text": 0.2, "meta": 0.3},
        }
        catalog = {
            sku: {
                "sku": sku,
                "title": sku,
                "product_type": "earrings",
                "collection": None,
                "materials": [],
                "stones": [],
                "colors": [],
                "price_inr": 100.0,
                "parent_id": None,
                "in_stock": True,
            }
            for sku in ids
        }
        (artifacts_dir / "manifest.json").write_text(json.dumps(manifest))
        (artifacts_dir / "catalog.json").write_text(json.dumps(catalog))
        n = len(ids)
        matrices = {"ids": np.array(ids)}
        for signal in ("image", "text", "meta"):
            matrices[f"S_{signal}"] = np.eye(n, dtype=np.float32)
            matrices[f"Z_{signal}"] = np.zeros((n, n), dtype=np.float32)
        np.savez(artifacts_dir / "matrices.npz", **matrices)

        # Deliberately no thumbs/ subdirectory — the exact condition that
        # crashed on Render.
        assert not (artifacts_dir / "thumbs").exists()

        code = (
            "from fastapi.testclient import TestClient\n"
            "from api.app.main import app\n"
            "with TestClient(app) as client:\n"
            "    resp = client.get('/thumbs/does-not-exist.webp')\n"
            "    print('STATUS', resp.status_code)\n"
        )
        env = dict(os.environ)
        env["ARTIFACTS_DIR"] = str(artifacts_dir)
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "STATUS 404" in result.stdout, result.stdout + result.stderr
        # The endpoint should have created the directory so future lookups
        # go through StaticFiles' normal (already-tested) missing-file path.
        assert (artifacts_dir / "thumbs").is_dir()
