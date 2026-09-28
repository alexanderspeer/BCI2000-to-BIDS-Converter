from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def write_motion(path: Path, states: dict[str, Any], rules: dict[str, dict[str, Any]], fs: float) -> tuple[list[str], int]:
    selected = [(name, str(rule.get("column", name))) for name, rule in rules.items() if name in states]
    if not selected:
        return [], 0
    count = len(states[selected[0][0]])
    if any(len(states[name]) != count for name, _ in selected):
        raise ValueError("Motion states have different sample counts")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        for index in range(count):
            writer.writerow([states[name][index].item() for name, _ in selected])
    return [column for _, column in selected], count


def motion_channels(path: Path, columns: list[str], rules: dict[str, dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["name", "type", "units", "description"])
        for column in columns:
            rule = next((value for key, value in rules.items() if value.get("column", key) == column), {})
            writer.writerow([column, rule.get("type", "POSITION"), rule.get("units", "n/a"), rule.get("description", "BCI2000 state")])
