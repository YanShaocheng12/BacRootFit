# BacRootFit

**Predicting bacterial root colonization-associated genes using protein language models.**

BacRootFit links genetic-perturbation evidence to complete native-strain proteins. Release **v1.0.0** contains **14,505 unique proteins: 1,036 positives and 13,469 experimentally screened small-effect controls, from 21 studies**. Each protein may link to multiple experimental observations.

The selected predictor uses frozen ProtT5 means → per-protein L2 normalization → training-fitted StandardScaler → class-balanced RBF-SVM. Scores are raw decision values, not probabilities. A control is a qualified experimental non-hit under the recorded conditions, rather than proof that a protein cannot affect colonization.

- [Database search and downloads](https://yanshaocheng12.github.io/BacRootFit/)
- [Versioned data, models, features and results](https://github.com/YanShaocheng12/BacRootFit/releases/tag/v1.0.0)
- [Data and evidence documentation](docs/DATA.md)
- [Reproducibility and verification scope](docs/REPRODUCIBILITY.md)

## Install and download

Python 3.10 is the reference environment. CPU inference with cached features does not require PyTorch or an encoder.

```bash
git clone https://github.com/YanShaocheng12/BacRootFit.git
cd BacRootFit
python -m pip install -e .
bacrootfit assets
bacrootfit verify --out verification.json
```

The asset command downloads four archives from the public v1.0.0 release and verifies SHA-256 before installation. It preserves locally modified files by stopping instead of overwriting them. `release_manifest.json` lists direct download URLs, archive hashes and canonical-file identities.

For offline installation, download the four ZIP assets to a directory of your choice, copy them to the offline computer, and run:

```bash
bacrootfit assets --from-dir /path/to/downloaded_archives
bacrootfit verify --out verification.json
```

## Predict from the supplied feature example

```bash
bacrootfit predict --fasta examples/example.faa --features examples/example_raw_mean.npz --model-dir models/deployment --out example_predictions.tsv
```

The three example proteins are database records for checking execution. They are not an independent validation cohort. Their raw 1,024-dimensional means include sequence hashes; substituted sequences are rejected.

## Predict a new FASTA

Install CUDA-compatible PyTorch and the [encoder dependencies](environments/README.md), then obtain the pinned ProtT5 snapshot:

```bash
bacrootfit download-encoder --encoder-dir resources/prott5 --model-dir models/deployment
bacrootfit predict --fasta your_proteins.faa --encoder-dir resources/prott5 --model-dir models/deployment --out predictions.tsv --save-features raw_means.npz
```

The registered extraction uses CUDA FP16, complete nonoverlapping windows of 1,022 residues and residue mean pooling with special tokens excluded. Long sequences are not truncated. Identifiers must be unique and sequences must contain canonical amino acids. No scaler is fitted during prediction. Output columns are `protein_id`, `sequence_sha256`, `decision_score`, `threshold`, and `predicted_label`; score ≥ threshold is positive.

## Reproduce the final model or the full comparison

| Task | Released materials and requirements |
| --- | --- |
| Run the final model on cached features | Model bundles and checked example included; CPU supported |
| Extract ProtT5 features from new FASTA and predict | Public entry point; requires encoder weights and the CUDA environment |
| Refit the selected ProtT5–SVM | ProtT5 mean bank and fixed partitions included |
| Rerun all 340 configurations / 1,700 CV fits | Requires all five complete mean/std/residue banks; not included in the lightweight download |

Refit the selected model without changing its data partitions or configuration. The shared fit engine imports PyTorch even for an SVM; install a CPU PyTorch build for this step if CUDA is not used:

```bash
bacrootfit train --root . --out runs/development --dry-run
bacrootfit train --root . --out runs/development
bacrootfit train --root . --role deployment --out runs/deployment
```

Each run reconstructs fivefold OOF predictions, chooses the pooled MCC-maximizing threshold and refits on the corresponding training pool. Standardization and class weights are fitted inside each training portion. Separate outputs preserve released models.

For the complete comparison:

```bash
bacrootfit train --root . --features-dir /path/to/all_five_banks --all-configurations --out runs/search340 --dry-run
bacrootfit train --root . --features-dir /path/to/all_five_banks --all-configurations --out runs/search340
```

The full banks occupy approximately 78 GB, excluding pretrained weights and new training outputs. [Per-encoder generation commands](docs/FEATURE_BANKS.md) describe checkpoints, dependencies, precision, storage and verification. Existing rankings and predictions allow result auditing; they do not substitute for regenerating the full comparison.

## Evaluate a locked predictor

Evaluation requires the prediction ID set to equal the expected cohort by default. For an internal-test prediction file produced by the public predictor:

```bash
bacrootfit evaluate --labels data/samples.tsv --cohort-ids config/internal_full_groups.tsv --predictions internal_predictions.tsv --out internal_metrics.json --bootstrap 5000 --seed 20261016
```

For H3:

```bash
bacrootfit evaluate --labels external/H3/samples.tsv --predictions H3_predictions.tsv --groups config/H3_full_groups.tsv --out H3_metrics.json --bootstrap 5000 --seed 20261016
```

Outputs include expected/matched/missing IDs, completeness, class counts and metrics. Predictions outside the specified cohort are rejected. Partial analyses require `--allow-subset` and are identified as such. With no `--cohort-ids`, the expected cohort is the complete label table. A single stored threshold is required; evaluation never selects a test threshold.

Recompute the paper's intervals from archived locked predictions, using the supplied cohort groups and the original multinomial resampling rule:

```bash
python scripts/reproduce_paper_intervals.py --root . --out runs/paper_intervals --bootstrap 5000
```

This checks the recomputed bounds against `results/uncertainty/primary_CI.tsv`. It evaluates archived predictions without retraining; [reproducibility documentation](docs/REPRODUCIBILITY.md) explains the distinction.

## Model roles and paper results

| Bundle | Training pool | Fixed raw threshold | Purpose |
| --- | --- | --- | --- |
| `models/development` | 11,664 development proteins | 0.17759950571640748 | Internal test and historical H3 results |
| `models/deployment` | All 14,505 database proteins | −0.028397905657864597 | Subsequent application; full-database OOF threshold |

The development model achieved internal-test ROC-AUC **0.8481**, AP **0.4519**, MCC **0.3968** on 2,841 proteins, and H3 ROC-AUC **0.8577**, AP **0.4011**, MCC **0.3683** on 1,878 proteins. H3 is a **three-hour duckweed surface-colonization transfer cohort** (86 positives / 1,792 controls), rather than root-specific or newly blind external validation. The full-data deployment refit has no separate held-out performance claim. Neither model is probability-calibrated.

## Database browser, citation and license

`website/dist/` is a static browser with study/strain/label filters, sequence search, evidence details and matched FASTA/TSV downloads. To run it locally: `python -m http.server 8000 --directory website/dist`, then open http://localhost:8000.

Cite the manuscript and versioned resource using [CITATION.cff](CITATION.cff). [Release access and maintenance](docs/PUBLISHING.md) documents distribution.

Code: **MIT** (`LICENSE`). Original curation contributions and downstream model artifacts: **CC BY 4.0** (`DATA_LICENSE.md`). Third-party sequences, publications, pretrained encoder weights and tools retain their upstream terms. Source identifiers are preserved. See `THIRD_PARTY_NOTICES.md`.
