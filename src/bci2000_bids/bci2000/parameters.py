"""Conservative helpers for BCI2000 parameter mappings.

These implement the useful, device-neutral part of the neighboring MATLAB
parameter parser without copying MATLAB code or silently discarding units.
"""

from __future__ import annotations

import re
from typing import Any


_NUMBER = re.compile(r"^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(.*)$")


def parse_numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    match = _NUMBER.match(value)
    if not match or any(operator in value for operator in ("==", "~=", ">=", "<=", "&&", "||")):
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def parameter_values(parameters: dict[str, Any], name: str, aliases: tuple[str, ...] = ()) -> Any:
    """Return the first present parameter using case-insensitive aliases."""
    wanted = {name.casefold(), *(alias.casefold() for alias in aliases)}
    for key, value in parameters.items():
        if str(key).casefold() in wanted:
            return value
    return None


def flatten_values(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple)):
        result: list[Any] = []
        for item in value:
            result.extend(flatten_values(item))
        return result
    return [value]
