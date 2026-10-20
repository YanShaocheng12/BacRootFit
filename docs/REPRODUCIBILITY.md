# Reproducibility scope

## Included in the release

1. Formal FASTA, labels, source observation tables, mapping/evidence records and repaired group assignments.
2. Original development/test/fivefold/monitor IDs and full-database deployment folds.
3. All 340 configuration definitions and stored development rankings, representative test predictions, OOF records, baselines, uncertainty, split sensitivity and LOSO summaries.
4. Separate unmodified development and deployment SVM/scaler bundles.
5. The 16,383-row raw ProtT5 mean bank (14,505 formal proteins followed by 1,878 H3 rows), with sequence-checked feature index.
6. Public inference, feature extraction, training, evaluation and verification entry points, plus the original V27 numerical fit routines and original archival scripts.

`config/plan.json` uses formal-database row coordinates for development/internal-test IDs and **cohort-local** row coordinates for `H3_full`/`H3_balanced`. In the combined feature bank, H3 rows start at 14,505; add that offset only when indexing the combined array. Join labels and predictions by ID and sequence hash rather than assuming every plan field uses global feature-row coordinates. H3 labels do not include homology groups; supply a verified group table via `evaluate --groups` for new group-bootstrap runs, or use the archived paper confidence intervals.

The trained SVM recipe uses four of the five fold partitions as the actual training pool, with no neural early-stopping monitor. Neural candidates use the saved actual-training/monitor division inside that pool. Preprocessing and class weights are derived from the actual training rows for that fit. OOF threshold selection concatenates all development validation predictions; it does not average fold-wise thresholds or study-wise MCC.

The threshold search enumerates score boundaries, includes all-negative and all-positive points, assigns MCC=0 to zero denominators and chooses the highest threshold on an exact MCC tie. Configuration ranking uses pooled OOF MCC, then AUC, AP and original registry order. Neural refits use the ceiling of median best epoch across folds. Tests never select a configuration or threshold.

## Portability changes

`src/bacrootfit/research_engine/fit26.py` and `neural26.py` preserve the numerical V27 source. Only the location bindings in `common26.py` are adapted to explicit environment inputs; the command wrapper supplies those inputs, installs the frozen split/configuration files and writes new outputs separately. The new orchestration is sequential to avoid hardware-specific scheduling assumptions. `provenance/public_adaptations.json` records original file hashes.

The public predictor changes the original `main` signature solely to accept CLI argument routing. The original inference source is retained for comparison. Encoder numerical settings, raw-mean identity checking, normalization, stored scaler and fixed threshold are preserved.

## Full comparison prerequisites

The main download provides raw ProtT5 means for the selected model. It does not contain all five large pretrained encoders or approximately 78 GB of native residue/mean/std arrays. The complete 340-configuration search requires those five arrays reconstructed to the recorded recipes or distributed as separate large data assets. `config/feature_banks/` lists exact original array hashes, dimensions, native precision and mean/std recipes; `research_archive/original_v27/` and `research_archive/original_workspace/` preserve the original full workflow and its upstream source dependencies. The results asset also includes `results/graph/parent_scaffold_NOT_TRAINING.faa` for the historical bridge-aware homology scaffold. Those parent sequences are not extra labelled training proteins. Do not claim that installing the small package alone reproduces the entire 1,700-fit experiment from fresh FASTA.

`bacrootfit train --all-configurations --features-dir ... --dry-run` checks required array hashes, partitions and the 1,700-fit plan before fitting. The package currently extracts the final ProtT5 mean recipe; other encoder/residue-bank regeneration still relies on the archived research implementation and its documented upstream dependencies. Fixed published partitions are distributed instead of rerunning an approximate similarity search to silently create new splits.

## Validation records

The local publication handoff contains `validation/` with executed verification, CPU cached-feature inference, isolated FASTA-to-score checks where available, a rerun of the selected development configuration and tests. The final handoff report states which checks actually passed. None of these packaging checks reranks all 340 candidates or changes the released paper model/data.
