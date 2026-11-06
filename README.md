# BacRootFit

BacRootFit provides a curated resource for bacterial root-association evidence and pretrained protein-sequence classifiers. The current resource contains **2,072 curated protein records**: 1,036 experimental positive proteins and 1,036 annotation-screened Swiss-Prot background proteins.

[Browse the database](https://yanshaocheng12.github.io/BacRootFit/) · [Model details](docs/MODELS.md) · [Evidence and data](docs/DATA.md)

## Installation

Use Python 3.10 in an environment with an NVIDIA GPU and a CUDA-enabled PyTorch installation for encoding protein sequences. Install the PyTorch build appropriate for your GPU first, then:

```bash
git clone https://github.com/YanShaocheng12/BacRootFit.git
cd BacRootFit
python -m pip install -e .
bacrootfit list-models
```

The first prediction downloads the required frozen protein language model weights from Hugging Face. Adaptive and equal-weight fusion need ProtT5, ProtBert and ESM-2; single-encoder classifiers need only their respective encoder. The three encoders are loaded one at a time. First use requires internet access and substantial disk space for the pretrained checkpoints.

## Predict your own protein FASTA

```bash
bacrootfit predict --input your_proteins.faa --model adaptive_fusion --output predictions.tsv
```

Input records must have unique identifiers and nonempty protein sequences containing the 20 canonical amino acids. Proteins longer than 1,022 residues are processed in consecutive windows and pooled across all residues. To try the interface, `examples/synthetic.faa` contains an artificial sequence; it is not a database protein.

```bash
bacrootfit predict --input examples/synthetic.faa --model adaptive_fusion --output predictions.tsv
```

Use `bacrootfit list-models` to see all 17 choices: five classifier types for each of ProtT5, ProtBert and ESM-2, plus equal-weight and adaptive fusion. For example:

```bash
bacrootfit predict --input your_proteins.faa --model prott5_svm --output predictions.tsv
```

Each output row contains the input ID, sequence SHA-256, model name, decision score and predicted label. Fusion models also report the three encoder weights. Thresholds and fitted preprocessing are loaded automatically. Scores are model decision values, **not calibrated probabilities**. A positive prediction is a candidate for further investigation, not evidence that a protein has a confirmed root-colonization phenotype.

## Model and data scope

The 17 classifiers are the evaluated models from the same homology-group-separated training split. Neural models, random forests and XGBoost use training seed 43; deterministic LR and SVM were fitted once. These are evaluation models fitted on the training portion, not separate full-dataset deployment retrains. See the [model card](docs/MODELS.md) for inputs, thresholds and limitations.

The database interface provides curated record identifiers and study metadata. This repository does not distribute the database protein sequences or external evaluation cohorts. Background records are selected using existing annotations and evidence; they are **not individually proven experimental negatives**. Original literature and third-party pretrained models retain their own terms.

For an existing feature archive, a CPU-only classifier interface is available through `bacrootfit predict --features features.npz`; the archive must contain `ids`, `sha256`, and the required raw mean arrays named `prott5`, `protbert`, and/or `esm2`. IDs and sequence hashes must match the supplied FASTA exactly and in order. The mean features must have been produced with the pinned encoders and preprocessing described in [model details](docs/MODELS.md).

## License

Code is made available under the [MIT License](LICENSE). Model artifacts and curated metadata are made available under CC BY 4.0 to the extent permitted by their third-party sources. Check the original licenses and conditions for UniProt, source studies and pretrained encoders before reuse. See [data notes](docs/DATA.md).
