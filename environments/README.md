# Environments

The classifier/inference package pins NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2 and joblib 1.6.0. Python 3.10 is the original execution environment. `original_environment.json` records the reference machine and package versions for reproducibility.

For FASTA feature extraction and neural candidates, install a compatible CUDA PyTorch wheel (the registered run used `torch==2.13.0+cu130` on RTX 5070) and `requirements-encoder.txt`. CUDA compatibility depends on the local driver and hardware. Raw-mean/SVM inference and classical fits can run on CPU; CUDA FP16 feature extraction is required to follow the registered encoder recipe.

The old requirements list is preserved as `original_registered_requirements.txt`. Its SentencePiece/protobuf entries came from the legacy vendored setup rather than global packages. The public encoder environment uses SentencePiece 0.2.1 and protobuf 6.33.5, which were verified in isolated FASTA inference. Reproduction checks compare embeddings and scores; dependency installation alone is not a numerical validation.

The archived shared training engine imports PyTorch for all classifier types. Selected-model SVM refitting therefore requires PyTorch (a CPU build is sufficient); cached-feature prediction and evaluation do not. Full-search neural candidates and registered feature extraction require CUDA. Concrete per-encoder feature generation commands are in `docs/FEATURE_BANKS.md`.
