# bci2000-bids

`bci2000-bids` converts BCI2000 `.dat` recordings into a BIDS dataset. It can
export neural signals as EDF, discrete state transitions as events, and explicitly
configured continuous states as BIDS Motion data. The package does not infer
participant identity, clinical information, or the scientific meaning of arbitrary
custom states.

## Installation

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[yaml,bci2000]"
```

Alternatively, install the runtime dependencies directly with
`pip install -r requirements.txt` and then install the package with
`pip install -e .`.

`BCI2000Tools` is an optional backend because users who only inspect profiles or
run unit tests do not need it. It is used as the reader rather than vendored into
this project.

## Quick start

```bash
bci2000-bids inspect recording.dat
bci2000-bids convert recording.dat --output ./bids --subject 001 --session 01 --task motor --datatype beh
bci2000-bids validate ./bids
```

For desktop use, launch `bci2000-bids-gui`. It uses Tkinter from the standard
Python installation, provides file/output/profile pickers, previews recordings,
supports dry runs, and runs conversion in the background so the window remains
responsive. No MATLAB installation or manual `PYTHONPATH` setup is required.

For a directory, use `--recursive` when nested files should be included. Multiple
files are sorted by normalized path and become `run-01`, `run-02`, and so on.

## Profiles and reproducibility

State semantics belong in a profile, not Python source. An example is in
`examples/configs/generic-motion.yaml`. Use `--profile` or save all conversion
settings in a config file:

```bash
bci2000-bids convert incoming/ --recursive --output bids/ --config study.yaml
```

The default existing-output policy is `error`; `skip` and `overwrite` are explicit
alternatives. `--dry-run` discovers and numbers files without writing recordings.
`--preserve-source` copies inputs to `sourcedata/` and records SHA-256 checksums.
Preserved source files are raw recordings and may contain identifying metadata; use
that option only in an access-controlled dataset. Dry-run does not decode recordings
or prove that the destination is writable.

Behavior-only recordings write events under `beh/` and never create a fake EDF.
Select `--datatype eeg` or `--datatype ieeg` only when the researcher has confirmed
the modality. iEEG conversion also requires `--channel-type ECOG`, `SEEG`, or `DBS`
unless that value is supplied by the profile/configuration. Automatic state
suggestions are not scientific decisions.

To export only configured states/events/motion without neural data, use
`--no-neural` with a reviewed profile. The GUI exposes the same choice as
**Include neural signal data**.

If conversion is selected without a profile, the converter creates a conservative
starter mapping automatically and reports a warning. This adds suggested events and
motion alongside neural output when neural export is enabled. Review and save that
mapping with the `profile` command before using the conversion for analysis.
The GUI asks whether to generate that starter profile or open the custom profile
builder before conversion begins.

Generate a reviewed starter profile for an unfamiliar recording with:

```bash
bci2000-bids profile recording.dat --output recording-profile.json
```

Open the generated file and confirm every event and motion mapping before using it.
The generator marks the profile `review_required: true` and uses only conservative
name/bit-width suggestions.

## Python API

```python
from bci2000_bids import convert

convert(["run01.dat", "run02.dat"], "dataset", subject="001", session="01",
        task="motor", datatype="ieeg", profile="profile.yaml")
```

## Limitations

The initial release supports BCI2000 state/signal data and EDF output. It does not
convert imaging, video, NeuroOmega, or clinical metadata. BCI2000Tools must be able
to open the source file, and EDF export requires pyEDFlib. Motion is only emitted
when the profile supplies defensible units and semantics.

The `--validate` option runs the external `bids-validator` when it is installed. If
it is unavailable, the command reports that external validation was not run rather
than claiming a validator pass.

The public project contains synthetic tests only. Keep any linkage table, names,
consent records, and private source recordings outside this repository.
