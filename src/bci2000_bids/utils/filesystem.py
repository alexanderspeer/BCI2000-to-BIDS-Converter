from pathlib import Path
import shutil


def preserve_source(source: Path, root: Path, subject: str, session: str) -> Path:
    destination = root / "sourcedata" / f"sub-{subject}" / f"ses-{session}" / "bci2000" / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copy2(source, destination)
    return destination
