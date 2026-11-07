"""Compare the installed CLI's output with the reference, tolerating numeric drift."""
import csv
import math
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
def read(path):
    with open(path, newline='', encoding='utf8') as f:
        return list(csv.DictReader(f, delimiter='\t'))
expected = read(root / 'examples/synthetic_expected.tsv')
actual = read(sys.argv[1])
assert len(actual) == len(expected) == 1
for key in ('protein_id', 'sequence_sha256', 'model', 'predicted_label'):
    assert actual[0][key] == expected[0][key], (key, actual[0][key], expected[0][key])
assert math.isclose(float(actual[0]['decision_score']), float(expected[0]['decision_score']), rel_tol=1e-5, abs_tol=1e-6)
print('CPU example matches expected model output.')
