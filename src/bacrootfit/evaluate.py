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
    parser.add_argument("--groups", type=Path, help="Optional TSV with sample_id and homology_group when labels do not contain groups")
    args = parser.parse_args(argv)
    labels = table(args.labels)
    if len({row["sample_id"] for row in labels}) != len(labels):
        raise ValueError("Duplicate label identifiers")
    lookup = {row["sample_id"]: row for row in labels}
    predictions = table(args.predictions)
    if not predictions or len({r["protein_id"] for r in predictions}) != len(predictions):
        raise ValueError("Expected unique nonempty prediction identifiers")
    if not all(r["protein_id"] in lookup for r in predictions):
        raise ValueError("A prediction identifier has no matching label")
    thresholds = {float(r["threshold"]) for r in predictions}
    if len(thresholds) != 1:
        raise ValueError("One locked model threshold is required per evaluation")
    threshold = thresholds.pop()
    y = np.array([int(lookup[r["protein_id"]]["label"]) for r in predictions])
    scores = np.array([float(r["decision_score"]) for r in predictions])
    if any(int(r["predicted_label"]) != int(s >= threshold) for r, s in zip(predictions, scores)):
        raise ValueError("Stored classes disagree with the fixed threshold")
    result = dict(threshold=threshold, scores_are_probabilities=False, **evaluate(y, scores, threshold))
    if args.bootstrap:
        group_lookup = {r["sample_id"]: r for r in table(args.groups)} if args.groups else lookup
        if any(not group_lookup.get(r["protein_id"], {}).get("homology_group") for r in predictions):
            raise ValueError("Group bootstrap requires homology_group for every predicted ID; supply --groups")
        groups = [group_lookup[r["protein_id"]]["homology_group"] for r in predictions]
        result["group_bootstrap"] = bootstrap(y, scores, groups, threshold, args.bootstrap)
    save_json(args.out, result)
    print(result)
