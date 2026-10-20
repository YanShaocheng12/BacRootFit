# GitHub, website and Zenodo release

Target repository: **YanShaocheng12/BacRootFit**, version **v1.0.0**.

The researcher authorized MIT for code and CC BY 4.0 for original curation data. Repository creation and upload need an authenticated connection to that GitHub account. Do not put access tokens into scripts, Git remotes or this repository.

## GitHub

The local publication handoff has `repository/`, `assets/`, validation receipts and ZIP files. Upload only the repository tree as Git source; attach the four separately checksummed assets to a release. The ignored large data/model/feature working directories are installed from those assets. `scripts/publish_github.ps1` validates the authenticated account and repository state, then creates the repository if needed, pushes `main` and creates a **draft** v1.0.0 release with the prepared assets. It refuses to overwrite an existing release. Check the concrete release before publishing it. The script does not create a Zenodo DOI.

Use `scripts/configure_downloads.py --repository https://github.com/YanShaocheng12/BacRootFit --tag v1.0.0` only after confirming the public release assets exist. It verifies each remote asset against the expected SHA-256 before recording downloadable URLs. Before that, local asset installation remains available via `--from-dir`.

GitHub blocks regular Git files above 100 MiB and recommends keeping repositories small. Release assets are appropriate for model and feature archives: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github

## Website

The static `website/dist/` browser can run locally and is ready for GitHub Pages. In repository Settings → Pages, choose GitHub Actions as the build source, then run the `pages` workflow. It uploads only the static directory. It serves real database records with source evidence and supports matched metadata/FASTA download. The large model and feature downloads point to the public release only after availability is verified. Online ProtT5 prediction is not implemented; users run the checked local predictor.

The bundled database download is versioned and checksum-listed. Experimental labels and model output are clearly named. Do not reinterpret H3 as root-specific colonization or the deployment model's training-set predictions as a new held-out test.

## Zenodo

Create the data record and link it to the code release, or enable Zenodo's GitHub integration before publishing the selected release. GitHub's official instructions are https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content . Zenodo can archive public GitHub releases; a GitHub-only archive does not automatically include separately installed local feature banks.

Deposit the four asset ZIPs plus the code snapshot, `release_manifest.json`, checksums and the exact paper version metadata. The handoff also supplies a ready-to-upload combined archive. Use `.zenodo.json` for software metadata and `zenodo/data_metadata.json` for data; review the record title, author names, affiliations and license scope. No unissued DOI is present. After DOI minting, add the **version-specific** DOI to `CITATION.cff`, the README, website and manuscript availability statement, retaining the relation to any concept DOI and separate data/code records.
