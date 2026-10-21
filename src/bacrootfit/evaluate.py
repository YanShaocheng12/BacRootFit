"""Recompute metrics from ID-joined predictions at an already locked threshold."""
import argparse
from pathlib import Path
import numpy as np
from .io import table, save_json
from .metrics import evaluate, bootstrap


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--bootstrap", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20261016, help="Group-bootstrap seed (paper: 20261016)")
    parser.add_argument("--cohort-ids", type=Path, help="TSV with sample_id defining the complete expected cohort; otherwise all label IDs")
    parser.add_argument("--allow-subset", action="store_true", help="Explicitly allow missing cohort predictions and label the result as a subset")
    parser.add_argument("--groups", type=Path, help="Optional TSV with sample_id and homology_group when labels do not contain groups")
    args = parser.parse_args(argv)
    labels = table(args.labels)
    if len({row["sample_id"] for row in labels}) != len(labels):
        raise ValueError("Duplicate label identifiers")
    lookup = {row["sample_id"]: row for row in labels}
    if not lookup or "" in lookup:
        raise ValueError("Expected nonempty label identifiers")
    expected = set(lookup)
    if args.cohort_ids:
        cohort = table(args.cohort_ids)
        expected = {r["sample_id"] for r in cohort}
        if not cohort or len(expected) != len(cohort) or "" in expected:
            raise ValueError("Expected unique nonempty cohort identifiers")
        if not expected <= set(lookup):
            raise ValueError("A cohort identifier has no matching label")
    predictions = table(args.predictions)
    if not predictions or len({r["protein_id"] for r in predictions}) != len(predictions):
        raise ValueError("Expected unique nonempty prediction identifiers")
    predicted_ids = {r["protein_id"] for r in predictions}
    extra = predicted_ids - expected
    missing = expected - predicted_ids
    if extra:
        raise ValueError(f"{len(extra)} prediction IDs are outside the expected labelled cohort: {sorted(extra)[:5]}")
    if missing and not args.allow_subset:
        raise ValueError(f"Incomplete cohort: matched={len(predicted_ids)}, expected={len(expected)}, missing={len(missing)}. "
                         "Supply --cohort-ids for a predefined cohort or --allow-subset for explicit subset analysis.")
    thresholds = {float(r["threshold"]) for r in predictions}
    if len(thresholds) != 1:
        raise ValueError("One locked model threshold is required per evaluation")
    threshold = thresholds.pop()
    y = np.array([int(lookup[r["protein_id"]]["label"]) for r in predictions])
    scores = np.array([float(r["decision_score"]) for r in predictions])
    for row in predictions:
        label_hash = lookup[row["protein_id"]].get("sequence_sha256")
        if label_hash and row.get("sequence_sha256") and label_hash != row["sequence_sha256"]:
            raise ValueError("Prediction sequence hash differs from the label record")
    if any(int(r["predicted_label"]) != int(s >= threshold) for r, s in zip(predictions, scores)):
        raise ValueError("Stored classes disagree with the fixed threshold")
    result = dict(threshold=threshold, scores_are_probabilities=False, **evaluate(y, scores, threshold))
    result["coverage"] = dict(mode="subset_allowed" if args.allow_subset else "complete_required",
                              complete=not missing, expected=len(expected), matched=len(predicted_ids),
                              missing=len(missing), unexpected=0, missing_ids=sorted(missing),
                              positive=int(y.sum()), negative=int((1-y).sum()))
    if args.bootstrap < 0 or args.bootstrap == 1:
        raise ValueError("--bootstrap must be zero or at least two")
    if args.bootstrap:
        group_rows = table(args.groups) if args.groups else labels
        group_lookup = {r["sample_id"]: r for r in group_rows}
        if len(group_lookup) != len(group_rows):
            raise ValueError("Duplicate group identifiers")
        if any(not group_lookup.get(r["protein_id"], {}).get("homology_group") for r in predictions):
            raise ValueError("Group bootstrap requires homology_group for every predicted ID; supply --groups")
        groups = [group_lookup[r["protein_id"]]["homology_group"] for r in predictions]
        for row in predictions:
            group_row, label_row = group_lookup[row["protein_id"]], lookup[row["protein_id"]]
            for key in ["sequence_sha256", "label"]:
                if group_row.get(key) and label_row.get(key) and group_row[key] != label_row[key]:
                    raise ValueError(f"Group table {key} differs from label record")
        result["group_bootstrap"] = bootstrap(y, scores, groups, threshold, args.bootstrap, args.seed)
    save_json(args.out, result)
    print(result)
