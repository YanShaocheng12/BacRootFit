"""Pooled metrics, deterministic MCC boundaries and group-bootstrap uncertainty."""
import math
import numpy as np
from sklearn.metrics import average_precision_score, confusion_matrix, matthews_corrcoef, roc_auc_score


def evaluate(y, scores, threshold):
    y = np.asarray(y, dtype=int)
    scores = np.asarray(scores, dtype=np.float64)
    if y.ndim != 1 or len(y) == 0 or scores.shape != y.shape or not np.isfinite(scores).all():
        raise ValueError("Expected matching nonempty labels and finite scores")
    if not set(y) <= {0, 1} or not math.isfinite(threshold):
        raise ValueError("Binary labels and a finite threshold are required")
    predicted = scores >= threshold
    tn, fp, fn, tp = (int(v) for v in confusion_matrix(y, predicted, labels=[0, 1]).ravel())
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    return dict(n=len(y), positive=int(y.sum()), negative=int((1-y).sum()),
                ROC_AUC=float(roc_auc_score(y, scores)) if len(set(y)) == 2 else None,
                AP=float(average_precision_score(y, scores)) if y.sum() else None,
                MCC=float(matthews_corrcoef(y, predicted)),
                precision=tp / (tp + fp) if tp + fp else 0.0, recall=recall,
                specificity=specificity, F1=2*tp / (2*tp+fp+fn) if 2*tp+fp+fn else 0.0,
                accuracy=float(np.mean(y == predicted)), balanced_accuracy=(recall+specificity)/2,
                TP=tp, FP=fp, FN=fn, TN=tn)


def optimize_threshold(y, scores):
    """Use development OOF only. Highest threshold wins exact MCC ties."""
    y = np.asarray(y, dtype=int)
    scores = np.asarray(scores, dtype=np.float64)
    if set(y) != {0, 1} or scores.shape != y.shape or not np.isfinite(scores).all():
        raise ValueError("Threshold selection requires both classes and finite matching OOF scores")
    order = np.argsort(-scores, kind="stable")
    ordered = scores[order]
    labels = y[order]
    ends = np.r_[np.flatnonzero(ordered[:-1] != ordered[1:]), len(ordered)-1]
    tp = np.r_[0, np.cumsum(labels)[ends]].astype(float)
    fp = np.r_[0, np.cumsum(1-labels)[ends]].astype(float)
    fn, tn = y.sum()-tp, (1-y).sum()-fp
    den = np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    mcc = np.divide(tp*tn-fp*fn, den, out=np.zeros_like(den), where=den > 0)
    bounds = np.r_[np.nextafter(ordered[0], np.inf), ordered[ends]]
    threshold = float(bounds[int(np.argmax(mcc))])
    return threshold, evaluate(y, scores, threshold)


def bootstrap(y, scores, groups, threshold, repeats=1000, seed=20261016):
    """Percentile group resampling at a locked threshold; no threshold optimization."""
    y, scores, groups = np.asarray(y), np.asarray(scores), np.asarray(groups)
    if len(y) != len(groups) or repeats < 2:
        raise ValueError("Matching group IDs and at least two bootstrap repeats are required")
    evaluate(y, scores, threshold)
    if set(y) != {0, 1}:
        raise ValueError("Group bootstrap requires both label classes")
    unique, inverse = np.unique(groups, return_inverse=True)
    metric = WeightedMetrics(y, scores, threshold)
    rng = np.random.default_rng(seed)
    draws = []
    rejected = 0
    while len(draws) < repeats:
        # Match the paper's multinomial draws over sorted group identifiers.
        weights = rng.multinomial(len(unique), np.full(len(unique), 1 / len(unique)))[inverse]
        if not weights @ y or not weights @ (1-y):
            rejected += 1
            if rejected > repeats * 100:
                raise ValueError("Too many single-class group-bootstrap resamples")
            continue
        draws.append(metric(weights))
    values = np.asarray(draws)
    return dict(requested=repeats, accepted=len(draws), rejected_single_class=rejected,
                seed=seed, unit="homology_group", groups=len(unique),
                resampling="multinomial_equal_probability_groups", interval="percentile_95",
                intervals={k: np.quantile(values[:, i], [.025, .975]).tolist()
                           for i, k in enumerate(WeightedMetrics.keys)})


class WeightedMetrics:
    """Evaluate repeated group membership without materializing repeated samples.

    Tied-score ROC and AP boundaries follow the archived paper implementation.
    """
    keys = ["ROC_AUC", "AP", "MCC", "precision", "recall", "specificity", "F1", "accuracy", "balanced_accuracy"]

    def __init__(self, y, scores, threshold):
        self.y = np.asarray(y, int)
        self.predicted = np.asarray(scores) >= threshold
        self.order = np.argsort(-np.asarray(scores), kind="stable")
        ordered = np.asarray(scores)[self.order]
        self.ends = np.r_[np.flatnonzero(ordered[:-1] != ordered[1:]), len(ordered)-1]

    def __call__(self, weights):
        y, predicted = self.y, self.predicted
        w = np.asarray(weights, float)
        pos, neg = w @ y, w @ (1-y)
        tp, fp = w @ (y*predicted), w @ ((1-y)*predicted)
        fn, tn = pos-tp, neg-fp
        den = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
        recall, specificity = tp/pos, tn/neg
        precision = tp/(tp+fp) if tp+fp else 0.
        ordered_w, ordered_y = w[self.order], y[self.order]
        ct = np.cumsum(ordered_w*ordered_y)[self.ends]
        cf = np.cumsum(ordered_w*(1-ordered_y))[self.ends]
        tr, fr = np.r_[0., ct/pos], np.r_[0., cf/neg]
        auc = np.sum(np.diff(fr)*(tr[1:]+tr[:-1])*.5)
        pp = np.divide(ct, ct+cf, out=np.zeros_like(ct), where=ct+cf > 0)
        ap = np.sum(np.diff(tr)*pp)
        return np.array([auc, ap, (tp*tn-fp*fn)/den if den else 0., precision, recall,
                         specificity, 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.,
                         (tp+tn)/(pos+neg), (recall+specificity)/2])
