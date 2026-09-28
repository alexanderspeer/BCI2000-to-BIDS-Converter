from __future__ import annotations

from typing import Any


def suggest_profile(info: dict[str, Any]) -> dict[str, Any]:
    """Create a conservative, reviewable starter profile from header state names."""
    events: dict[str, dict[str, Any]] = {}
    motion: dict[str, dict[str, Any]] = {}
    ignored: list[str] = []
    for item in info.get("states", []):
        name = str(item["name"])
        lower = name.lower()
        if any(token in lower for token in ("joystickx", "joysticky", "cursorx", "cursory", "gaze", "eyetracker")):
            motion[name] = {"column": name, "type": "POSITION", "units": "n/a"}
        elif int(item.get("bit_width", 0)) <= 1 or any(token in lower for token in ("event", "marker", "stimulus", "target", "movement", "trial", "button", "presentation")):
            events[name] = {"strategy": "rising_edge" if int(item.get("bit_width", 0)) == 1 else "change", "trial_type": name}
        else:
            ignored.append(name)
    return {
        "name": "review-required-starter-profile",
        "metadata": {"tracking_system": "unknown", "review_required": True},
        "events": events,
        "motion": motion,
        "ignore": ignored,
    }
