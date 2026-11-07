"""Create an artificial fixture; its vectors are not protein-language-model embeddings."""
import hashlib
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
lines = (root / 'examples/synthetic.faa').read_text(encoding='ascii').splitlines()
sequence = ''.join(lines[1:])
np.savez_compressed(root / 'examples/synthetic_features.npz',
                    ids=np.array([lines[0][1:]]),
                    sha256=np.array([hashlib.sha256(sequence.encode()).hexdigest()]),
                    prott5=np.zeros((1, 1024), dtype=np.float32))
