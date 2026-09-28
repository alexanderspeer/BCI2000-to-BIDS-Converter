from pathlib import Path


def add_participant(root: Path, subject: str) -> None:
    path = root / "participants.tsv"
    text = path.read_text(encoding="utf-8")
    participant = f"sub-{subject}"
    if participant not in {line.split("\t", 1)[0] for line in text.splitlines()[1:]}:
        with path.open("a", encoding="utf-8") as stream:
            stream.write(participant + "\n")
