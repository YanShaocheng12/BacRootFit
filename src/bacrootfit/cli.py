"""Public command routing. CUDA dependencies are imported only when needed."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(prog="bacrootfit")
    parser.add_argument("command", choices=["predict", "extract", "train", "evaluate", "verify", "assets", "download-encoder"])
    args, rest = parser.parse_known_args()
    if args.command == "predict":
        from .predict import main as run
    elif args.command == "train":
        from .train import main as run
    elif args.command in ["extract", "download-encoder"]:
        from .encoder import main as run
        rest = [args.command] + rest
    elif args.command == "verify":
        from .verify import main as run
    elif args.command == "assets":
        from .assets import main as run
    else:
        from .evaluate import main as run
    run(rest)
