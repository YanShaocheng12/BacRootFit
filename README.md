# BacRootFit

BacRootFit provides a curated database of bacterial root-colonization evidence and a pretrained protein-sequence prediction model.

**[Browse the database](https://yanshaocheng12.github.io/BacRootFit/)** · **[Download software v1.0.1](https://github.com/YanShaocheng12/BacRootFit/releases/tag/v1.0.1)** · **[Data and models v1.0.0](https://github.com/YanShaocheng12/BacRootFit/releases/tag/v1.0.0)**

The database contains 14,505 complete proteins from 21 studies, with experimental labels and links to source evidence. The pretrained predictor uses frozen ProtT5 features and an RBF-SVM.

## Requirements and installation

Use Python 3.10. **Predicting a new FASTA requires a compatible NVIDIA GPU, CUDA-enabled PyTorch and the ProtT5 encoder.** Cached-feature prediction can run on CPU. See [installation and environments](docs/INSTALLATION.md) for dependencies and offline installation.

```bash
git clone --branch v1.0.1 https://github.com/YanShaocheng12/BacRootFit.git
cd BacRootFit
python -m pip install -e .
bacrootfit assets --only data models
```

Install a PyTorch build compatible with your GPU and CUDA driver, then:

```bash
python -m pip install -r environments/requirements-encoder.txt
```

## Predict your own FASTA

Input FASTA records must have unique identifiers and nonempty sequences containing canonical amino acids. The complete protein is used, including long sequences processed in successive windows.

```bash
bacrootfit download-encoder --encoder-dir resources/prott5 --model-dir models/deployment
bacrootfit predict --fasta your_proteins.faa --encoder-dir resources/prott5 --model-dir models/deployment --out predictions.tsv
```

### Using the pretrained model

For routine prediction, use the model fitted on the complete database: `models/deployment`. The bundle automatically applies its preprocessing parameters and decision threshold. No manual threshold entry is required.

The separate development model is provided to reproduce the released evaluations. See the [model card](docs/MODEL_CARD.md) for model roles and evaluation details.

## Output and interpretation

`predictions.tsv` contains protein ID, sequence hash, decision score, the automatically applied threshold and predicted label. **Decision scores are not probabilities.** A positive prediction identifies a candidate for further investigation; experimental labels remain specific to their source conditions.

## Data and model downloads

Software **v1.0.1** includes all configuration files, cohort groups and reproduction helpers. It uses unchanged **v1.0.0 data and model assets**, downloaded automatically by `bacrootfit assets`.

- [Database search, evidence and data downloads](https://yanshaocheng12.github.io/BacRootFit/)
- [Data, models, ProtT5 mean features and stored results](https://github.com/YanShaocheng12/BacRootFit/releases/tag/v1.0.0)

### Check the installation with the supplied example

```bash
bacrootfit predict --fasta examples/example.faa --features examples/example_raw_mean.npz --model-dir models/deployment --out example_predictions.tsv
```

This CPU check uses features matched to the three supplied example sequences. These features cannot be used for a different FASTA. For complete data-integrity checks, run `bacrootfit verify --out verification.json`.

## Documentation and reuse

- [Installation and dependency details](docs/INSTALLATION.md)
- [Model card and evaluation summary](docs/MODEL_CARD.md)
- [Data definitions and evidence](docs/DATA.md)
- [Reproduce the analyses](docs/REPRODUCIBILITY.md)
- [Evaluate predictions and recompute uncertainty](docs/EVALUATION.md)
- [Generate all five encoder banks](docs/FEATURE_BANKS.md)

Resource citation metadata are provided in [CITATION.cff](CITATION.cff). Code is **MIT**; original curation contributions and downstream model artifacts are **CC BY 4.0**. Third-party terms remain applicable; see [license details](THIRD_PARTY_NOTICES.md).
