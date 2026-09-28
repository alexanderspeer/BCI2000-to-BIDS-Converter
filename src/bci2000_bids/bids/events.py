from __future__ import annotations

from typing import Any
import numpy as np


def extract_events(states: dict[str, Any], fs: float, rules: dict[str, dict[str, Any]], columns: dict[str, str] | None = None) -> tuple[list[str], list[list[Any]]]:
    columns = columns or {}
    names = ["onset", "duration", "trial_type"]
    extra = [rule["column"] for rule in rules.values() if "column" in rule and rule["column"] not in names]
    extra += [column for column in columns.values() if column not in names and column not in extra]
    names += extra
    rows: list[list[Any]] = []
    for state, rule in rules.items():
        if state not in states:
            continue
        values = np.asarray(states[state]).ravel()
        if not len(values):
            continue
        strategy = rule.get("strategy", "value_change")
        changes = np.flatnonzero(values[1:] != values[:-1]) + 1
        if strategy == "rising_edge":
            starts = changes[(values[changes] != 0) & (values[changes - 1] == 0)]
            if values[0] != 0:
                starts = np.r_[0, starts]
            ends = None
        elif strategy == "falling_edge":
            starts = changes[(values[changes] == 0) & (values[changes - 1] != 0)]
            ends = None
        elif strategy in {"change", "value_change"}:
            starts, ends = changes, None
        elif strategy == "nonzero_change":
            starts, ends = changes[values[changes] != 0], None
        elif strategy == "interval":
            starts = np.r_[0, changes]
            ends = np.r_[starts[1:], len(values)]
            selected = values[starts] != 0
            starts, ends = starts[selected], ends[selected]
        else:
            raise ValueError(f"Unsupported event strategy: {strategy}")
        for index, start in enumerate(starts):
            duration = (int(ends[index]) - int(start)) / fs if ends is not None else 0.0
            row = [float(start) / fs, duration, str(rule.get("trial_type", rule.get("column", state)))]
            for column in extra:
                source = next((key for key, value in columns.items() if value == column), None)
                row.append(states[source][start].item() if source and source in states else (values[start].item() if column == rule.get("column", state) else "n/a"))
            rows.append(row)
    rows.sort(key=lambda row: (row[0], row[2]))
    return names, rows
