# BacRootFit

**Predicting bacterial root colonization-associated genes using protein language models.**

BacRootFit links genetic-perturbation evidence to complete native-strain proteins and provides a frozen ProtT5 mean → per-protein L2 normalization → training-fitted StandardScaler → class-balanced RBF-SVM predictor. Scores are raw decision values, not probabilities.

The manuscript database contains **14,505 unique proteins: 1,036 positives and 13,469 experimentally screened small-effect controls, from 21 contributing studies**. A control label is an operational experimental non-hit under the recorded conditions; it does not prove universal absence of a colonization function. Evidence, source limitations and provenance are preserved per record.

## Install

Python 3.10 is the registered reference. The CPU package can load cached features and perform SVM inference without installing PyTorch or an encoder.

```bash
python -m pip install -e .
bacrootfit --help
```

Download the four versioned ZIP assets from this repository's release, or use the prepared local `assets/` folder supplied with the publication handoff:

```bash
bacrootfit assets --from-dir ../assets
bacrootfit verify --out verification.json
```

The asset installer verifies SHA-256 and refuses to replace locally changed files. After the GitHub release is public, `bacrootfit assets` discovers its versioned download URLs from the GitHub API and verifies each download against the frozen manifest; `--from-dir` also works offline. `release_manifest.json` records all archive hashes and canonical-file identities without claiming an unpublished deposit already exists.

## Predict from a checked feature example

```bash
bacrootfit predict --fasta examples/example.faa --features examples/example_raw_mean.npz --model-dir models/deployment --out example_predictions.tsv
```

The three example proteins are training-database records supplied to test execution. They are not an independent validation cohort. The NPZ contains raw 1,024-dimensional means and a sequence hash for each FASTA record; shuffled or substituted sequences are rejected.

## Predict a new FASTA

Install a CUDA-compatible PyTorch wheel and the encoder dependencies documented in `environments/README.md`, then obtain the **pinned** ProtT5 snapshot:

```bash
bacrootfit download-encoder --encoder-dir resources/prott5 --model-dir models/deployment
bacrootfit predict --fasta your_proteins.faa --encoder-dir resources/prott5 --model-dir models/deployment --out predictions.tsv --save-features raw_means.npz
```

The registered recipe uses CUDA FP16, complete nonoverlapping windows of 1,022 residues and residue mean pooling with special tokens excluded. Long proteins are not truncated. Input identifiers must be unique and sequences must contain canonical amino acids. No scaler is fitted at prediction time. CPU feature extraction is not silently substituted for the registered numerical recipe.

Output columns: `protein_id`, `sequence_sha256`, `decision_score`, `threshold`, `predicted_label`. A score **≥ threshold** is called positive.

## Reproduce the selected model

```bash
bacrootfit train --root . --out runs/development --dry-run
bacrootfit train --root . --out runs/development
bacrootfit train --root . --role deployment --out runs/deployment
```

Each command uses the frozen repaired homology-group partitions, reconstructs pooled fivefold OOF predictions, selects the overall MCC-maximizing threshold and refits on the corresponding training pool. Standardization and balanced sample weights are fitted separately inside each training portion. The public numerical fit routines preserve the original V27 implementation; path configuration and orchestration were made portable. Released weights remain unchanged, and reruns write to a separate directory.

To rerun **all 340 registered configurations / 1,700 CV fits**:

```bash
bacrootfit train --root . --features-dir /path/to/all_five_native_banks --all-configurations --out runs/search340 --dry-run
bacrootfit train --root . --features-dir /path/to/all_five_native_banks --all-configurations --out runs/search340
```

This larger search needs the five original encoder banks, including standard deviations and residue arrays for learned pooling, plus CUDA. The lightweight release includes the ProtT5 mean bank sufficient for the selected model, not the approximately 78-GB full bank collection. `config/feature_banks/` pins native arrays by hash. See `docs/REPRODUCIBILITY.md` for what is included, what was tested and the remaining full-search prerequisites. The complete 340-configuration ranking and stored OOF predictions are distributed in the results asset; they are not recreated by the small example.

## Evaluate a locked predictor

```bash
bacrootfit evaluate --labels data/samples.tsv --predictions predictions.tsv --out metrics.json --bootstrap 1000
```

Predictions and labels are joined by protein ID. A single model threshold must already be present in the prediction file. This command never optimizes a test threshold. Reported paper confidence intervals and paired comparisons are preserved in `results/uncertainty/`; arbitrary new evaluation runs are separate outputs.

## Model roles and paper results

| Bundle | Training pool | Fixed raw threshold | Purpose |
| --- | --- | --- | --- |
| `models/development` | 11,664 development proteins | 0.17759950571640748 | Reproduce internal test and historical H3 results |
| `models/deployment` | All 14,505 database proteins | −0.028397905657864597 | Subsequent application; threshold derived from full-database OOF |

The development model achieved internal test ROC-AUC **0.8481**, AP **0.4519**, MCC **0.3968** on 2,841 proteins, and H3 ROC-AUC **0.8577**, AP **0.4011**, MCC **0.3683** on 1,878 proteins. H3 is a **three-hour duckweed surface-colonization transfer cohort** (86 positives / 1,792 controls); it is not a root-specific cohort or a newly blind study. Neither model has been calibrated into probabilities. The deployment refit must not inherit the development model's held-out performance claim.

## Data, browsing and citation

`website/dist/` provides a static browser with study/strain/label filters, protein/locus search, evidence details, matched FASTA/TSV downloads and local prediction instructions. Run `python -m http.server 8000 --directory website/dist` and open http://localhost:8000. GitHub Pages can serve the same directory using the supplied workflow after Pages is enabled for GitHub Actions.

See `docs/DATA.md`, `docs/MODEL_CARD.md` and `docs/PUBLISHING.md`. Cite the manuscript title and authors listed in `CITATION.cff`; replace the provisional software citation with the version-specific Zenodo DOI once deposited. No DOI has been invented or reserved by this package.

## License

Original project code: **MIT** (`LICENSE`). Project-authored curation tables, annotations and downstream model artifacts: **CC BY 4.0** (`DATA_LICENSE.md`). Third-party sequences, publications, encoder weights and tools retain upstream terms; their source identifiers are retained and they are not relicensed by this project. Pretrained encoder weights and original paper PDFs/supplementary spreadsheets are not included. See `THIRD_PARTY_NOTICES.md`.
