"""Small, dependency-light readers and checked artifact installation."""
import csv
import hashlib
import json
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_table(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def save_json(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf8")


def fasta(path):
    result = []
    identifier = None
    sequence = []
    seen = set()
    for raw in Path(path).read_text(encoding="utf8").splitlines():
        if not raw.strip():
            continue
        if raw.startswith(">"):
            if identifier is not None:
                result.append((identifier, "".join(sequence)))
            parts = raw[1:].split()
            if not parts or parts[0] in seen:
                raise ValueError("FASTA identifiers must be nonempty and unique")
            identifier = parts[0]
            seen.add(identifier)
            sequence = []
        else:
            if identifier is None:
                raise ValueError("Sequence occurs before a FASTA header")
            sequence.append(raw.strip())
    if identifier is not None:
        result.append((identifier, "".join(sequence)))
    if not result or any(not seq or set(seq) - set("ACDEFGHIKLMNPQRSTVWY") for _, seq in result):
        raise ValueError("Nonempty complete canonical amino-acid sequences are required")
    return result
