# Reproducibility scope

## Included materials

1. Formal FASTA, labels, qualified source observations, sequence mappings, evidence rules and homology groups.
2. Fixed development/internal-test, fivefold validation and neural-monitor partitions; full-data deployment folds.
3. All 340 candidate definitions, development rankings, OOF predictions, representative tests, baselines, intervals, split-sensitivity and LOSO summaries.
4. Separate unmodified development and deployment SVM/scaler bundles.
5. The 16,383-row raw ProtT5 mean bank: 14,505 formal proteins followed by 1,878 H3 rows, with sequence-checked index.
6. Public prediction, extraction, training, evaluation and verification commands; archived numerical routines and workflow sources.
7. `config/H3_full_groups.tsv` and `config/internal_full_groups.tsv` for the paper's uncertainty analysis, plus H3 grouping policy and checkpoint file locks.

The first six items are in the v1.0.0 assets/source release; item 7 and the additional maintenance helpers are provided in the current Git checkout. The original archives are preserved.

## Execution levels

| Analysis | Executable entry point | Extra requirements |
| --- | --- | --- |
| Cached-feature inference | `bacrootfit predict --features ...` | Installed model asset; CPU supported |
| New FASTA → ProtT5 → prediction | `bacrootfit predict --encoder-dir ...` | Pinned encoder; CUDA FP16 environment |
| Selected model's fivefold OOF and refit | `bacrootfit train --root . --out ...` | Included ProtT5 mean bank and fixed partitions |
| All 340 configurations | `bacrootfit train --all-configurations --features-dir ... --out ...` | All five mean/std/residue banks, CUDA and neural dependencies |
| Paper group-bootstrap intervals | `python scripts/reproduce_paper_intervals.py ...` | Archived fixed predictions and supplied cohort groups |

The complete five-encoder banks occupy approximately 78 GB and are separate from the lightweight release. [FEATURE_BANKS.md](FEATURE_BANKS.md) gives one concrete generation command per encoder and the required dependencies. That generation is distinct from both refitting a classifier and auditing stored results.

## Data coordinates and fitting rules

`config/plan.json` uses formal-database row coordinates for development/internal-test IDs and **cohort-local** coordinates for `H3_full`/`H3_balanced`. The combined feature bank starts H3 at row 14,505. Use ID and sequence-hash joins when selecting rows.

The SVM uses each fold's four-fold training pool. Neural candidates additionally use the saved training/monitor split for early stopping. Preprocessing and class weights come from the actual training rows for that fit. Pooled OOF threshold selection enumerates score boundaries, includes all-positive/all-negative points, assigns zero MCC to zero denominators and selects the higher threshold on an exact tie. Candidate ranking uses OOF MCC, then AUC, AP and registry order. Neural refit epochs are the ceiling of median best fold epoch. Test and H3 results do not select a configuration or threshold.

## Complete-cohort evaluation and uncertainty

By default, `bacrootfit evaluate` requires exactly the label-table IDs. Use `--cohort-ids config/internal_full_groups.tsv` to define the internal test within the larger formal label table. Missing predictions fail before metrics are saved. `--allow-subset` explicitly permits partial analysis; the output includes completeness, expected/matched/missing counts, missing IDs and class counts. Extra, duplicate, inconsistent-threshold and sequence-mismatched predictions fail.

H3 groups contain 1,878 IDs in 1,430 components. They inherit historical H3 extension components and union connected repaired parent components by sequence SHA-256, without splitting inherited components. They are used only for uncertainty, not to train or select the model. `config/H3_group_policy.json` records original source hashes and the grouping rule. Internal test has 2,841 IDs in 1,557 groups.

The paper used 5,000 accepted equal-probability multinomial draws over sorted groups, seed 20261016, at fixed predictions and thresholds, with percentile 2.5/97.5 bounds. Single-class draws are rejected. The public evaluator implements the same draw and tied-score metric rules. The helper below converts archived `sample_id` prediction headers to the public `protein_id` schema, checks complete membership and compares all nine reported metric intervals with the archived table:

```bash
python scripts/reproduce_paper_intervals.py --root . --out runs/paper_intervals --bootstrap 5000
```

This recomputes uncertainty from stored predictions. It is not a new model fit, newly independent validation, or between-study uncertainty estimate. Paired baseline differences remain archived in `results/uncertainty/paired_differences.tsv`; the single-predictor evaluation command does not recompute that paired analysis.

## Numerical portability and validation

The V27 numerical `fit26.py` and `neural26.py` are preserved. `common26.py` adapts path bindings; the wrapper supplies explicit inputs and writes new outputs separately. `provenance/public_adaptations.json` records source identities. Published partitions are distributed directly rather than silently regenerated by a different approximate homology search.

The publication checks reran the selected development and deployment recipes (five folds plus one refit each). Development OOF/internal scores differed from the originals by at most 4.44×10⁻¹⁶; the deployment threshold was identical. Cached-feature inference reproduced internal and H3 metrics. FASTA-to-score execution was checked on three existing database proteins, including a 4,538-residue example split into five windows; maximum raw-mean difference from the original FP16 cache was 6.10×10⁻⁵. These examples test execution, not biological generalization.

Tests cover threshold boundaries, input identities, checked installation and complete/subset evaluation. New bank generation follows the archived checkpoint/tokenization/precision/batching/storage recipe; `complete.json` reports comparisons with historical bank hashes. Different hardware, kernels or batching can change floating-point values. A full 340-configuration run from newly regenerated banks has not been repeated for this maintenance revision.
