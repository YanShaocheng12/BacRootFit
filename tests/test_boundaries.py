import itertools
import numpy as np
import pytest
from bacrootfit.metrics import evaluate, optimize_threshold


def test_mcc_search_matches_bruteforce_with_tied_scores():
    scores = np.array([0., 0., 1., 2., 2., 3.])
    boundaries = np.r_[np.nextafter(scores.max(), np.inf), np.unique(scores)]
    for labels in itertools.product([0, 1], repeat=len(scores)):
        if len(set(labels)) != 2:
            continue
        expected = max((evaluate(labels, scores, float(t))['MCC'], float(t)) for t in boundaries)
        threshold, report = optimize_threshold(labels, scores)
        assert (report['MCC'], threshold) == expected


def test_fixed_threshold_and_one_class_are_explicit():
    m = evaluate([1, 0], [.5, .4], .5)
    assert (m['TP'], m['TN']) == (1, 1)
    assert evaluate([0, 0], [1., 2.], 3.)['ROC_AUC'] is None
    with pytest.raises(ValueError):
        optimize_threshold([0, 1], [np.nan, 1.])
