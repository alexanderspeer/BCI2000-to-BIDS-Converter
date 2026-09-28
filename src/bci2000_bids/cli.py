from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .bci2000.inspection import inspect_recording
from .bids.validation import validate
from .convert import convert
from .logging import configure
from .profiles.generate import suggest_profile
from .utils.prompts import ask


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bci2000-bids")
    parser.add_argument("--debug", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("file", type=Path)
    convert_parser = commands.add_parser("convert")
    convert_parser.add_argument("input", nargs="+", type=Path)
    convert_parser.add_argument("--output", required=True, type=Path)
    convert_parser.add_argument("--subject")
    convert_parser.add_argument("--session", default="01")
    convert_parser.add_argument("--task")
    convert_parser.add_argument("--datatype", choices=["beh", "eeg", "ieeg"])
    convert_parser.add_argument("--channel-type", choices=["ECOG", "SEEG", "DBS"], help="Required for iEEG output")
    neural = convert_parser.add_mutually_exclusive_group()
    neural.add_argument("--include-neural", dest="export_neural", action="store_true", help="Export neural signal data")
    neural.add_argument("--no-neural", dest="export_neural", action="store_false", help="Export only configured states/events/motion")
    convert_parser.set_defaults(export_neural=None)
    convert_parser.add_argument("--profile", type=Path)
    convert_parser.add_argument("--config", type=Path)
    convert_parser.add_argument("--recursive", action="store_true")
    convert_parser.add_argument("--preserve-source", action="store_true")
    convert_parser.add_argument("--on-existing", choices=["error", "skip", "overwrite"], default="error")
    convert_parser.add_argument("--validate", action="store_true")
    convert_parser.add_argument("--dry-run", action="store_true")
    profile = commands.add_parser("profile")
    profile.add_argument("file", type=Path)
    profile.add_argument("--output", type=Path)
    valid = commands.add_parser("validate")
    valid.add_argument("output", type=Path)
    commands.add_parser("gui")
    args = parser.parse_args(argv)
    configure("DEBUG" if args.debug else "INFO")
    try:
        if args.command == "inspect":
            print(json.dumps(inspect_recording(args.file), indent=2))
        elif args.command == "profile":
            info = inspect_recording(args.file)
            profile = suggest_profile(info)
            profile["name"] = args.file.stem + "-starter"
            text = json.dumps(profile, indent=2) + "\n"
            if args.output:
                args.output.write_text(text, encoding="utf-8")
            else:
                print(text, end="")
        elif args.command == "validate":
            print(validate(args.output))
        elif args.command == "gui":
            from .gui import main as gui_main
            return gui_main()
        else:
            if not args.subject and not sys.stdin.isatty():
                raise ValueError("subject is required in non-interactive mode")
            if not args.task and not sys.stdin.isatty():
                raise ValueError("task is required in non-interactive mode")
            if not args.subject:
                args.subject = ask("Subject label")
            if not args.task:
                args.task = ask("Task label")
            if not args.datatype:
                if args.subject and args.task:
                    args.datatype = "beh"
                elif sys.stdin.isatty():
                    args.datatype = ask("Recording type: beh, eeg, or ieeg", "beh")
                else:
                    raise ValueError("datatype is required in non-interactive mode; choose beh, eeg, or ieeg")
            report = convert(args.input, args.output, subject=args.subject, session=args.session, task=args.task, datatype=args.datatype, channel_type=args.channel_type, export_neural=args.export_neural, profile=args.profile, config=args.config, recursive=args.recursive, preserve_source=args.preserve_source, on_existing=args.on_existing, validate=args.validate, dry_run=args.dry_run)
            print(f"Planned/converted {len(report.runs)} run(s).")
        return 0
    except Exception as error:
        print(f"ERROR: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
