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

The GUI's **Preserve source and checksum** option copies raw `.dat` files into the
selected dataset's `sourcedata/` directory. These files may contain identifying
metadata and should only be preserved in an access-controlled location.

On Linux distributions that split Tkinter into a separate system package, install
the distribution's Tk package once (for example `python3-tk`). Windows and macOS
Python installers normally include it.
