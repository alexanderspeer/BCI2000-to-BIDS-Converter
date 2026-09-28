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


def test_neural_conversion_defaults_missing_units_to_microvolts(monkeypatch, tmp_path):
    class NeuralRecording(FakeRecording):
        n_channels = 1
        channel_names = ["AL1"]
        channel_units = ["n/a"]

        def read_selected(self, names, signal=False, progress=None):
            return np.array([[1.25], [-2.5], [3.75], [0.0]]), {}

    source = tmp_path / "recording.dat"
    source.write_bytes(b"synthetic")
    converter_module = importlib.import_module("bci2000_bids.convert")
    monkeypatch.setattr(converter_module, "BCI2000Recording", NeuralRecording)
    convert(source, tmp_path / "dataset", subject="001", session="01", task="test",
            datatype="ieeg", channel_type="SEEG", profile=Profile())
    channels = tmp_path / "dataset/sub-001/ses-01/ieeg/sub-001_ses-01_task-test_run-01_channels.tsv"
    assert channels.read_text() == "name\ttype\tunits\nAL1\tSEEG\tuV\n"

    import pyedflib
    edf = tmp_path / "dataset/sub-001/ses-01/ieeg/sub-001_ses-01_task-test_run-01_ieeg.edf"
    reader = pyedflib.EdfReader(str(edf))
    try:
        assert reader.getPhysicalDimension(0) == "uV"
        np.testing.assert_allclose(reader.readSignal(0), [1.25, -2.5, 3.75, 0.0], atol=0.01)
    finally:
        reader.close()
