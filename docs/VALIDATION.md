# Software validation records

Validation records describe what was executed; they are not additional biological test cohorts.

- Selected development and full-data recipes were each refitted through five folds plus one refit. Development OOF/internal scores differed from the stored scores by at most 4.44×10⁻¹⁶; the deployment threshold matched.
- Cached-feature prediction reproduced released internal and H3 point metrics.
- Internal and H3 group-bootstrap intervals were each recomputed with 5,000 accepted draws and matched all nine archived metric intervals exactly.
- All five native encoder entry points were checked on three existing software-example proteins, including a 4,538-residue protein. Differences against the corresponding original means/stds were within the recorded native-precision tolerances; detailed values are in `provenance/maintenance_validation_20261021.json`.
- Tests cover tied-score threshold boundaries, FASTA identity, checked asset installation and complete/subset evaluation.

The full 340-configuration comparison was not retrained for this software release. Large feature banks and checkpoints remain separately obtained prerequisites. Source and environment identities are retained for reproducibility.
