# BacRootFit model card

## Task and input

The model prioritizes bacterial protein-coding genes from their complete protein sequences. Labels describe genetic-perturbation phenotypes in source experiments. The sequence-only model receives no host or experimental-condition input.

## Model and preprocessing

Frozen ProtT5 residue means are followed by per-protein L2 normalization, a training-fitted StandardScaler and an RBF-SVM with balanced training sample weights. The selected configuration has C=1 and the registered gamma multiplier of 1. Long proteins use complete nonoverlapping 1,022-residue windows, excluding padding and special tokens. Exact encoder revisions and preprocessing settings are supplied with the bundles.

## Which model to use

| Bundle | Training pool | Use |
| --- | --- | --- |
| `models/deployment` | All 14,505 database proteins | Routine prediction of new sequences |
| `models/development` | 11,664 development proteins | Reproduce the released held-out evaluations |

Each bundle includes its own scaler and decision threshold, applied automatically. Approximate raw thresholds are −0.0284 (deployment) and 0.1776 (development); exact values remain in each `bundle.json`. Do not transfer thresholds between bundles. Scores are uncalibrated decision values, not probabilities.

## Evaluation summary

The following results use the **development** bundle at its fixed threshold. They do not describe a separate test of the full-data deployment refit.

| Cohort | Proteins | ROC-AUC | AP | MCC |
| --- | --- | --- | --- | --- |
| Internal homology-group-isolated test | 2,841 | 0.8481 | 0.4519 | 0.3968 |
| H3 duckweed surface-colonization transfer | 1,878 | 0.8577 | 0.4011 | 0.3683 |

H3 contains 86 positives and 1,792 controls from a three-hour duckweed surface assay. It is phenotype-transfer evidence, rather than a root-specific or newly blind source. Cross-study supplementary evaluation uses seven dual-class studies with source, strain and homology exclusions. Detailed metrics and uncertainty are in the results asset.

## Interpretation

Class prevalence influences precision and AP. Experimental non-hits are condition-specific controls. General growth effects and incomplete perturbation efficacy can influence source labels. Predictions prioritize candidates and require independent assessment in a new biological context.
