from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ..exceptions import BIDSValidationError


def validate(root: Path, *, require_external: bool = False) -> str:
    if not (root / "dataset_description.json").exists():
        raise BIDSValidationError("Missing dataset_description.json")
    try:
        json.loads((root / "dataset_description.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise BIDSValidationError(f"Invalid dataset_description.json: {error}") from error
    command = ["bids-validator", str(root), "--json"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=300)
    except FileNotFoundError:
        message = "bids-validator not installed; external validation was not run"
        if require_external:
            raise BIDSValidationError(message)
        return message
    except subprocess.TimeoutExpired as error:
        raise BIDSValidationError("bids-validator timed out after 300 seconds") from error
    if result.returncode:
        raise BIDSValidationError(result.stdout or result.stderr)
    return result.stdout
