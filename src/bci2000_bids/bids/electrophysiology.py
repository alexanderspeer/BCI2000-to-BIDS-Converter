from __future__ import annotations

import math
import os
import warnings
from pathlib import Path
import numpy as np

_RECORD_DURATIONS = (1.0, 0.5, 0.25, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001)
_RECORD_BYTES_LIMIT = 61_440


def _edf_bound(value: float, side: str) -> float:
    if not math.isfinite(value):
        raise ValueError("EDF physical bounds must be finite")
    for decimals in range(6, -1, -1):
        scale = 10 ** decimals
        rounded = (math.floor(value * scale) if side == "min" else math.ceil(value * scale)) / scale
        if len(str(float(rounded))) <= 8:
            return float(rounded)
    rounded = math.floor(value) if side == "min" else math.ceil(value)
    if len(str(float(rounded))) > 8:
        raise ValueError(f"Signal range cannot be represented safely in EDF: {value}")
    return float(rounded)


def _record_duration(n_samples: int, fs: float, n_channels: int) -> tuple[float, int]:
    for duration in _RECORD_DURATIONS:
        samples = round(fs * duration)
        if (samples > 0 and math.isclose(fs * duration, samples, abs_tol=1e-9)
                and n_samples % samples == 0
                and samples * n_channels * 2 <= _RECORD_BYTES_LIMIT):
            return duration, samples
    raise ValueError("No EDF record duration preserves the source sample count and sampling frequency")


def write_edf(signal: np.ndarray, path: Path, fs: float, labels: list[str], units: list[str]) -> None:
    try:
        import pyedflib
    except ImportError as error:
        raise RuntimeError("EDF export requires pyEDFlib") from error
    if signal.ndim != 2 or signal.shape[1] != len(labels):
        raise ValueError("Signal shape and channel labels do not match")
    if len(set(labels)) != len(labels) or any(not label or len(label) > 16 or any(ord(char) > 127 for char in label) for label in labels):
        raise ValueError("EDF channel labels must be unique, non-empty, ASCII, and at most 16 characters")
    if len(units) != len(labels) or any(not unit or len(unit) > 8 or any(ord(char) > 127 for char in unit) for unit in units):
        raise ValueError("EDF units must be present, ASCII, and at most 8 characters")
    headers = []
    for index, label in enumerate(labels):
        values = np.asarray(signal[:, index], dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Neural signal contains NaN or infinity")
        low, high = float(values.min()), float(values.max())
        if low == high:
            low, high = low - 1, high + 1
        low, high = _edf_bound(low, "min"), _edf_bound(high, "max")
        headers.append({"label": label, "dimension": units[index], "sample_frequency": fs,
                       "physical_min": low, "physical_max": high, "digital_min": -32768, "digital_max": 32767,
                       "transducer": "", "prefilter": ""})
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    record_duration, _ = _record_duration(signal.shape[0], fs, len(labels))
    writer = pyedflib.EdfWriter(str(temporary), len(labels), file_type=pyedflib.FILETYPE_EDFPLUS)
    try:
        writer.setSignalHeaders(headers)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"Forcing a specific record_duration.*", category=UserWarning)
            if record_duration != 1.0:
                writer.setDatarecordDuration(record_duration)
            writer.writeSamples(signal.T)
    finally:
        writer.close()
    os.replace(temporary, path)


def channels_tsv(path: Path, labels: list[str], units: list[str], channel_type: str | list[str] = "MISC") -> None:
    import csv
    types = [channel_type] * len(labels) if isinstance(channel_type, str) else channel_type
    if len(types) != len(labels):
        raise ValueError("Channel type count does not match channel count")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["name", "type", "units"])
        writer.writerows([[label, channel_type, unit] for label, channel_type, unit in zip(labels, types, units)])
