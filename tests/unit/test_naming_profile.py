import json

import pytest

from bci2000_bids.bids.naming import BIDSContext, normalize_label
from bci2000_bids.config import load_profile
from bci2000_bids.exceptions import ProfileValidationError


def test_labels_and_prefix():
    assert normalize_label("sub-001", "sub") == "001"
    assert BIDSContext("001", "01", "task", 2).prefix.endswith("run-02")


def test_profile_rejects_duplicate_route(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"events": {"X": {}}, "ignore": ["X"]}))
    with pytest.raises(ProfileValidationError):
        load_profile(path)
