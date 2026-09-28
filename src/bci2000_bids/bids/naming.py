from __future__ import annotations

import re
from dataclasses import dataclass

from ..exceptions import BIDSConversionError


def normalize_label(value: str, field: str) -> str:
    value = value.strip()
    if value.startswith(f"{field}-"):
        value = value[len(field) + 1:]
    if not value or not re.fullmatch(r"[A-Za-z0-9]+", value):
        raise BIDSConversionError(f"{field} must contain only letters and numbers")
    return value


def normalize_entity(value: str, field: str) -> str:
    """Validate a non-prefix BIDS entity such as ``tracksys``."""
    value = value.strip()
    if not value or not re.fullmatch(r"[A-Za-z0-9]+", value):
        raise BIDSConversionError(f"{field} must contain only letters and numbers")
    return value


@dataclass(frozen=True)
class BIDSContext:
    subject: str
    session: str
    task: str
    run: int

    @property
    def prefix(self) -> str:
        return f"sub-{self.subject}_ses-{self.session}_task-{self.task}_run-{self.run:02d}"
