from __future__ import annotations

import csv
import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from .bci2000.reader import BCI2000Recording
from .bids.dataset import initialize_dataset
from .bids.electrophysiology import channels_tsv, write_edf
from .bids.events import extract_events
from .bids.motion import motion_channels, write_motion
from .bids.naming import BIDSContext, normalize_entity, normalize_label
from .bids.participants import add_participant
from .sidecars import write_json
from .config import Profile, load_profile
from .exceptions import BIDSConversionError, OutputExistsError
from .utils.hashing import sha256

@dataclass
class ConversionReport:
    outputs: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    runs: list[int] = field(default_factory=list)


def discover_inputs(inputs: str | Path | Iterable[str | Path], recursive: bool = False) -> list[Path]:
    values = [inputs] if isinstance(inputs, (str, Path)) else list(inputs)
    files: list[Path] = []
    for value in values:
        path = Path(value).expanduser().resolve()
        if path.is_file():
            if path.suffix.lower() == ".dat":
                files.append(path)
        elif path.is_dir():
            iterator = path.rglob("*.dat") if recursive else path.glob("*.dat")
            files.extend(iterator)
        else:
            raise BIDSConversionError(f"Input does not exist: {path}")
    return sorted(set(files), key=lambda path: str(path).casefold())


def _load_config(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    source = Path(path)
    if source.suffix.lower() in {".yaml", ".yml"}:
        import yaml  # type: ignore
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
    else:
        data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise BIDSConversionError("Conversion configuration must be an object")
    return data


def _write_tsv(path: Path, columns: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def convert(inputs: str | Path | Iterable[str | Path], output: str | Path, *, subject: str | None = None,
            session: str | None = None, task: str | None = None, datatype: str | None = None,
            channel_type: str | None = None,
            export_neural: bool | None = None,
            profile: str | Path | Profile | None = None, config: str | Path | None = None,
            recursive: bool = False, preserve_source: bool = False, on_existing: str = "error",
            validate: bool = False, dry_run: bool = False,
            progress: Callable[[float, str], None] | None = None) -> ConversionReport:
    settings = _load_config(config)
    subject = subject or settings.get("subject")
    session = session or settings.get("session", "01")
    task = task or settings.get("task")
    datatype = datatype or settings.get("datatype", "beh")
    channel_type = channel_type or settings.get("channel_type")
    if export_neural is None:
        export_neural = settings.get("export_neural")
    preserve_source = preserve_source or bool(settings.get("preserve_source", False))
    on_existing = settings.get("on_existing", on_existing)
    if not subject or not task:
        raise BIDSConversionError("subject and task are required (use flags, config, or interactive CLI)")
    subject, session, task = normalize_label(str(subject), "sub"), normalize_label(str(session), "ses"), normalize_label(str(task), "task")
    if datatype not in {"beh", "eeg", "ieeg"}:
        raise BIDSConversionError("datatype must be beh, eeg, or ieeg")
    if export_neural is None:
        export_neural = datatype in {"eeg", "ieeg"}
    if export_neural and datatype == "beh":
        raise BIDSConversionError("Neural export requires datatype=eeg or datatype=ieeg")
    if on_existing not in {"error", "skip", "overwrite"}:
        raise BIDSConversionError("on_existing must be error, skip, or overwrite")
    files = discover_inputs(inputs, recursive)
    if not files:
        raise BIDSConversionError("No .dat files found")
    if len({path.name for path in files}) != len(files):
        raise BIDSConversionError("Input files have duplicate names; use unique source filenames")
    if isinstance(profile, Profile):
        routing = profile
    else:
        routing = load_profile(profile or settings.get("profile"))
    if not export_neural and not (routing.events or routing.motion or routing.event_columns):
        raise BIDSConversionError("State-only conversion requires a profile with event or motion mappings")
    if export_neural and datatype == "ieeg":
        channel_type = str(channel_type or routing.metadata.get("channel_type", ""))
        if channel_type not in {"ECOG", "SEEG", "DBS"}:
            raise BIDSConversionError("iEEG conversion requires channel_type=ECOG, SEEG, or DBS")
    tracking_system = normalize_entity(str(routing.metadata.get("tracking_system", "unknown")), "tracking_system")
    root = Path(output).expanduser().resolve()
    root.parent.mkdir(parents=True, exist_ok=True)
    destination = root / f"sub-{subject}" / f"ses-{session}"
    if destination.exists() and on_existing == "error":
        raise OutputExistsError(f"Output session already exists: {destination}. Use a new session or explicit overwrite policy.")
    if destination.exists() and on_existing == "skip":
        return ConversionReport(runs=list(range(1, len(files) + 1)))
    report = ConversionReport(runs=list(range(1, len(files) + 1)))
    if dry_run:
        return report
    stage = Path(tempfile.mkdtemp(prefix=f".{root.name}-", dir=root.parent))
    try:
        if root.exists():
            if not root.is_dir():
                raise BIDSConversionError(f"Output path is not a directory: {root}")
            shutil.copytree(root, stage, dirs_exist_ok=True)
        initialize_dataset(stage)
        add_participant(stage, subject)
        if destination.exists() and on_existing == "overwrite":
            shutil.rmtree(stage / f"sub-{subject}" / f"ses-{session}")
        (stage / f"sub-{subject}" / f"ses-{session}").mkdir(parents=True, exist_ok=True)
        published_relative: set[Path] = set()
        for run, source in enumerate(files, 1):
            if progress:
                progress((run - 1) / len(files), f"Reading run {run}/{len(files)}: {source.name}")
            context = BIDSContext(subject, session, task, run)
            output_datatype = datatype if export_neural else "beh"
            datatype_dir = stage / f"sub-{subject}" / f"ses-{session}" / output_datatype
            prefix = context.prefix
            event_dir = datatype_dir
            with BCI2000Recording(source) as recording:
                state_names = list(dict.fromkeys(list(routing.events) + list(routing.motion) + list(routing.event_columns)))
                missing = sorted(set(state_names) - set(recording.states))
                if missing:
                    raise BIDSConversionError(f"Profile states missing from {source.name}: {', '.join(missing)}")
                signal, states = recording.read_selected(
                    state_names,
                    signal=bool(export_neural),
                    progress=(lambda fraction, run=run: progress(((run - 1) + fraction * 0.75) / len(files), f"Decoding run {run}/{len(files)}") if progress else None),
                )
                if routing.events or routing.event_columns:
                    columns, rows = extract_events(states, recording.sampling_frequency, routing.events, routing.event_columns)
                    event_path = event_dir / f"{prefix}_events.tsv"
                    _write_tsv(event_path, columns, rows)
                    write_json(event_dir / f"{prefix}_events.json", {column: {"Description": "Mapped BCI2000 state"} for column in columns if column not in {"onset", "duration", "trial_type"}})
                if routing.motion:
                    motion_dir = stage / f"sub-{subject}" / f"ses-{session}" / "motion"
                    motion_path = motion_dir / f"{prefix}_tracksys-{tracking_system}_motion.tsv"
                    motion_columns, _ = write_motion(motion_path, states, routing.motion, recording.sampling_frequency)
                    motion_channels(motion_dir / f"{prefix}_tracksys-{tracking_system}_channels.tsv", motion_columns, routing.motion)
                    write_json(motion_dir / f"{prefix}_tracksys-{tracking_system}_motion.json", {"SamplingFrequency": recording.sampling_frequency, "StartTime": 0.0, "Columns": motion_columns, "TrackingSystemName": tracking_system})
                if export_neural:
                    signal_dir = datatype_dir
                    signal_path = signal_dir / f"{prefix}_{datatype}.edf"
                    write_edf(signal, signal_path, recording.sampling_frequency, recording.channel_names, recording.channel_units)
                    primary_type = channel_type if datatype == "ieeg" else "EEG"
                    channel_types = ["ECG" if name.upper().startswith(("ECG", "EKG")) else primary_type for name in recording.channel_names]
                    channels_tsv(signal_dir / f"{prefix}_channels.tsv", recording.channel_names, recording.channel_units, channel_types)
                    sidecar = {"TaskName": task, "SamplingFrequency": recording.sampling_frequency, "PowerLineFrequency": "n/a", "SoftwareFilters": "n/a", "HardwareFilters": "n/a", "SourceSystem": "BCI2000", "RecordingDuration": recording.duration, "ConversionSoftware": "bci2000-bids"}
                    sidecar["iEEGReference" if datatype == "ieeg" else "EEGReference"] = routing.metadata.get("reference", "n/a")
                    write_json(signal_dir / f"{prefix}_{datatype}.json", sidecar)
                if preserve_source:
                    preserved = preserve_source_file(source, stage, subject, session)
                    manifest = stage / "sourcedata" / f"sub-{subject}" / f"ses-{session}" / "bci2000" / "checksums.tsv"
                    if not manifest.exists():
                        _write_tsv(manifest, ["filename", "sha256"], [])
                    with manifest.open("a", encoding="utf-8", newline="") as stream:
                        csv.writer(stream, delimiter="\t", lineterminator="\n").writerow([source.name, sha256(preserved)])
            planned = list((stage / f"sub-{subject}" / f"ses-{session}").rglob("*"))
            published_relative.update(path.relative_to(stage) for path in planned if path.is_file())
            if progress:
                progress(run / len(files), f"Finished run {run}/{len(files)}")
        if validate:
            from .bids.validation import validate as validate_bids
            validate_bids(stage)
        if root.exists():
            backup = root.with_name(f".{root.name}-backup")
            if backup.exists():
                shutil.rmtree(backup)
            root.replace(backup)
            try:
                stage.replace(root)
            except Exception:
                backup.replace(root)
                raise
            shutil.rmtree(backup)
        else:
            stage.replace(root)
        report.outputs = sorted((root / relative for relative in published_relative), key=str)
        return report
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def preserve_source_file(source: Path, stage: Path, subject: str, session: str) -> Path:
    destination = stage / "sourcedata" / f"sub-{subject}" / f"ses-{session}" / "bci2000" / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination
