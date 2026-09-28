# Developer Guide

The reader is responsible for BCI2000 quirks. Profile validation is separate from
state transforms. BIDS writers accept arrays or mappings and should remain pure
where possible. `convert.py` is the orchestration layer and uses a temporary stage
before installing a run.
