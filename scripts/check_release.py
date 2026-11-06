import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
models = json.loads((root/'models/catalog.json').read_text())['models']
assert len(models) == 17
for name, model in models.items():
    assert (root/model['artifact']).is_file(), name
    for scaler in model['scalers'].values(): assert (root/scaler).is_file(), name
site = json.loads((root/'website/dist/data/records.json').read_text(encoding='utf8'))
assert len(site['records']) == 2072 and len(site['studies']) == 21
assert sum(r['group']=='Experimental positive' for r in site['records']) == 1036
assert all('sequence' not in r and 'sha256' not in r for r in site['records'])
print('Verified 17 model artifacts and 2,072 metadata records.')
