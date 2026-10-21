# Release access and maintenance

## Public distribution

- Database browser: https://yanshaocheng12.github.io/BacRootFit/
- Source code: https://github.com/YanShaocheng12/BacRootFit
- Paper data and model release: https://github.com/YanShaocheng12/BacRootFit/releases/tag/v1.0.0

The release provides separate data, models, ProtT5 mean features and results ZIPs. Install them with `bacrootfit assets`, or download them manually and use `bacrootfit assets --from-dir /path/to/archives`. SHA-256 values and direct URLs are in `release_manifest.json`.

The release's original ZIPs preserve the paper data and model identities. The `main` branch carries subsequent documentation and evaluation-interface fixes; use its current checkout for complete-cohort checking, the supplied H3 bootstrap groups and the new reproduction helpers. These additions do not change paper model weights, sequences, labels or fixed predictions.

## Website and code

The GitHub Pages workflow publishes `website/dist/`. The browser presents experimental labels and source evidence; the repository provides local prediction and reproduction instructions. Evidence pages display a source publication plus recorded supplement/worksheet/row or article figure/table details. Original archive paths remain in downloadable audit records.

Installation, executable examples and the distinction between selected-model reproduction and full comparison are in the [README](../README.md), [reproducibility scope](REPRODUCIBILITY.md) and [feature-bank guide](FEATURE_BANKS.md).

## Maintenance procedure

Maintainers should preserve the paper archive hashes. For a changed data or model artifact, issue a new version rather than silently replacing a paper archive. Documentation-only and interface changes can be tracked separately on `main`.

`scripts/configure_downloads.py` checks public asset identities and synchronizes the repository manifest and both website metadata files. It can verify downloaded content, or use a saved GitHub release API response with `--release-metadata` to verify GitHub's server-side SHA-256 and file sizes. Actual asset installation always verifies downloaded bytes.

To update the site, commit the validated static sources, push `main` and run the `pages` GitHub Actions workflow. Automated checks run independently on pushes. `scripts/publish_github.ps1` remains a maintainer bootstrap utility for first-time releases; it is not required by users.

## Citation and archival metadata

The current resource can be cited by repository URL and version. `CITATION.cff`, `.zenodo.json` and `zenodo/data_metadata.json` contain citation and archival metadata. A future archival deposit should include the versioned assets and matching source snapshot; add the issued version-specific DOI consistently to those records and the website. An archive of Git source alone does not include separately downloaded feature banks.

Code is MIT; original curation contributions are CC BY 4.0. Third-party material retains upstream terms.
