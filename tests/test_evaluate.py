import json
import numpy as np
import pytest
from bacrootfit.evaluate import main
from bacrootfit.io import write_table
from bacrootfit.metrics import WeightedMetrics, evaluate


def inputs(tmp_path):
    labels, predictions = tmp_path/'labels.tsv', tmp_path/'predictions.tsv'
    write_table(labels, [dict(sample_id='a', label=1, homology_group='g1'),
                         dict(sample_id='b', label=0, homology_group='g2')])
    write_table(predictions, [dict(protein_id='a', decision_score=.7, threshold=.5, predicted_label=1)])
    return labels, predictions, tmp_path/'metrics.json'


def test_missing_predictions_require_explicit_subset(tmp_path):
    labels, predictions, out = inputs(tmp_path)
    args = ['--labels', str(labels), '--predictions', str(predictions), '--out', str(out)]
    with pytest.raises(ValueError, match='matched=1, expected=2, missing=1'):
        main(args)
    assert not out.exists()
    main(args+['--allow-subset'])
    result = json.loads(out.read_text())
    assert result['coverage']['missing_ids'] == ['b']
    assert result['coverage']['positive'] == 1
    assert result['coverage']['complete'] is False


def test_predefined_cohort_is_complete_and_rejects_extra_ids(tmp_path):
    labels, predictions, out = inputs(tmp_path)
    cohort = tmp_path/'cohort.tsv'
    write_table(cohort, [dict(sample_id='a')])
    args = ['--labels', str(labels), '--predictions', str(predictions), '--out', str(out), '--cohort-ids', str(cohort)]
    main(args)
    assert json.loads(out.read_text())['coverage']['complete'] is True
    write_table(predictions, [dict(protein_id='b', decision_score=.2, threshold=.5, predicted_label=0)])
    with pytest.raises(ValueError, match='outside the expected'):
        main(args+['--allow-subset'])


def test_group_table_identity_is_checked(tmp_path):
    labels, predictions, out = inputs(tmp_path)
    write_table(predictions, [dict(protein_id='a', decision_score=.7, threshold=.5, predicted_label=1),
                              dict(protein_id='b', decision_score=.1, threshold=.5, predicted_label=0)])
    groups = tmp_path/'groups.tsv'
    write_table(groups, [dict(sample_id='a', label=0, homology_group='g1'),
                         dict(sample_id='b', label=0, homology_group='g2')])
    with pytest.raises(ValueError, match='Group table label'):
        main(['--labels', str(labels), '--predictions', str(predictions), '--out', str(out),
              '--bootstrap', '2', '--groups', str(groups)])


def test_weighted_bootstrap_metrics_equal_expanded_samples_with_ties():
    y = np.array([0, 1, 0, 1, 1, 0, 0, 1])
    scores = np.array([.2, .7, .7, .1, .7, -.2, .3, .1])
    weights = np.array([0, 2, 1, 3, 1, 0, 4, 2])
    expanded = np.repeat(np.arange(len(y)), weights)
    expected = evaluate(y[expanded], scores[expanded], .3)
    assert np.allclose(WeightedMetrics(y, scores, .3)(weights), [expected[k] for k in WeightedMetrics.keys], atol=1e-12)
