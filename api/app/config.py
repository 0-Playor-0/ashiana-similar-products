"""API-only configuration: env vars (§7 .env.example) plus the shared
config/*.yaml files. Deliberately independent of pipeline/paths.py — the API
has its own requirements.txt and must not pick up any coupling to the
offline pipeline's package (rule 5).
"""

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"

_artifacts_env = os.environ.get("ARTIFACTS_DIR", "artifacts")
_artifacts_path = Path(_artifacts_env)
ARTIFACTS_DIR = _artifacts_path if _artifacts_path.is_absolute() else ROOT / _artifacts_path

FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

SETTINGS = yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text())
TAXONOMY = yaml.safe_load((CONFIG_DIR / "taxonomy.yaml").read_text())

K_DEFAULT = SETTINGS["fusion"]["k_default"]
K_MAX = SETTINGS["fusion"]["k_max"]
Z_THRESHOLD = SETTINGS["reasons"]["z_threshold"]
