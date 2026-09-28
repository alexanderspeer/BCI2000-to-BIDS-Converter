import numpy as np
import importlib

from bci2000_bids.config import Profile
from bci2000_bids.convert import convert


class FakeRecording:
    n_samples = 4
    sampling_frequency = 2.0
    duration = 2.0
    channel_names = []
    channel_units = []

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    @property
    def states(self):
        return ["Marker"]

    def read_selected(self, names, signal=False, progress=None):
        if progress:
            progress(1.0)
        return None, {"Marker": np.array([0, 1, 1, 0])}


def test_behavior_only_conversion_is_staged(monkeypatch, tmp_path):
    source = tmp_path / "recording.dat"
    source.write_bytes(b"synthetic")
    converter_module = importlib.import_module("bci2000_bids.convert")
    monkeypatch.setattr(converter_module, "BCI2000Recording", FakeRecording)
    convert(source, tmp_path / "dataset", subject="001", session="01", task="test", datatype="beh",
            profile=Profile(events={"Marker": {"strategy": "rising_edge", "trial_type": "marker"}}))
    output = tmp_path / "dataset/sub-001/ses-01/beh/sub-001_ses-01_task-test_run-01_events.tsv"
    assert output.read_text() == "onset\tduration\ttrial_type\n0.5\t0.0\tmarker\n"
