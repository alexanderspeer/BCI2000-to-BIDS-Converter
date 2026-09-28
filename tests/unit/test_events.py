import numpy as np

from bci2000_bids.bids.events import extract_events


def test_rising_edges_are_not_one_row_per_sample():
    columns, rows = extract_events({"Marker": np.array([0, 0, 1, 1, 0, 1])}, 10, {"Marker": {"strategy": "rising_edge", "trial_type": "start"}})
    assert columns == ["onset", "duration", "trial_type"]
    assert [row[0] for row in rows] == [0.2, 0.5]


def test_intervals_have_duration():
    _, rows = extract_events({"Moving": np.array([0, 1, 1, 0])}, 2, {"Moving": {"strategy": "interval", "trial_type": "movement"}})
    assert rows[0][:3] == [0.5, 1.0, "movement"]
