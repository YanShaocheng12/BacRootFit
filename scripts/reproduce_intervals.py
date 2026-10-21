"""Recompute fixed-prediction released intervals using the released cohort groups.

This evaluates archived predictions; it neither trains a model nor changes a
threshold. Each cohort must be complete. Results are written separately.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from bacrootfit.io import table, write_table, save_json
from bacrootfit.evaluate import main as evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--bootstrap', type=int, default=5000)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    if out.exists():
        parser.error('Use a new output directory')
    candidate = json.loads((root/'config/selection_lock.json').read_text(encoding='utf8'))['spec']['id']
    checks = []
    archived = table(root/'results/uncertainty/primary_CI.tsv')
    for cohort in ['internal_full', 'H3_full']:
        rows = table(root/'results/tests'/candidate/f'{cohort}_predictions.tsv')
        predictions = [dict(protein_id=r['sample_id'], sequence_sha256=r['sequence_sha256'],
                            decision_score=r['decision_score'], threshold=r['threshold'],
                            predicted_label=r['predicted_label']) for r in rows]
        path = out/f'{cohort}_predictions.tsv'
        write_table(path, predictions)
        labels = root/('data/samples.tsv' if cohort == 'internal_full' else 'external/H3/samples.tsv')
        command = ['--labels', str(labels), '--predictions', str(path), '--out', str(out/f'{cohort}_metrics.json'),
                   '--cohort-ids', str(root/'config'/f'{cohort}_groups.tsv'),
                   '--groups', str(root/'config'/f'{cohort}_groups.tsv'), '--bootstrap', str(args.bootstrap), '--seed', '20261016']
        evaluate(command)
        report = json.loads((out/f'{cohort}_metrics.json').read_text(encoding='utf8'))
        errors = []
        if args.bootstrap == 5000:
            for row in archived:
                if row['cohort'] == cohort:
                    actual = report['group_bootstrap']['intervals'][row['metric']]
                    errors.extend(np.abs(np.asarray(actual)-[float(row['lower']), float(row['upper'])]).tolist())
            if not errors or max(errors) > 1e-12:
                raise ValueError('Intervals differ from the archived evaluation: '+cohort)
        checks.append(dict(cohort=cohort, n=report['n'], groups=report['group_bootstrap']['groups'],
                           bootstrap=args.bootstrap, max_interval_error=max(errors) if errors else None,
                           paper_interval_comparison=args.bootstrap == 5000))
    save_json(out/'verification.json', dict(status='PASS', fixed_predictions=True, refitting=False, checks=checks))


if __name__ == '__main__':
    main()
