import argparse, csv, hashlib, sys
from pathlib import Path
import numpy as np
from .models import catalog, predict_features

def fasta(path):
    records, name, seq = [], None, []
    for line in Path(path).read_text(encoding='utf8').splitlines():
        line = line.strip()
        if not line: continue
        if line.startswith('>'):
            if name is not None: records.append((name, ''.join(seq).upper()))
            name = line[1:].split()[0] if line[1:].strip() else ''
            seq = []
        elif name is None: raise ValueError('FASTA must start with a > identifier.')
        else: seq.append(''.join(line.split()))
    if name is not None: records.append((name, ''.join(seq).upper()))
    if not records or len({i for i, _ in records}) != len(records): raise ValueError('FASTA identifiers must be nonempty and unique.')
    for identifier, sequence in records:
        if not identifier or not sequence or set(sequence) - set('ACDEFGHIKLMNPQRSTVWY'):
            raise ValueError(f'{identifier}: sequence must contain canonical amino acids only.')
    return records

def main():
    parser = argparse.ArgumentParser(prog='bacrootfit')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list-models', help='List available pretrained classifiers.')
    p = sub.add_parser('predict', help='Score protein sequences in FASTA format.')
    p.add_argument('--input', required=True, help='Protein FASTA')
    p.add_argument('--output', required=True, help='Output TSV')
    p.add_argument('--model', default='adaptive_fusion', help='Model ID from list-models')
    p.add_argument('--features', help='Optional NPZ containing ids, sha256 and exact matching raw mean feature arrays')
    args = parser.parse_args()
    models = catalog()['models']
    if args.command == 'list-models':
        for name, info in models.items(): print(f"{name}\t{info['description']}")
        return
    if args.model not in models: parser.error(f'Unknown model: {args.model}')
    records = fasta(args.input)
    if args.features:
        with np.load(args.features, allow_pickle=False) as f:
            ids, hashes = f['ids'].astype(str).tolist(), f['sha256'].astype(str).tolist()
            expected = [hashlib.sha256(s.encode()).hexdigest() for _, s in records]
            if ids != [i for i, _ in records] or hashes != expected: raise ValueError('Cached feature IDs or sequence hashes do not match FASTA in order.')
            features = {k: f[k] for k in models[args.model]['encoders']}
    else:
        from .encoders import extract
        features = {}
        for name in models[args.model]['encoders']:
            print(f'Encoding with {name}...', file=sys.stderr, flush=True)
            features[name] = extract([s for _, s in records], name)
    result = predict_features(features, args.model)
    with Path(args.output).open('w', encoding='utf8', newline='') as f:
        fields = ['protein_id', 'sequence_sha256', 'model', 'decision_score', 'predicted_label']
        if result['weights'] is not None: fields += ['weight_prott5', 'weight_protbert', 'weight_esm2']
        writer = csv.DictWriter(f, fieldnames=fields, delimiter='\t'); writer.writeheader()
        for j, (identifier, sequence) in enumerate(records):
            row = dict(protein_id=identifier, sequence_sha256=hashlib.sha256(sequence.encode()).hexdigest(), model=args.model, decision_score=float(result['score'][j]), predicted_label=int(result['prediction'][j]))
            if result['weights'] is not None: row.update(zip(fields[-3:], map(float, result['weights'][j])))
            writer.writerow(row)
    print(f'Wrote {len(records)} predictions to {args.output}')

if __name__ == '__main__': main()
