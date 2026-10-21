# Evaluation and uncertainty

Evaluation uses a stored model threshold; it never optimizes a threshold on test labels.

## Complete internal test

For a prediction file produced by the public predictor:

```bash
bacrootfit evaluate --labels data/samples.tsv --cohort-ids config/internal_full_groups.tsv --predictions internal_predictions.tsv --out internal_metrics.json --bootstrap 5000 --seed 20261016
```

## Complete H3 transfer cohort

```bash
bacrootfit evaluate --labels external/H3/samples.tsv --predictions H3_predictions.tsv --groups config/H3_full_groups.tsv --out H3_metrics.json --bootstrap 5000 --seed 20261016
```

Prediction IDs must equal the expected cohort. Without `--cohort-ids`, the complete label table defines that cohort. Missing, duplicate, unexpected and sequence-mismatched IDs are checked. Output includes expected/matched/missing counts, missing IDs, class counts and completeness. Partial analysis requires `--allow-subset` and is explicitly marked.

## Recompute released intervals

After installing the results asset:

```bash
python scripts/reproduce_intervals.py --root . --out runs/intervals --bootstrap 5000
```

The helper converts the archived prediction headers, checks complete cohort membership and compares recomputed bounds against `results/uncertainty/primary_CI.tsv`. It uses the original 5,000 accepted multinomial group draws, seed 20261016 and percentile 95% intervals. It does not refit a model or adjust a threshold.

H3 has 1,878 records in 1,430 bootstrap groups. Internal test has 2,841 records in 1,557 groups. Supplied group tables include IDs, sequence hashes and labels; `config/H3_group_policy.json` records their provenance. Paired comparisons remain in `results/uncertainty/paired_differences.tsv` and are distinct from single-model intervals.
