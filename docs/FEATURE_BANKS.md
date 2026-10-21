# Generating the complete five-encoder banks

The selected classifier needs only the ProtT5 mean bank included in the feature asset. The full 340-configuration comparison additionally requires residue and standard-deviation arrays for all five encoders. The following commands generate those arrays from the released FASTA files; stored results alone do not perform this step.

## Environment and checkpoint locks

Install the package and assets as in the README. Install a PyTorch build compatible with the CUDA driver, then:

```bash
python -m pip install -r environments/requirements-encoder.txt
```

The paper environment used Python 3.10, PyTorch 2.13.0+cu130, Transformers 5.18.0 and an RTX 5070 with 12 GB VRAM. Exact dependency versions and the original environment are in `environments/`. `build_feature_banks.py` uses native Transformers classes with remote code disabled.

| Key | Checkpoint | Native hidden precision | Storage / dimension |
| --- | --- | --- | --- |
| `prott5` | Rostlab/prot_t5_xl_half_uniref50-enc | FP16 | float16 / 1,024 |
| `ankh` | ElnaggarLab/ankh-base | BF16 | lossless uint16 BF16 bits / 768 |
| `esm` | facebook/esm2_t33_650M_UR50D | FP32 | float32 / 1,280 |
| `protbert` | Rostlab/prot_bert | FP16 | float16 / 1,024 |
| `esmc` | biohub/ESMC-600M | BF16 | lossless uint16 BF16 bits / 1,152 |

`config/encoder_checkpoints.json` lists source revisions and exact checkpoint/tokenizer file hashes. Four encoders have archived commit revisions. The original ESM2 checkpoint is content-pinned by its model, config and tokenizer SHA-256 values; its upstream repository is used for retrieval and any changed file is rejected. Encoder weights are downloaded separately under upstream terms.

## Check and generate

Work from the repository root. First inspect input consistency and required output storage without downloading weights or allocating large arrays:

```bash
python scripts/build_feature_banks.py --encoder prott5 --encoder-dir resources/prott5 --out full_banks/prott5 --dry-run
```

Then run one command per encoder. Each `--out` must be a new directory. `--download` fetches the locked checkpoint; omit it when the verified checkpoint files already exist.

```bash
python scripts/build_feature_banks.py --encoder prott5 --encoder-dir resources/prott5 --download --out full_banks/prott5
python scripts/build_feature_banks.py --encoder ankh --encoder-dir resources/ankh --download --out full_banks/ankh
python scripts/build_feature_banks.py --encoder esm --encoder-dir resources/esm --download --out full_banks/esm
python scripts/build_feature_banks.py --encoder protbert --encoder-dir resources/protbert --download --out full_banks/protbert
python scripts/build_feature_banks.py --encoder esmc --encoder-dir resources/esmc --download --out full_banks/esmc
```

For a small software check, add `--smoke-test` and use a separate temporary output directory. It extracts the three supplied software examples, marks the metadata `smoke_test_only`, and cannot be used as a full-search bank.

The script joins formal and H3 FASTA records against `config/feature_index.tsv` by ID, hash and length. It uses all residues in nonoverlapping windows of 1,022, excludes padding/special tokens, sorts windows by length/row/position, and follows the archived bounded-batch recipe. H3 rows are extracted without labels; training uses only the formal development indices. Mean and population standard deviation (`ddof=0`) are accumulated in FP64 and stored as FP32. Residue arrays retain each encoder's native precision losslessly. Ankh uses the archived fast-tokenizer backend rather than an incompatible automatically selected tokenizer.

Each encoder directory contains `mean.npy`, `std.npy`, `residues.npy`, `done.npy`, `complete.json` and progress metadata. The complete set requires approximately 78 GB, plus weights and training outputs. Current generation writes a new bank rather than resuming a partial directory. An interrupted directory has no valid completion record and must not be used for fitting.

## Verify and fit

```bash
bacrootfit train --root . --features-dir full_banks --all-configurations --out runs/search340 --dry-run
bacrootfit train --root . --features-dir full_banks --all-configurations --out runs/search340
```

Training verifies bank dimensions, row identity, complete status and file hashes before fitting. `complete.json` records whether regenerated file hashes match the historical bank; floating-point differences across kernels/hardware may prevent byte identity. Report the regenerated bank identities with new results instead of presenting them as the original frozen arrays.

This path regenerates the feature banks and reruns the registered search. It does not rerun source-paper data curation or rebuild the historical bridge-aware homology graph; the released evidence tables and fixed partitions remain its inputs. Original extraction and downstream scripts are retained in the results asset under `research_archive/` for audit.
