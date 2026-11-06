from pathlib import Path
import json
import joblib
import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

REPO = Path(__file__).resolve().parents[2]
DIMS = {'prott5': 1024, 'protbert': 1024, 'esm2': 1280}

class NeuralClassifier(nn.Module):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode
        self.proj = nn.ModuleList([nn.Sequential(nn.Linear(d, 512), nn.GELU(), nn.Linear(512, 128), nn.LayerNorm(128)) for d in DIMS.values()])
        self.head = nn.Sequential(nn.Linear(128, 32), nn.GELU(), nn.Dropout(.2), nn.Linear(32, 1))
        self.gate = nn.Sequential(nn.Linear(384, 32), nn.GELU(), nn.Linear(32, 3)) if mode == 'M5' else None

    def forward(self, inputs):
        if self.mode in ('M1', 'M2', 'M3'):
            i = int(self.mode[1]) - 1
            h = F.normalize(self.proj[i](inputs[i]), dim=1)
            alpha = None
        else:
            z = [F.normalize(p(x), dim=1) for p, x in zip(self.proj, inputs)]
            alpha = torch.softmax(self.gate(torch.cat(z, dim=1)), dim=1) if self.gate else torch.full((len(z[0]), 3), 1/3, device=z[0].device)
            h = sum(alpha[:, i:i+1] * z[i] for i in range(3))
        return self.head(h).squeeze(1), alpha

def catalog(root=REPO):
    return json.loads((Path(root) / 'models' / 'catalog.json').read_text(encoding='utf8'))

def predict_features(features, model_id, root=REPO):
    """Score raw mean embeddings, applying the model's own scaler and threshold."""
    root = Path(root)
    item = catalog(root)['models'][model_id]
    required = item['encoders']
    n = len(features[required[0]])
    for name in required:
        a = np.asarray(features[name])
        if a.shape != (n, DIMS[name]) or not np.isfinite(a).all():
            raise ValueError(f'Invalid {name} mean features: {a.shape}')
    if item['family'] == 'neural':
        # Non-used branches of the three-branch network are never evaluated for single encoders.
        inputs = []
        for name, dim in DIMS.items():
            if name in required:
                scaler = joblib.load(root / item['scalers'][name])
                x = scaler.transform(np.asarray(features[name], dtype=np.float32)).astype(np.float32)
            else:
                x = np.zeros((n, dim), dtype=np.float32)
            inputs.append(torch.from_numpy(x))
        net = NeuralClassifier(item['mode']).eval()
        checkpoint = torch.load(root / item['artifact'], map_location='cpu', weights_only=True)
        net.load_state_dict(checkpoint['state_dict'], strict=True)
        with torch.inference_mode():
            logits, alpha = net(inputs)
        score = logits.numpy().astype(np.float64)
        weights = None if alpha is None else alpha.numpy()
    else:
        name = required[0]
        x = np.asarray(features[name], dtype=np.float32)
        if item['scalers']:
            x = joblib.load(root / item['scalers'][name]).transform(x).astype(np.float32)
        clf = joblib.load(root / item['artifact'])
        if item['method'] == 'RF': score = clf.predict_proba(x)[:, 1]
        elif item['method'] == 'XGBoost': score = clf.predict(x, output_margin=True)
        else: score = clf.decision_function(x)
        score = np.asarray(score, dtype=np.float64)
        weights = None
    return {'score': score, 'prediction': (score >= item['threshold']).astype(int), 'weights': weights, 'threshold': item['threshold']}
