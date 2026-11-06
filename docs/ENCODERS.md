# Encoder and model use

Use `bacrootfit list-models` for exact model IDs. The prediction command applies the model-specific scaler, threshold and score convention automatically. `adaptive_fusion` and `equal_fusion` require three encoders; the other models require one. A CUDA GPU is required for the provided FASTA extraction path.

The feature input API is `from bacrootfit.models import predict_features`. It accepts a dictionary of raw mean feature matrices and a model ID. Verify that externally produced embeddings use the same checkpoints, sequence processing, precision and windowing; the API cannot infer their provenance.

For offline installations, set `BACROOTFIT_PROTT5_PATH`, `BACROOTFIT_PROTBERT_PATH`, and/or `BACROOTFIT_ESM2_PATH` to local directories containing the exact pinned checkpoints. Verify their hashes against the checkpoint details before use.

The project does not include training datasets, external evaluation sequences, cached dataset embeddings, full encoder weights, or a claim that the current classifiers were refit on all 2,072 records. Original publications and pretrained model terms apply.
