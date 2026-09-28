from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Callable, Iterator

from ..exceptions import BCI2000ReadError

def _frequency(stream: Any) -> float:
    raw = str(getattr(stream, "paramdefs", {}).get("SamplingRate", {}).get("valstr", ""))
    match = re.fullmatch(r"([\d.eE+\-]+)\s*([kKmM]?)(?:[hH][zZ])?", raw.strip())
    if match:
        value = float(match.group(1)) * {"": 1, "k": 1e3, "m": 1e6}[match.group(2).lower()]
        if math.isfinite(value) and value > 0:
            return value
    value = float(stream.samplingfreq_hz)
    if not math.isfinite(value) or value <= 0:
        raise BCI2000ReadError(f"Invalid sampling frequency: {value}")
    return value


class BCI2000Recording:
    """Lazy wrapper around BCI2000Tools.

    Opening a recording reads the header only. Signal/state arrays are decoded only
    when requested, and ``iter_chunks`` permits bounded-memory processing.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        if not self.path.is_file() or self.path.suffix.lower() != ".dat":
            raise BCI2000ReadError(f"Expected an existing .dat file: {self.path}")
        try:
            from BCI2000Tools.FileReader import bcistream  # type: ignore
            self._stream = bcistream(str(self.path))
        except Exception as error:
            raise BCI2000ReadError(f"Cannot open BCI2000 file {self.path}: {error}") from error
        self.parameters = dict(getattr(self._stream, "params", {}))
        self.state_definitions = dict(getattr(self._stream, "statedefs", {}))
        self.sampling_frequency = _frequency(self._stream)
        self.n_samples = int(self._stream.samples())
        self.n_channels = int(self._stream.nchan)
        self.channel_names = self._parameter_values("ChannelNames")
        if len(self.channel_names) != self.n_channels:
            self.channel_names = [f"ch{index + 1:03d}" for index in range(self.n_channels)]
        self.channel_units = self._parameter_values("SourceChUnits")
        if len(self.channel_units) == 1:
            self.channel_units *= self.n_channels
        if len(self.channel_units) != self.n_channels:
            self.channel_units = ["n/a"] * self.n_channels

    def _parameter_values(self, name: str) -> list[str]:
        value = self.parameters.get(name, [])
        if isinstance(value, (str, bytes)):
            value = [value]
        try:
            return [str(item).strip() for item in value]
        except TypeError:
            return [str(value).strip()]

    @property
    def states(self) -> list[str]:
        return sorted(self.state_definitions)

    @property
    def duration(self) -> float:
        return self.n_samples / self.sampling_frequency

    def decode(self, names: list[str] | None = None, *, signal: bool = False, chunk_size: int = 50_000) -> tuple[Any, dict[str, Any]]:
        names = self.states if names is None else names
        try:
            self._stream.rewind()
            return self._stream.decode(nsamp=self.n_samples, states=names, apply_gains=signal)
        except Exception as error:
            raise BCI2000ReadError(f"Cannot decode {self.path}: {error}") from error

    def read_selected(self, names: list[str], *, signal: bool = False, chunk_size: int = 50_000, progress: Callable[[float], None] | None = None) -> tuple[Any, dict[str, Any]]:
        """Decode selected data in bounded chunks, retaining only requested arrays."""
        import numpy as np
        signals: list[Any] = []
        values: dict[str, list[Any]] = {name: [] for name in names}
        for chunk_number, (chunk_signal, chunk_states) in enumerate(self.iter_chunks(names, signal=signal, chunk_size=chunk_size), 1):
            if signal:
                signals.append(chunk_signal)
            for name in names:
                values[name].append(np.asarray(chunk_states[name]).reshape(-1))
            if progress:
                progress(min(1.0, chunk_number * chunk_size / max(1, self.n_samples)))
        neural = None
        if signal:
            # BCI2000Tools returns channels x samples; writers use samples x channels.
            neural = np.concatenate(signals, axis=1).T
        return neural, {name: np.concatenate(parts) for name, parts in values.items()}

    def iter_chunks(self, names: list[str] | None = None, *, signal: bool = False, chunk_size: int = 50_000) -> Iterator[tuple[Any, dict[str, Any]]]:
        names = self.states if names is None else names
        try:
            self._stream.rewind()
            remaining = self.n_samples
            while remaining:
                count = min(chunk_size, remaining)
                yield self._stream.decode(nsamp=count, states=names, apply_gains=signal)
                remaining -= count
        except Exception as error:
            raise BCI2000ReadError(f"Cannot decode chunks from {self.path}: {error}") from error

    def close(self) -> None:
        close = getattr(self._stream, "close", None)
        if close:
            close()

    def __enter__(self) -> "BCI2000Recording":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
