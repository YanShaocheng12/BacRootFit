"""Verify sequences, binary labels, repaired group separation, and model hashes."""
import argparse
import hashlib
import json
from pathlib import Path
from .io import table, fasta, sha256, save_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    rows = table(root / "data/samples.tsv")
    sequences = dict(fasta(root / "data/proteins.faa"))
    if len(rows) != 14505 or len(sequences) != 14505 or sum(int(r["label"]) for r in rows) != 1036:
        raise ValueError("Formal database size or label counts differ from the manuscript lock")
    if len({r["sample_id"] for r in rows}) != len(rows) or len({r["sequence_sha256"] for r in rows}) != len(rows):
        raise ValueError("Database identifiers or sequences are not unique")
    for row in rows:
        sequence = sequences[row["sample_id"]]
        if len(sequence) != int(row["length"]) or hashlib.sha256(sequence.encode()).hexdigest() != row["sequence_sha256"]:
            raise ValueError(f"Sequence identity check failed: {row['sample_id']}")
    feature_index = table(root / "config/feature_index.tsv")
    if [(r["sample_id"], r["sequence_sha256"]) for r in rows] != [(r["sample_id"], r["sequence_sha256"]) for r in feature_index[:14505]]:
        raise ValueError("Training data and feature row order differ")
    plan = json.loads((root / "config/plan.json").read_text(encoding="utf8"))
    group = [r["homology_group"] for r in rows]
    def separated(a, b):
        if set(a) & set(b) or {group[i] for i in a} & {group[i] for i in b}:
            raise ValueError("Repaired homology group crosses a split")
    separated(plan["development"], plan["internal_test"])
    if sorted(plan["development"] + plan["internal_test"]) != list(range(len(rows))):
        raise ValueError("Development/test partition does not cover the formal database exactly")
    seen = []
    for fold in plan["folds"]:
        separated(fold["pool"], fold["validation"])
        separated(fold["train"], fold["monitor"])
        if sorted(fold["train"] + fold["monitor"]) != sorted(fold["pool"]):
            raise ValueError("Training/monitor IDs do not partition the training pool")
        if sorted(fold["pool"] + fold["validation"]) != sorted(plan["development"]):
            raise ValueError("Fold does not partition the development set")
        seen.extend(fold["validation"])
    if sorted(seen) != sorted(plan["development"]):
        raise ValueError("OOF coverage is not exactly once")
    external = table(root / "external/H3/samples.tsv")
    if len(external) != 1878 or sum(int(r["label"]) for r in external) != 86:
        raise ValueError("H3 cohort counts changed")
    if [(r["sample_id"], r["sequence_sha256"]) for r in external] != [(r["sample_id"], r["sequence_sha256"]) for r in feature_index[14505:]]:
        raise ValueError("H3 records do not match the appended feature-bank rows")
    if sorted(plan["H3_full"]) != list(range(len(external))):
        raise ValueError("H3 plan indices must use the external cohort's local row coordinates")
    checked = 0
    manifest = json.loads((root / "release_manifest.json").read_text(encoding="utf8"))
    for relative, expected in manifest["canonical_files"].items():
        if (root / relative).exists():
            if sha256(root / relative) != expected:
                raise ValueError(f"Canonical file checksum differs: {relative}")
            checked += 1
    supplements = manifest.get("supplementary_files", {})
    for relative, expected in supplements.items():
        if not (root / relative).is_file() or sha256(root / relative) != expected:
            raise ValueError(f"Supplementary file checksum differs: {relative}")
    for role in ["development", "deployment"]:
        folder = root / "models" / role
        if not folder.exists():
            continue
        lock = json.loads((folder / "bundle.json").read_text(encoding="utf8"))
        for name, expected in lock["files"].items():
            if sha256(folder / name) != expected:
                raise ValueError(f"Model checksum differs: {role}/{name}")
            checked += 1
    record = dict(status="PASS", proteins=len(rows), positive=1036, controls=13469,
                  groups=len(set(group)), development=len(plan["development"]), internal_test=len(plan["internal_test"]),
                  folds=5, group_crossovers=0, canonical_files_verified=checked,
                  supplementary_files_verified=len(supplements),
                  scope="Identity/group integrity; not an exhaustive new sequence-similarity search")
    if args.out:
        save_json(args.out, record)
    print(json.dumps(record, indent=2))
