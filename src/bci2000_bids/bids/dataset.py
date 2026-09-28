from __future__ import annotations

import csv
import json
from pathlib import Path


def initialize_dataset(root: Path, name: str = "BCI2000 BIDS dataset") -> None:
    root.mkdir(parents=True, exist_ok=True)
    description = root / "dataset_description.json"
    if not description.exists():
        description.write_text(json.dumps({"Name": name, "BIDSVersion": "1.10.1", "DatasetType": "raw", "GeneratedBy": [{"Name": "bci2000-bids", "Version": "0.1.0"}]}, indent=2) + "\n", encoding="utf-8")
    participants = root / "participants.tsv"
    if not participants.exists():
        with participants.open("w", encoding="utf-8", newline="") as stream:
            csv.writer(stream, delimiter="\t", lineterminator="\n").writerow(["participant_id"])
        (root / "participants.json").write_text("{}\n", encoding="utf-8")
