# Third-party materials

The database preserves source-study DOIs, source-table locators, native sequence identifiers, mapping references and evidence limitations. Attribution records are supplied in the data asset (`study_catalog.tsv`, `source_file_catalog.tsv`, `measurement_source_links.tsv`, `protein_traceability.tsv`). A derived experimental label is not a replacement for the cited primary experiment.

Protein sequences retain their upstream accession and provider terms. The project's CC BY statement covers original compilation and curation contributions, not exclusive ownership of underlying sequences. Original article text, PDFs, source spreadsheets, raw sequencing reads and third-party executables are excluded from the release.

ProtT5 is downloaded separately from `Rostlab/prot_t5_xl_half_uniref50-enc`, revision `94a6abc029ae13029317b140b7424e012bf8dfbf`. Bundle manifests list exact required file hashes. Consult the upstream model card and provider terms before use; BacRootFit does not grant a new license for the pretrained encoder. Other encoder checkpoints used in the comparison are likewise not redistributed. The recorded Ankh checkpoint has CC-BY-NC-SA-4.0 metadata. Reproducing a comparison does not relicense its encoder.

Python dependencies are installed through their original distributions. They retain their own licenses. Original research scripts are project-authored source records, not vendored copies of the dependencies or executables they invoke.
