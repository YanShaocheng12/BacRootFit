"""Build small, hash-prefix sequence files for on-demand website record details."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-dir', type=Path, default=Path(__file__).resolve().parents[1]/'website/dist')
    args = parser.parse_args()
    data = args.site_dir/'data'
    records = json.loads((data/'records.json').read_text(encoding='utf8'))['records']
    sequences, identifier, parts = {}, None, []
    for line in (data/'proteins.faa').read_text(encoding='utf8').splitlines():
        if line.startswith('>'):
            if identifier is not None:
                if identifier in sequences:
                    raise ValueError('Duplicate FASTA identifier')
                sequences[identifier] = ''.join(parts)
            identifier, parts = line[1:].split()[0], []
        elif line.strip():
            if identifier is None:
                raise ValueError('Sequence before FASTA header')
            parts.append(line.strip())
    if identifier is not None:
        if identifier in sequences:
            raise ValueError('Duplicate FASTA identifier')
        sequences[identifier] = ''.join(parts)
    if len({r['id'] for r in records}) != len(records) or set(sequences) != {r['id'] for r in records}:
        raise ValueError('Record and FASTA identifiers do not match exactly')
    shards = {}
    for row in records:
        sequence = sequences[row['id']]
        if len(sequence) != row['length'] or hashlib.sha256(sequence.encode()).hexdigest() != row['sha']:
            raise ValueError('Sequence identity mismatch: '+row['id'])
        shards.setdefault(row['sha'][:2], {})[row['id']] = sequence
    out = data/'sequences'
    out.mkdir(exist_ok=True)
    for prefix, values in sorted(shards.items()):
        (out/f'{prefix}.json').write_bytes(json.dumps(values, separators=(',', ':'), sort_keys=True).encode('utf8'))
    print(json.dumps(dict(proteins=len(records), shards=len(shards),
                         largest_shard_bytes=max((out/f'{p}.json').stat().st_size for p in shards),
                         full_FASTA_unchanged=True)))


if __name__ == '__main__':
    main()
