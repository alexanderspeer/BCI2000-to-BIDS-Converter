"""Small desktop front end for bci2000-bids.

Tkinter is part of the Python standard library on normal desktop Python
installations, so the GUI adds no third-party runtime dependency.
"""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ModuleNotFoundError:  # pragma: no cover - depends on the host OS package
    tk = None  # type: ignore[assignment]
    filedialog = messagebox = ttk = None  # type: ignore[assignment]

from .bci2000.inspection import inspect_recording
from .config import load_profile
from .convert import convert, discover_inputs


class ConverterGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("BCI2000 to BIDS")
        root.minsize(760, 560)
        self.input_value = tk.StringVar()
        self.output_value = tk.StringVar()
        self.profile_value = tk.StringVar()
        self.subject_value = tk.StringVar()
        self.session_value = tk.StringVar(value="01")
        self.task_value = tk.StringVar()
        self.datatype_value = tk.StringVar(value="beh")
        self.channel_type_value = tk.StringVar(value="ECOG")
        self.neural_value = tk.BooleanVar(value=False)
        self.recursive_value = tk.BooleanVar()
        self.preserve_value = tk.BooleanVar()
        self.validate_value = tk.BooleanVar(value=True)
        self.dry_run_value = tk.BooleanVar()
        self.existing_value = tk.StringVar(value="error")
        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self._build()
        self.root.after(100, self._drain_messages)

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        row = 0
        ttk.Label(frame, text="Input .dat file or directory").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.input_value).grid(row=row, column=1, sticky="ew", padx=8)
        input_buttons = ttk.Frame(frame)
        input_buttons.grid(row=row, column=2)
        ttk.Button(input_buttons, text="Files", command=self._choose_files).pack(side="left")
        ttk.Button(input_buttons, text="Folder", command=self._choose_directory).pack(side="left", padx=(4, 0))
        row += 1
        ttk.Label(frame, text="BIDS output directory").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.output_value).grid(row=row, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Choose", command=self._choose_output).grid(row=row, column=2)
        row += 1
        ttk.Label(frame, text="Profile (prompted if empty)").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.profile_value).grid(row=row, column=1, sticky="ew", padx=8)
        profile_buttons = ttk.Frame(frame)
        profile_buttons.grid(row=row, column=2)
        ttk.Button(profile_buttons, text="Choose", command=self._choose_profile).pack(side="left")
        ttk.Button(profile_buttons, text="Create", command=self._create_profile).pack(side="left", padx=(4, 0))
        row += 1
        labels = [("Subject", self.subject_value), ("Session", self.session_value), ("Task", self.task_value)]
        for label, variable in labels:
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Entry(frame, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8)
            row += 1
        ttk.Checkbutton(frame, text="Include neural signal data", variable=self.neural_value).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1
        ttk.Label(frame, text="Neural datatype (if included)").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Combobox(frame, textvariable=self.datatype_value, values=("beh", "eeg", "ieeg"), state="readonly").grid(row=row, column=1, sticky="w", padx=8)
        row += 1
        ttk.Label(frame, text="iEEG channel type").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Combobox(frame, textvariable=self.channel_type_value, values=("ECOG", "SEEG", "DBS"), state="readonly").grid(row=row, column=1, sticky="w", padx=8)
        row += 1
        options = ttk.Frame(frame)
        options.grid(row=row, column=0, columnspan=3, sticky="w", pady=8)
        ttk.Checkbutton(options, text="Include nested directories", variable=self.recursive_value).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(options, text="Preserve source and checksum", variable=self.preserve_value).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(options, text="Run BIDS validation", variable=self.validate_value).pack(side="left")
        row += 1
        ttk.Label(frame, text="Existing output").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Combobox(frame, textvariable=self.existing_value, values=("error", "skip", "overwrite"), state="readonly").grid(row=row, column=1, sticky="w", padx=8)
        row += 1
        actions = ttk.Frame(frame)
        actions.grid(row=row, column=0, columnspan=3, sticky="w", pady=8)
        ttk.Button(actions, text="Inspect", command=self.inspect).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Dry run", command=lambda: self.start(True)).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Convert", command=lambda: self.start(False)).pack(side="left")
        row += 1
        self.status = tk.Text(frame, height=17, wrap="word", state="disabled")
        self.status.grid(row=row, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        frame.rowconfigure(row, weight=1)
        row += 1
        self.progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate", maximum=100)
        self.progress.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.progress_label = ttk.Label(frame, text="Ready")
        self.progress_label.grid(row=row, column=2, sticky="e", padx=(8, 0))

    def _choose_files(self) -> None:
        paths = filedialog.askopenfilenames(title="Select BCI2000 DAT files", filetypes=(("BCI2000 DAT", "*.dat"), ("All files", "*.*")))
        if paths:
            self.input_value.set(";".join(paths))

    def _choose_output(self) -> None:
        path = filedialog.askdirectory(title="Select BIDS output directory")
        if path:
            self.output_value.set(path)

    def _choose_directory(self) -> None:
        path = filedialog.askdirectory(title="Select directory containing BCI2000 DAT files")
        if path:
            self.input_value.set(path)

    def _choose_profile(self) -> None:
        path = filedialog.askopenfilename(title="Select conversion profile", filetypes=(("JSON/YAML", "*.json *.yaml *.yml"), ("All files", "*.*")))
        if path:
            self.profile_value.set(path)

    def _create_profile(self) -> None:
        try:
            files = self._inputs()
            if not files:
                raise ValueError("No .dat files found")
            ProfileBuilder(self.root, files[0], self.profile_value)
        except Exception as error:
            messagebox.showerror("Create profile", str(error))

    def _inputs(self) -> list[Path]:
        raw = self.input_value.get().strip()
        if not raw:
            raise ValueError("Choose at least one .dat file or directory")
        values = [Path(value) for value in raw.split(";")]
        return discover_inputs(values, recursive=self.recursive_value.get())

    def _write(self, text: str) -> None:
        self.status.configure(state="normal")
        self.status.insert("end", text + "\n")
        self.status.see("end")
        self.status.configure(state="disabled")

    def inspect(self) -> None:
        try:
            files = self._inputs()
            summaries = []
            for path in files:
                info = inspect_recording(path)
                summaries.append(f"{path.name}: {info['number_of_channels']} channels, {info['sampling_frequency_hz']:g} Hz, {info['duration_seconds']:.3f} s, {len(info['states'])} states")
            self._write("Found %d recording(s):" % len(files))
            for summary in summaries:
                self._write(summary)
        except Exception as error:
            messagebox.showerror("Inspection failed", str(error))

    def start(self, dry_run: bool) -> None:
        try:
            files = self._inputs()
            output = self.output_value.get().strip()
            if not output:
                raise ValueError("Choose a BIDS output directory")
            if not self.subject_value.get().strip() or not self.task_value.get().strip():
                raise ValueError("Subject and task are required")
        except Exception as error:
            messagebox.showerror("Conversion settings", str(error))
            return
        if not self.profile_value.get().strip():
            choice = messagebox.askyesnocancel(
                "Conversion profile",
                "No profile is selected.\n\n"
                "Yes: automatically analyze state values and generate a starter profile.\n"
                "No: open the custom profile builder.\n"
                "Cancel: return to the conversion form.",
            )
            if choice is None:
                return
            if choice is False:
                self._create_profile()
                return
        settings = {
            "subject": self.subject_value.get(),
            "session": self.session_value.get(),
            "task": self.task_value.get(),
            "datatype": self.datatype_value.get(),
            "channel_type": self.channel_type_value.get(),
            "export_neural": self.neural_value.get(),
            "profile": self.profile_value.get() or None,
            "preserve_source": self.preserve_value.get(),
            "on_existing": self.existing_value.get(),
            "validate": self.validate_value.get() and not dry_run,
        }
        self._write(("Dry run for " if dry_run else "Converting ") + f"{len(files)} recording(s)...")
        thread = threading.Thread(target=self._run, args=(files, output, dry_run, settings), daemon=True)
        thread.start()

    def _run(self, files: list[Path], output: str, dry_run: bool, settings: dict[str, object]) -> None:
        try:
            report = convert(files, output, subject=str(settings["subject"]), session=str(settings["session"]), task=str(settings["task"]), datatype=str(settings["datatype"]), channel_type=str(settings["channel_type"]), export_neural=bool(settings["export_neural"]), profile=settings["profile"], recursive=False, preserve_source=bool(settings["preserve_source"]), on_existing=str(settings["on_existing"]), validate=bool(settings["validate"]), dry_run=dry_run, progress=lambda fraction, message: self.messages.put(("progress", (fraction, message))))
            for warning in report.warnings:
                self.messages.put(("message", f"WARNING: {warning}"))
            self.messages.put(("message", f"Completed: {len(report.runs)} run(s). Output: {output}"))
        except Exception as error:
            self.messages.put(("message", f"ERROR: {error}"))

    def _drain_messages(self) -> None:
        while True:
            try:
                kind, value = self.messages.get_nowait()
                if kind == "progress":
                    fraction, message = value  # type: ignore[misc]
                    self.progress["value"] = float(fraction) * 100
                    self.progress_label.configure(text=f"{float(fraction) * 100:.0f}% {message}")
                else:
                    self._write(str(value))
            except queue.Empty:
                break
        self.root.after(100, self._drain_messages)


class ProfileBuilder:
    """Interactive state-routing editor backed by a BCI2000 header inspection."""

    def __init__(self, parent: tk.Misc, source: Path, output_variable: tk.StringVar) -> None:
        self.source = source
        self.output_variable = output_variable
        self.window = tk.Toplevel(parent)
        self.window.title(f"Create profile: {source.name}")
        self.window.geometry("900x650")
        self.rows: dict[str, dict[str, object]] = {}
        info = inspect_recording(source)
        self._build(info)

    def _build(self, info: dict[str, object]) -> None:
        frame = ttk.Frame(self.window, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text=("Events: discrete occurrences or meaningful state transitions. "
                              "Use rising_edge for a binary marker; do not emit one row per sample.\n"
                              "Motion: continuous position/trajectory samples with defensible units. "
                              "Ignore: internal states or states whose scientific meaning is unknown."), justify="left", wraplength=850).grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tree = ttk.Treeview(frame, columns=("bits", "route", "strategy"), show="tree headings", selectmode="browse")
        tree.heading("#0", text="BCI2000 state")
        tree.heading("bits", text="Bits")
        tree.heading("route", text="Route")
        tree.heading("strategy", text="Event strategy")
        tree.column("#0", width=330)
        tree.column("bits", width=70)
        tree.column("route", width=110)
        tree.column("strategy", width=150)
        tree.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)
        states = info.get("states", [])
        for item in states:  # type: ignore[union-attr]
            name = str(item["name"])
            bits = int(item.get("bit_width", 0))
            default = "ignore"
            self.rows[name] = {"bits": bits, "route": default, "strategy": "rising_edge" if bits == 1 else "change", "column": name, "units": "n/a", "trial_type": name}
            tree.insert("", "end", iid=name, text=name, values=(bits, default, self.rows[name]["strategy"]))
        controls = ttk.Frame(frame)
        controls.grid(row=2, column=0, columnspan=2, sticky="ew", pady=8)
        route = tk.StringVar(value="ignore")
        strategy = tk.StringVar(value="value_change")
        column = tk.StringVar()
        units = tk.StringVar(value="n/a")
        trial_type = tk.StringVar()
        ttk.Label(controls, text="Route").grid(row=0, column=0, sticky="w")
        ttk.Combobox(controls, textvariable=route, values=("ignore", "event", "motion"), state="readonly", width=12).grid(row=0, column=1, padx=5)
        ttk.Label(controls, text="Strategy").grid(row=0, column=2, sticky="w")
        ttk.Combobox(controls, textvariable=strategy, values=("rising_edge", "falling_edge", "change", "nonzero_change", "interval", "value_change"), state="readonly", width=18).grid(row=0, column=3, padx=5)
        ttk.Label(controls, text="Column").grid(row=0, column=4, sticky="w")
        ttk.Entry(controls, textvariable=column, width=18).grid(row=0, column=5, padx=5)
        ttk.Label(controls, text="Units").grid(row=0, column=6, sticky="w")
        ttk.Entry(controls, textvariable=units, width=12).grid(row=0, column=7, padx=5)
        ttk.Label(controls, text="Trial type").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(controls, textvariable=trial_type, width=18).grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=(6, 0))
        ttk.Label(controls, text="Tracking system").grid(row=1, column=3, sticky="w", pady=(6, 0))
        tracking = tk.StringVar(value="unknown")
        ttk.Entry(controls, textvariable=tracking, width=18).grid(row=1, column=4, padx=5, pady=(6, 0))

        def select(_event: object = None) -> None:
            selected = tree.selection()
            if not selected:
                return
            row = self.rows[selected[0]]
            route.set(str(row["route"])); strategy.set(str(row["strategy"])); column.set(str(row["column"]))
            units.set(str(row["units"])); trial_type.set(str(row["trial_type"]))

        def apply() -> None:
            selected = tree.selection()
            if not selected:
                return
            name = selected[0]
            row = self.rows[name]
            row.update({"route": route.get(), "strategy": strategy.get(), "column": column.get() or name, "units": units.get() or "n/a", "trial_type": trial_type.get() or name})
            tree.item(name, values=(row["bits"], row["route"], row["strategy"]))

        tree.bind("<<TreeviewSelect>>", select)
        ttk.Button(controls, text="Apply state", command=apply).grid(row=1, column=5, pady=(6, 0))
        ttk.Button(controls, text="Save profile", command=lambda: self._save(tracking.get())).grid(row=1, column=6, columnspan=2, pady=(6, 0))

    def _save(self, tracking: str) -> None:
        destination = filedialog.asksaveasfilename(parent=self.window, title="Save profile", defaultextension=".json", filetypes=(("JSON profile", "*.json"), ("All files", "*.*")))
        if not destination:
            return
        events: dict[str, dict[str, object]] = {}
        motion: dict[str, dict[str, object]] = {}
        ignored: list[str] = []
        for name, row in self.rows.items():
            route = row["route"]
            if route == "event":
                rule = {"strategy": row["strategy"], "trial_type": row["trial_type"]}
                if row["column"] != name:
                    rule["column"] = row["column"]
                events[name] = rule
            elif route == "motion":
                motion[name] = {"column": row["column"], "type": "POSITION", "units": row["units"]}
            else:
                ignored.append(name)
        profile = {"name": Path(destination).stem, "metadata": {"tracking_system": tracking or "unknown", "review_required": True}, "events": events, "motion": motion, "ignore": ignored}
        temporary = Path(destination)
        temporary.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
        load_profile(temporary)
        self.output_variable.set(str(temporary))
        self.window.destroy()


def main() -> int:
    if tk is None:
        raise RuntimeError("Tkinter is unavailable. Install your operating system's Python Tk package (for example python3-tk on Debian/Ubuntu).")
    root = tk.Tk()
    ConverterGUI(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
