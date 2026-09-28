from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
