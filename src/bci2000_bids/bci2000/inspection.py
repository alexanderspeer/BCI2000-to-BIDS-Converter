from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .reader import BCI2000Recording


@dataclass
class StateStatistics:
    name: str
    bit_width: int
    unique_values: int | None = None
    transitions: int | None = None
    kind: str = "header-only"


def inspect_recording(path: str) -> dict[str, Any]:
    with BCI2000Recording(path) as recording:
        return {"filename": recording.path.name, "path": str(recording.path), "duration_seconds": recording.duration,
                "sampling_frequency_hz": recording.sampling_frequency, "number_of_channels": recording.n_channels,
                "number_of_samples": recording.n_samples, "channel_names": recording.channel_names,
                "states": [StateStatistics(name, int(recording.state_definitions[name].get("length", 0))).__dict__ for name in recording.states],
                "parameters": {key: str(value) for key, value in recording.parameters.items() if key in {"SamplingRate", "DataFormat", "Application", "SignalSource", "ChannelNames", "SourceChUnits"}}}


def state_statistics(values: Any, name: str, bit_width: int = 0) -> StateStatistics:
    array = np.asarray(values).ravel()
    transitions = int(np.count_nonzero(array[1:] != array[:-1])) if len(array) > 1 else 0
    return StateStatistics(name, bit_width, int(len(np.unique(array))), transitions, "continuous" if len(np.unique(array)) > 20 else "discrete")


def analyze_states(path: str, progress: Callable[[float], None] | None = None) -> dict[str, dict[str, Any]]:
    """Scan state values without retaining neural samples or complete state arrays."""
    with BCI2000Recording(path) as recording:
        names = recording.states
        stats: dict[str, dict[str, Any]] = {
            name: {"bit_width": int(recording.state_definitions[name].get("length", 0)), "minimum": None,
                   "maximum": None, "unique_values": set(), "transitions": 0, "nonzero_samples": 0,
                   "previous": None}
            for name in names
        }
        processed = 0
        for signal, chunk in recording.iter_chunks(names, signal=False):
            del signal
            for name in names:
                values = np.asarray(chunk[name]).reshape(-1)
                if not len(values):
                    continue
                current = stats[name]
                current["minimum"] = int(values.min()) if current["minimum"] is None else min(current["minimum"], int(values.min()))
                current["maximum"] = int(values.max()) if current["maximum"] is None else max(current["maximum"], int(values.max()))
                unique = current["unique_values"]
                if len(unique) <= 128:
                    unique.update(int(value) for value in np.unique(values))
                current["nonzero_samples"] += int(np.count_nonzero(values))
                current["transitions"] += int(np.count_nonzero(values[1:] != values[:-1]))
                if current["previous"] is not None and int(values[0]) != current["previous"]:
                    current["transitions"] += 1
                current["previous"] = int(values[-1])
            processed += len(np.asarray(next(iter(chunk.values()))).reshape(-1)) if chunk else 0
            if progress:
                progress(min(1.0, processed / max(1, recording.n_samples)))
        result = {}
        for name, current in stats.items():
            unique = current.pop("unique_values")
            current.pop("previous")
            current["unique_values"] = len(unique) if len(unique) <= 128 else 129
            current["transition_fraction"] = current["transitions"] / max(1, recording.n_samples - 1)
            current["percent_nonzero"] = 100 * current["nonzero_samples"] / max(1, recording.n_samples)
            result[name] = current
        return result
