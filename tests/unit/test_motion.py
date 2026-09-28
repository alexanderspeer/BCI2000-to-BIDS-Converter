import csv

import numpy as np

from bci2000_bids.bids.motion import motion_channels, write_motion


def test_motion_is_headerless_and_channels_define_order(tmp_path):
    states = {"X": np.array([1, 2]), "Y": np.array([3, 4])}
    rules = {"X": {"column": "x", "units": "arbitrary"}, "Y": {"column": "y", "units": "arbitrary"}}
    columns, count = write_motion(tmp_path / "run_motion.tsv", states, rules, 10)
    assert columns == ["x", "y"] and count == 2
    assert (tmp_path / "run_motion.tsv").read_text() == "1\t3\n2\t4\n"
    motion_channels(tmp_path / "run_channels.tsv", columns, rules)
    assert next(csv.reader((tmp_path / "run_channels.tsv").open(), delimiter="\t"))[0] == "name"
