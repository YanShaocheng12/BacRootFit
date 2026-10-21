# Reproducing the analyses

## Software and assets

**BacRootFit v1.0.0** includes the complete code, configuration, fixed partitions, internal/H3 bootstrap groups and executable reproduction helpers, together with downloadable data and model assets. Install all assets with `bacrootfit assets` before reproducing analyses.

| Task | Materials and requirements |
| --- | --- |
| Run a pretrained model on cached features | Included model bundles and sequence-checked example; CPU supported |
| Extract new FASTA features and predict | Pinned ProtT5 encoder and CUDA FP16 environment |
| Refit the selected ProtT5–SVM | Included raw ProtT5 means and fixed partitions; shared fit engine requires PyTorch |
| Rerun all 340 configurations / 1,700 CV fits | All five complete mean/std/residue banks and CUDA |
| Recompute held-out intervals | Stored predictions and supplied cohort groups |

## Refit the selected configuration

```bash
bacrootfit train --root . --out runs/development --dry-run
bacrootfit train --root . --out runs/development
bacrootfit train --root . --role deployment --out runs/deployment
```

Each run reconstructs pooled fivefold OOF predictions, determines the MCC-maximizing threshold and refits on its training pool. Standardization and class weights are fitted within the actual training portion. The development fit uses the fixed development pool; deployment uses all formal database proteins. Test and H3 predictions do not select a model or threshold. Separate output directories preserve the supplied bundles.

## Reproduce the full comparison

The lightweight feature asset includes ProtT5 means, not the approximately 78-GB collection of all five native banks. Follow [FEATURE_BANKS.md](FEATURE_BANKS.md) for per-encoder commands and checkpoint locks, then:

```bash
bacrootfit train --root . --features-dir full_banks --all-configurations --out runs/search340 --dry-run
bacrootfit train --root . --features-dir full_banks --all-configurations --out runs/search340
```

Stored rankings allow auditing but do not replace a new search. A complete run from newly regenerated banks has not been repeated for this software update. Native precision and hardware/kernel differences can affect numerical identity; retain generated bank manifests with new results.

## Partitions and selection rules

All configurations share fixed homology-group partitions. Connected groups use identity ≥30%, bidirectional coverage ≥80% and E-value ≤0.001, retaining historical bridge relationships and subsequently verified links. Split-specific audits found no detected qualifying cross-side hits in the released partitions; the heuristic search is not an exhaustive proof. A previous graph revision expanded the internal test from 2,822 to 2,841 proteins and regenerated development folds before the registered search was rerun. [Grouping history](GROUPING_HISTORY.md) preserves that effect on the analysis.

The SVM uses each fold's four-fold training pool. Neural candidates use the saved actual-training/monitor subdivision. OOF threshold selection pools validation predictions, enumerates effective score boundaries, includes all-positive/all-negative points and resolves exact MCC ties with the higher threshold. Candidates rank by MCC, AUC, AP and registry order. Neural refit epochs are the ceiling of median best fold epoch.

Formal database indices and H3 cohort indices have different coordinate systems in `config/plan.json`. H3 starts at row 14,505 in the combined bank. Join IDs and sequence hashes rather than assuming all plan indices are global.

## Evaluation and verification

See [EVALUATION.md](EVALUATION.md) for complete-cohort evaluation, explicit subset analysis and the group-bootstrap command. [Validation records](VALIDATION.md) describe numerical and software checks. The technical source mapping is retained in `provenance/public_adaptations.json`; user-facing commands do not require internal workflow names.
