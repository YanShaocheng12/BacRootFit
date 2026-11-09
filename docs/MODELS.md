# Model and inference details

The package provides 17 pretrained classifiers: ProtT5, ProtBert, and ESM-2 paired with LR, RBF-SVM, random forest, XGBoost and a nonlinear-projection MLP; plus equal-weight and adaptive three-encoder fusion. Classifiers are trained on the 1,333-protein training partition and use model-specific thresholds selected on the validation partition. The single published stochastic instance is seed 43; LR and SVM are deterministic single fits. These are not full-database refits or ensembles.

## Model inputs

Every encoder is frozen. Valid residues from the final hidden state are averaged; special and padding tokens are excluded. Proteins longer than 1,022 residues are split into nonoverlapping windows and their residue representations are aggregated with length weighting. The extraction settings match the evaluation: ProtT5 and ProtBert FP16 on CUDA, ESM-2 FP32 on CUDA, accumulation in float64. Hardware, driver and library differences can produce small numerical variation.

| Encoder | Checkpoint | Revision | Dimension |
|---|---|---|---:|
| ProtT5 | `Rostlab/prot_t5_xl_half_uniref50-enc` | `94a6abc029ae13029317b140b7424e012bf8dfbf` | 1,024 |
| ProtBert | `Rostlab/prot_bert` | `7a894481acdc12202f0a415dd567f6cfdb698908` | 1,024 |
| ESM-2 | `facebook/esm2_t33_650M_UR50D` | `08e4846e537177426273712802403f7ba8261b6c` | 1,280 |

The selected ESM-2 revision's `model.safetensors` SHA-256 matches the local encoder used for evaluation: `a08adabb949fa67ad3c14b509d04fd60368b35007b0095e3358f81200c4f4db0`.

LR and SVM use their own training-fitted `StandardScaler`; RF and XGBoost use raw mean features. Neural models use training-fitted scalers, then independent trainable projections `input→512→GELU→128→LayerNorm→L2`. The single-encoder classification head is `128→32→GELU→Dropout(0.2)→1`. Equal fusion averages the three 128-dimensional projected features. Adaptive fusion uses a `384→32→GELU→3→Softmax` gate and sums the projected vectors by the per-protein weights. It uses the same classification head. Gate weights describe model behavior and do not establish biological causation.

## Limitations

The evaluated background set is annotation-screened, not individually established as negative by root-colonization experiments. Internal test results were observed during model development and are retrospective. Experimental evidence can vary with strain, host and conditions. Classifier predictions do not prove a colonization phenotype; decision scores and RF vote fractions are not calibrated probabilities.

For cached raw embeddings, supply an NPZ containing `ids` and `sha256` Unicode arrays plus the required encoder arrays. The command checks exact ID and hash order before classification; the caller remains responsible for ensuring the features were extracted using the above pinned checkpoints and rules.
