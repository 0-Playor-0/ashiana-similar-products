"""Rule 5 / Phase 5 acceptance criterion: importing the API must never pull
in torch, transformers, or sentence_transformers.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_importing_api_main_does_not_import_torch():
    # A subprocess, not a plain `import`, so this is a clean-interpreter
    # check unaffected by whatever earlier tests in the same pytest session
    # (e.g. tests/pipeline/*) may have already imported.
    code = (
        "import api.app.main\n"
        "import sys\n"
        "heavy = {'torch', 'transformers', 'sentence_transformers'} & set(sys.modules)\n"
        "assert not heavy, f'heavy deps leaked into sys.modules: {heavy}'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=os.environ,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
