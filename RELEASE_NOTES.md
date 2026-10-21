# Post-release maintenance (main, 2026-10-21)

- Synchronize public availability metadata and verified direct download URLs.
- Replace preparation/handoff wording with public installation and reproduction instructions.
- Require complete evaluation cohorts by default; allow explicit subset analyses with coverage counts.
- Supply the original internal/H3 bootstrap groups, paper-compatible resampling and interval reproduction helper.
- Add per-encoder full-bank generation commands, content locks and explicit reproduction limits.
- Present formal release terminology and readable source locators in the database browser.

Paper data, model weights, partitions, labels and the original v1.0.0 ZIP assets are unchanged. Use the current Git checkout for these maintenance additions; the original v1.0.0 source snapshot preserves its original interface.

# BacRootFit v1.0.0

Manuscript-aligned resource: 14,505 complete proteins, experimental labels and evidence tracking, fixed homology partitions, 340-configuration development results and separate development/deployment SVM bundles. Public CLI supports checked raw-feature inference, pinned ProtT5 FASTA extraction, fixed-fold training, locked-threshold evaluation and data integrity verification.

The data archive includes the historical H3 duckweed surface-colonization transfer cohort separately from formal training data. No post-manuscript candidate source was added to the training database. The lightweight feature archive supplies raw ProtT5 means sufficient for reproducing the selected model; the full five-encoder residue collection remains a separate large-data requirement.

Archive identities and version-specific hashes are listed in release_manifest.json. Code is MIT; original curation contributions are CC BY 4.0; upstream terms remain applicable.
