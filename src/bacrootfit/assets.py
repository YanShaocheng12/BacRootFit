"""Install only checksum-verified release assets from a local folder or configured URLs."""
import argparse
import json
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
from .io import sha256


def unpack_checked(archive, root):
    root = Path(root).resolve()
    with ZipFile(archive) as bundle:
        for item in bundle.infolist():
            name = PurePosixPath(item.filename)
            if name.is_absolute() or ".." in name.parts or "\\" in item.filename or ":" in item.filename:
                raise ValueError("Unsafe archive member")
            target = root.joinpath(*name.parts).resolve()
            if not target.is_relative_to(root):
                raise ValueError("Archive destination escapes root")
            if target.exists() and not item.is_dir():
                with bundle.open(item) as stream:
                    import hashlib
                    expected = hashlib.file_digest(stream, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else hashlib.sha256(stream.read()).hexdigest()
                if sha256(target) != expected:
                    raise FileExistsError(f"Refusing to overwrite a changed file: {target}")
        bundle.extractall(root)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--from-dir", type=Path)
    parser.add_argument("--only", nargs="+", choices=["data", "models", "features", "results"])
    args = parser.parse_args(argv)
    manifest = json.loads((args.root / "release_manifest.json").read_text(encoding="utf8"))
    for asset in manifest["assets"]:
        if args.only and asset["kind"] not in args.only:
            continue
        if args.from_dir:
            path = args.from_dir / asset["filename"]
            if sha256(path) != asset["sha256"]:
                raise ValueError(f"Asset checksum mismatch: {path.name}")
            unpack_checked(path, args.root)
        else:
            if not asset.get("download_url"):
                raise ValueError("No public URL has been published. Supply --from-dir with the prepared assets folder.")
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / asset["filename"]
                urllib.request.urlretrieve(asset["download_url"], path)
                if sha256(path) != asset["sha256"]:
                    raise ValueError("Downloaded asset checksum mismatch")
                unpack_checked(path, args.root)
        print(f"Installed and verified: {asset['filename']}")
