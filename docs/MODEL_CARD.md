# BacRootFit model card

## Task and inputs

Prioritize individual bacterial protein-coding genes using the complete encoded protein sequence. Training labels describe experimental perturbation phenotypes in particular plant-associated conditions, not an intrinsic context-free function. The sequence-only model receives no host or experimental condition at inference.

## Architecture

Frozen ProtT5 encoder, exact pinned revision in each bundle; complete 1,022-residue nonoverlapping windows; amino-acid mean pooling without special tokens; per-protein L2 normalization; StandardScaler fitted on the relevant training pool; RBF-SVM with C=1 and balanced training sample weights. Gamma is 1/(feature dimension × training-feature variance), matching the registered multiplier 1. Probability fitting, PCA, encoder fine-tuning and ensembling are absent.

## Two bundles

The development bundle was fitted on 11,664 development proteins. Its fixed raw-score threshold 0.17759950571640748 came from pooled fivefold development OOF predictions. Internal test and H3 results in the paper belong to this bundle.

The deployment bundle was fitted after evaluation on all 14,505 proteins. Its raw-score threshold −0.028397905657864597 came from a separate full-database fivefold OOF pass of the already selected recipe. It is intended for subsequent application. Predictions from this full-database refit on former internal-test proteins are training-exposed and do not provide an independent test estimate.

Thresholds are stored with the corresponding scaler and weights. A score ≥ threshold is positive. Scores are uncalibrated decision values; a score of 0.8 does not mean 80% probability. Threshold values cannot be compared across bundles as probability cutoffs.

## Evaluation and limitations

Primary internal testing uses repaired homology-group separation, not complete study or strain exclusion. LOSO is a separate fixed-configuration supplementary analysis on seven dual-class studies, with held-out source/strain/group exclusions. H3 is a historically examined three-hour duckweed surface phenotype-transfer cohort, not root-specific independent prospective validation.

The class distribution is imbalanced. Interpret AP, precision and candidate enrichment alongside cohort prevalence. Class-balanced fitting does not rebalance test cohorts. Non-hit controls remain experimental-condition-specific; absence of statistical evidence is not proof of universal biological irrelevance. General growth effects and incomplete perturbation efficacy may influence source labels. The model should guide candidate prioritization and requires independent experimental assessment for a new biological context.
