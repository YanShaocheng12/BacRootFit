"""Build an indexed SQLite view from the authoritative release tables."""
import argparse
import csv
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=Path.cwd())
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
if args.out.exists():
    parser.error('Output exists; use a new file')
args.out.parent.mkdir(parents=True, exist_ok=True)
sources = {'samples': 'samples.tsv', 'studies': 'study_catalog.tsv',
           'measurements': 'measurements_qualified.tsv', 'source_links': 'measurement_source_links.tsv',
           'traceability': 'protein_traceability.tsv'}
with sqlite3.connect(args.out) as db:
    for name, filename in sources.items():
        with (args.root/'data'/filename).open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            columns = reader.fieldnames
            quoted = ', '.join('"'+c.replace('"','""')+'" TEXT' for c in columns)
            db.execute(f'CREATE TABLE "{name}" ({quoted})')
            db.executemany(f'INSERT INTO "{name}" VALUES ({",".join("?" for _ in columns)})',
                           (tuple(row[c] for c in columns) for row in reader))
        if 'sample_id' in columns:
            db.execute(f'CREATE INDEX "{name}_sample_idx" ON "{name}" (sample_id)')
    db.execute('CREATE INDEX samples_strain_idx ON samples (strain)')
    db.execute('CREATE INDEX samples_label_idx ON samples (label)')
    print(dict(tables=len(sources), samples=db.execute('SELECT COUNT(*) FROM samples').fetchone()[0], out=str(args.out)))
