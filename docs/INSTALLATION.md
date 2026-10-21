# Installation

## Get the complete software release

```bash
git clone --branch v1.0.0 https://github.com/YanShaocheng12/BacRootFit.git
cd BacRootFit
python -m pip install -e .
bacrootfit assets --only data models
```

Alternatively, download the v1.0.0 source ZIP from GitHub, extract it, change to the extracted directory and run the last two commands. This software release includes the cohort groups and all reproduction helpers; no files need to be copied from `main`.

Python 3.10 is the reference environment. Package installation provides pinned NumPy, SciPy, scikit-learn and joblib dependencies. Cached-feature SVM prediction and evaluation do not require PyTorch.

## New sequence prediction

Feature extraction follows the registered CUDA FP16 recipe and requires an NVIDIA GPU, a compatible CUDA PyTorch build and encoder dependencies:

```bash
python -m pip install -r environments/requirements-encoder.txt
bacrootfit download-encoder --encoder-dir resources/prott5 --model-dir models/deployment
```

The reference hardware and dependency versions are in [environments](../environments/README.md). Install the PyTorch build appropriate to your driver and hardware. Long sequences use full nonoverlapping windows; CPU extraction is not silently substituted for the registered recipe.

## Optional analysis assets

```bash
bacrootfit assets --only features results
bacrootfit verify --out verification.json
```

The supplied feature asset contains raw ProtT5 means for the selected model. The complete five-encoder banks are a separate large-data requirement; see [feature generation](FEATURE_BANKS.md).

## Offline installation and verification

Download the desired v1.0.0 asset ZIPs from the [data/model release](https://github.com/YanShaocheng12/BacRootFit/releases/tag/v1.0.0), then:

```bash
bacrootfit assets --from-dir /path/to/downloaded_archives --only data models
```

The installer checks each downloaded archive against the release manifest's SHA-256. It stops rather than overwriting a changed local file. The full `bacrootfit assets` command installs all four assets; `--only` selects the required categories. `release_manifest.json` lists the files and checksums for the complete BacRootFit v1.0.0 release.

## Source layout

`models/deployment` is the routine prediction bundle; `models/development` is the evaluation bundle. Keep each model's scaler, weights and configuration together. No fitting or threshold selection takes place when predicting.
