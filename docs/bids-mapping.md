# BIDS Mapping

Discrete state transitions become `*_events.tsv`; state intervals can include a
duration. Motion is headerless and its column order is declared by the matching
channels file. Neural output is EDF plus a channels file and sidecar. Behavior-only
recordings use `beh/` and do not receive an artificial neural file.
