# Desktop GUI

Install the package, then launch:

```bash
bci2000-bids-gui
```

The GUI uses Tkinter, which is included with standard Python desktop installers.
Choose one or more `.dat` files, or select a directory and enable recursive search.
Choose the BIDS output directory, enter de-identified subject/session/task labels,
select `beh`, `eeg`, or `ieeg`, and optionally select a profile. Use **Inspect**
before conversion and **Dry run** to preview the planned operation. The conversion
runs in a background thread and uses the same API, staging, checksum, and overwrite
protection as the command-line interface.

For iEEG, select the actual channel type (`ECOG`, `SEEG`, or `DBS`). ECG/EKG-named
channels are marked as `ECG` automatically.

Use **Include neural signal data** to choose between neural-plus-state conversion
and state-only conversion. State-only conversion still requires a reviewed profile
so the application knows which states are events, motion, or ignored data.

If no profile is selected, the GUI generates a review-required starter mapping and
shows a warning. This applies to both state-only and neural-plus-state conversion.
Save and review the profile before treating the output as analysis-ready.

Use `beh` only when neural export is intentionally disabled. For a recording with
neural channels plus events or motion states, select `eeg` or `ieeg`; events and
motion are exported in addition to the neural recording. Generate a starter profile
from the command line with `bci2000-bids profile recording.dat --output profile.json`,
then review it in the GUI's Profile field. If the Profile field is empty when
**Convert** is clicked, the GUI explicitly offers automatic generation, the custom
profile builder, or cancellation before any conversion starts.

The GUI's **Preserve source and checksum** option copies raw `.dat` files into the
selected dataset's `sourcedata/` directory. These files may contain identifying
metadata and should only be preserved in an access-controlled location.

On Linux distributions that split Tkinter into a separate system package, install
the distribution's Tk package once (for example `python3-tk`). Windows and macOS
Python installers normally include it.
