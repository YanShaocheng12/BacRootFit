"""Portable reproduction of the frozen-fold search or the selected configuration.

The numerical fit routines are the V27 routines; only paths and orchestration are
new. No test/H3 labels are loaded by the selection routine.
"""
import argparse
import importlib
import json
import math
import os
import shutil
import sys
from pathlib import Path
import numpy as np
from .io import table, write_table, save_json, sha256
from .metrics import optimize_threshold


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--features-dir", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--role", choices=["development", "deployment"], default="development")
    parser.add_argument("--config-id", default="prott5_mean_svm_C1_G1_balanced")
    parser.add_argument("--all-configurations", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    root, out = args.root.resolve(), args.out.resolve()
    if out == root or out.is_relative_to(root / "models") or out.is_relative_to(root / "data"):
        parser.error("Use a separate output directory; never replace released data or models")
    features = args.features_dir.resolve() if args.features_dir else root / "features"
    rows = table(root / "data/samples.tsv")
    if len(rows) != 14505:
        raise ValueError("The manuscript workflow requires the frozen 14,505-row database")
    plan = json.loads((root / "config/plan.json").read_text(encoding="utf8"))
    configs = json.loads((root / "config/candidates.json").read_text(encoding="utf8"))
    if args.role == "deployment":
        if args.all_configurations or args.config_id != "prott5_mean_svm_C1_G1_balanced":
            parser.error("Deployment reproduces the previously selected recipe, without new model search")
        deployment = json.loads((root / "config/deployment_plan.json").read_text(encoding="utf8"))
        configs, folds, train_ids = [deployment["spec"]], deployment["folds"], list(range(len(rows)))
    else:
        configs = configs if args.all_configurations else [s for s in configs if s["id"] == args.config_id]
        folds, train_ids = plan["folds"], plan["development"]
    if not configs:
        raise ValueError("Unknown configuration ID")
    # Check identity before fitting. H3 feature rows are retained in the bank,
    # but no H3 index is permitted in any fit or OOF partition.
    index = table(root / "config/feature_index.tsv")
    if [(r["sample_id"], r["sequence_sha256"]) for r in rows] != [(r["sample_id"], r["sequence_sha256"]) for r in index[:len(rows)]]:
        raise ValueError("Feature index identity or row order changed")
    for fold in folds:
        pool, validation = fold["pool"], fold["validation"]
        if max(pool + validation) >= len(rows) or set(pool) & set(validation):
            raise ValueError("A fit contains external or overlapping rows")
        if {rows[i]["homology_group"] for i in pool} & {rows[i]["homology_group"] for i in validation}:
            raise ValueError("Homology group crosses a development fold")
        if {rows[i]["homology_group"] for i in fold["train"]} & {rows[i]["homology_group"] for i in fold["monitor"]}:
            raise ValueError("Homology group crosses the early-stopping split")
    encoders = sorted({s["encoder"] for s in configs})
    requirements = {}
    for enc in encoders:
        required = {"mean.npy"}
        if any(s["encoder"] == enc and s["representation"] == "mean_std" for s in configs):
            required.add("std.npy")
        if any(s["encoder"] == enc and "attention" in s["representation"] for s in configs):
            required.add("residues.npy")
        requirements[enc] = sorted(required)
        metadata = json.loads((features / enc / "complete.json").read_text(encoding="utf8"))
        dimension = {"prott5": 1024, "ankh": 768, "esm": 1280, "protbert": 1024, "esmc": 1152}[enc]
        if metadata.get("smoke_test") or metadata.get("status") != "complete_verified" or metadata.get("proteins") != len(index) or metadata.get("dimension") != dimension:
            raise ValueError(f"Feature bank is incomplete or has the wrong dimensions: {enc}")
        if metadata.get("feature_index_sha256") and metadata["feature_index_sha256"] != sha256(root / "config/feature_index.tsv"):
            raise ValueError(f"Feature bank uses a different index: {enc}")
        for name in required:
            if sha256(features / enc / name) != metadata["files"][name]:
                raise ValueError(f"Feature-bank checksum mismatch: {enc}/{name}")
            array = np.load(features / enc / name, mmap_mode="r")
            expected_rows = sum(int(r["length"]) for r in index) if name == "residues.npy" else len(index)
            if array.shape != (expected_rows, dimension):
                raise ValueError(f"Feature-bank array dimensions differ: {enc}/{name}")
    summary = dict(role=args.role, configurations=len(configs), folds=len(folds),
                   CV_fits=len(configs)*len(folds), selected_refits=1,
                   training_proteins=len(train_ids), features=requirements,
                   uses_test_or_H3_labels_for_selection=False)
    print(json.dumps(summary, indent=2), flush=True)
    if args.dry_run:
        return
    out.mkdir(parents=True, exist_ok=True)
    data = out / "database/tables"
    data.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / "data/samples.tsv", data / "samples.tsv")
    for name in ["protocol.json", "feature_index.tsv"]:
        shutil.copyfile(root / "config" / name, out / name)
    if (root / "config/execution_resource_addendum.json").exists():
        shutil.copyfile(root / "config/execution_resource_addendum.json", out / "execution_resource_addendum.json")
    for enc in encoders:
        (out / "features" / enc).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(features / enc / "complete.json", out / "features" / enc / "complete.json")
    save_json(out / "public_run_plan.json", dict(summary, specs=configs, folds=folds))
    os.environ["BACROOTFIT_RUN_DIR"] = str(out)
    os.environ["BACROOTFIT_FEATURES_DIR"] = str(features)
    # Preserve the original sibling-module imports in the numerical engine.
    engine = Path(__file__).resolve().parent / "research_engine"
    sys.path.insert(0, str(engine))
    fit = importlib.import_module("fit26")
    y = np.array([int(r["label"]) for r in rows])
    results = []
    for order, spec in enumerate(configs):
        prediction, epochs = {}, []
        for fold in folds:
            folder = out / "cv" / spec["id"] / f"fold_{fold['fold']}"
            neural = spec["learner"] == "mlp"
            task = dict(folder=str(folder), spec=spec, train=fold["train"] if neural else fold["pool"],
                        monitor=fold["monitor"] if neural else [], validation=fold["validation"], seed=37)
            fit.fit_job(task)
            score = np.load(folder / "validation_scores.npy")
            epochs.append(json.loads((folder / "complete.json").read_text())["best_epoch"])
            for i, value in zip(fold["validation"], score):
                if i in prediction:
                    raise ValueError("Duplicate OOF prediction")
                prediction[i] = (float(value), fold["fold"])
            print(f"Fitted {spec['id']} fold {fold['fold']}", flush=True)
        if sorted(prediction) != sorted(train_ids):
            raise ValueError("OOF coverage is incomplete")
        score = np.array([prediction[i][0] for i in train_ids])
        threshold, metrics = optimize_threshold(y[train_ids], score)
        results.append(dict(candidate=spec["id"], order=order, threshold=threshold,
                            refit_epochs=math.ceil(float(np.median(epochs))), **metrics))
        write_table(out / "oof" / f"{spec['id']}.tsv", [dict(sample_id=rows[i]["sample_id"],
                    label=int(y[i]), fold=prediction[i][1], decision_score=prediction[i][0]) for i in train_ids])
    ranked = sorted(results, key=lambda r: (r["MCC"], r["ROC_AUC"], r["AP"], -r["order"]), reverse=True)
    write_table(out / "development_ranking.tsv", ranked)
    winner = ranked[0]
    spec = next(s for s in configs if s["id"] == winner["candidate"])
    save_json(out / "selection_lock.json", dict(spec=spec, selection=winner,
                                               role=args.role, uses_test_labels=False))
    target = out / "selected_model"
    fit.fit_job(dict(folder=str(target), spec=spec, train=train_ids, monitor=[], validation=[], seed=37,
                     fixed_epochs=winner["refit_epochs"] if spec["learner"] == "mlp" else None))
    if spec["learner"] != "mlp" and spec["encoder"] == "prott5" and spec["representation"] == "mean":
        canonical = json.loads((root / "models" / args.role / "bundle.json").read_text(encoding="utf8"))
        bundle = dict(canonical, spec=spec, threshold=winner["threshold"],
                      files={name: sha256(target / name) for name in ["model.joblib", "scaler.joblib"]})
        save_json(target / "bundle.json", bundle)
    save_json(out / "complete.json", dict(status="complete", **summary, winner=winner))
    print("Training complete. Selection used OOF only; held-out evaluation is a separate step.", flush=True)
