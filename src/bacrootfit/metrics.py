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


def bootstrap(y, scores, groups, threshold, repeats=1000, seed=37):
    """Percentile group resampling at a locked threshold; no threshold optimization."""
    y, scores, groups = np.asarray(y), np.asarray(scores), np.asarray(groups)
    if len(y) != len(groups) or repeats < 2:
        raise ValueError("Matching group IDs and at least two bootstrap repeats are required")
    unique = np.unique(groups)
    members = [np.flatnonzero(groups == g) for g in unique]
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(repeats):
        indices = np.concatenate([members[i] for i in rng.integers(len(unique), size=len(unique))])
        if len(set(y[indices])) == 2:
            draws.append(evaluate(y[indices], scores[indices], threshold))
    if not draws:
        raise ValueError("No bootstrap resample contained both classes")
    return dict(requested=repeats, accepted=len(draws), seed=seed, unit="homology_group",
                intervals={k: np.quantile([v[k] for v in draws], [.025, .975]).tolist()
                           for k in ["ROC_AUC", "AP", "MCC", "precision", "recall", "accuracy", "balanced_accuracy"]})
