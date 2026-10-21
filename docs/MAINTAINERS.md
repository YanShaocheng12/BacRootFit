# Maintainer procedures

Public user documentation describes installation and operation. Original workflow filenames, source hashes and grouping corrections are retained in provenance and grouping history.

For local website development:

```bash
python -m http.server 8000 --directory website/dist
```

The `pages` GitHub Actions workflow publishes the static directory. Validate database filters, evidence details, original-source links and mobile layout before deployment. The `checks` workflow runs package tests on pushes and pull requests.

Protein details load small sequence files on demand. After updating the website FASTA or record index, regenerate them with `python scripts/build_website_sequences.py`; generation checks every ID, length and sequence hash against the source FASTA. The original complete FASTA remains the source for bulk downloads.

`python scripts/check_website_sequences.py` runs browser regression checks with Playwright and Chromium. Supply `--browser /path/to/chrome` to use an existing browser, or install Chromium through Playwright. The checks cover cold first opens, slow loading, retryable failures, sequence integrity and out-of-order dialog responses. `--public` checks first opens against the public site.

The public resource uses one release version for code, data and models. Keep direct artifact URLs and hashes in `release_manifest.json`, and publish a complete tagged source release. Preserve existing data/model archives; version any changed artifact. `scripts/configure_downloads.py` checks and updates artifact availability metadata.

Resource citation metadata belong to the software/database itself. A future publication citation can be added separately once its final metadata are available. Do not put provisional publication titles or DOI placeholders on the public homepage.
