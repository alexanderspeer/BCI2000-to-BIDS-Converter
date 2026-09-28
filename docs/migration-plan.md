# Migration Plan

The original checkout combined a private BIDS dataset, clinical metadata, notebooks,
and scripts. The publishable project was first isolated in `open_source/` and is now
the repository root.

1. Preserve the existing BCI2000 decoding, state-transition, EDF, checksum, and
   staging ideas, but remove project-root constants and study-specific routing.
2. Wrap `BCI2000Tools.FileReader.bcistream` behind a lazy `BCI2000Recording` API.
3. Move state routing into validated JSON/YAML profiles and expose pure event and
   motion writers.
4. Add a plan-driven library API and CLI with safe default no-overwrite behavior.
5. Test transformations with synthetic arrays and keep binary BCI2000 fixtures
   optional so CI never depends on research data.
6. Publish only this directory as a new repository; do not publish the parent
   directory or its existing history.

The legacy scripts remain available in the private checkout for comparison and are
not imported by the new package.

The neighboring MATLAB project was audited separately. Its declarative profile
model, explicit BIDS context, run-length event intervals, independent EDF writer,
and preview-oriented GUI informed this implementation. No MATLAB source was copied;
the neighboring project is MIT licensed but its MATLAB/MEX runtime is deliberately
not a dependency of the Python application.
