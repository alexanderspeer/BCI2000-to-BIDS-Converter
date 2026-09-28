from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .exceptions import ProfileValidationError


@dataclass(frozen=True)
class Profile:
    name: str = "default"
    events: dict[str, dict[str, Any]] = field(default_factory=dict)
    event_columns: dict[str, str] = field(default_factory=dict)
    motion: dict[str, dict[str, Any]] = field(default_factory=dict)
    ignore: frozenset[str] = frozenset()
    metadata: dict[str, Any] = field(default_factory=dict)


def load_profile(path: str | Path | None) -> Profile:
    if path is None:
        return Profile()
    source = Path(path)
    try:
        if source.suffix.lower() in {".yaml", ".yml"}:
            import yaml  # type: ignore
            data = yaml.safe_load(source.read_text(encoding="utf-8"))
        else:
            data = json.loads(source.read_text(encoding="utf-8"))
    except Exception as error:
        raise ProfileValidationError(f"Cannot read profile {source}: {error}") from error
    if not isinstance(data, dict):
        raise ProfileValidationError("Profile must be an object")
    events = data.get("events", {})
    motion = data.get("motion", {})
    columns = data.get("event_columns", {})
    ignored = data.get("ignore", [])
    if not all(isinstance(value, dict) for value in (events, motion)):
        raise ProfileValidationError("events and motion must be objects")
    if not isinstance(columns, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in columns.items()):
        raise ProfileValidationError("event_columns must map state names to column names")
    if not isinstance(ignored, list) or not all(isinstance(x, str) and x for x in ignored):
        raise ProfileValidationError("ignore must be a list of state names")
    reserved = {"onset", "duration", "trial_type"}
    for state, rule in motion.items():
        if not isinstance(state, str) or not state or not isinstance(rule, dict):
            raise ProfileValidationError("Each motion rule must be a named object")
        column = rule.get("column", state)
        if not isinstance(column, str) or not column or column in reserved:
            raise ProfileValidationError(f"Invalid motion column for {state}")
    for state, rule in events.items():
        if not isinstance(state, str) or not isinstance(rule, dict):
            raise ProfileValidationError("Each event rule must be a named object")
        if rule.get("strategy", "value_change") not in {"rising_edge", "falling_edge", "change", "nonzero_change", "interval", "value_change"}:
            raise ProfileValidationError(f"Unsupported event strategy for {state}")
        if rule.get("column", state) in reserved:
            raise ProfileValidationError(f"Reserved event column used by {state}")
    if len(set(columns.values())) != len(columns) or any(not value or value in reserved for value in columns.values()):
        raise ProfileValidationError("event_columns must contain unique non-reserved column names")
    destinations = set(events) | set(motion) | set(ignored) | set(columns)
    if len(destinations) != sum(map(len, (events, motion, ignored, columns))):
        raise ProfileValidationError("A state may have only one routing destination")
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ProfileValidationError("metadata must be an object")
    return Profile(str(data.get("name", source.stem)), dict(events), dict(columns), dict(motion), frozenset(ignored), dict(metadata))
