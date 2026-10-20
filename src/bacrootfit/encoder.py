"""Acquire the pinned encoder, or extract raw means without fitting preprocessing."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from .io import fasta, sha256


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["extract", "download-encoder"])
    parser.add_argument("--model-dir", type=Path, default=Path("models/deployment"))
    parser.add_argument("--encoder-dir", type=Path, required=True)
    parser.add_argument("--fasta", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    lock = json.loads((args.model_dir / "bundle.json").read_text(encoding="utf8"))
    if args.mode == "download-encoder":
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id=lock["encoder_repo"], revision=lock["encoder_revision"],
                          allow_patterns=list(lock["encoder_files"]), local_dir=args.encoder_dir)
        for name, expected in lock["encoder_files"].items():
            if sha256(args.encoder_dir / name) != expected:
                raise ValueError(f"Pinned encoder checksum mismatch: {name}")
        print("Pinned encoder files verified")
        return
    if args.fasta is None or args.out is None or args.out.exists():
        parser.error("extract requires --fasta and a new --out path")
    from .portable_reference import encode
    records = fasta(args.fasta)
    mean = encode(records, args.encoder_dir, lock)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out, mean=mean, sequence_sha256=np.array([
        hashlib.sha256(sequence.encode()).hexdigest() for _, sequence in records]))
    print(json.dumps(dict(n=len(records), shape=list(mean.shape), scaled=False)))
