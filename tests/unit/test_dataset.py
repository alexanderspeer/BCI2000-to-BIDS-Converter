import json

from bci2000_bids.bids.dataset import initialize_dataset


def test_dataset_initialization(tmp_path):
    initialize_dataset(tmp_path)
    assert json.loads((tmp_path / "dataset_description.json").read_text())["BIDSVersion"] == "1.10.1"
    assert (tmp_path / "participants.tsv").read_text() == "participant_id\n"
