# Database and evidence

Release v1.0.0 contains 14,505 unique complete proteins (1,036 label 1, 13,469 label 0), 21 contributing studies and 7,799 homology groups. Study counts are source memberships; one sequence may link to more than one source. Use `studies_included.tsv` or active catalogue entries when counting the 21 studies; `study_catalog.tsv` also contains archived noncontributing sources.

## Files

| Path after installing the data asset | Meaning |
| --- | --- |
| `data/samples.tsv`, `data/proteins.faa` | Formal training proteins, labels, homology groups and sequence hashes |
| `data/measurements_qualified.tsv` | Qualified source observations linked to formal proteins |
| `data/measurements_all_linked.tsv` | Broader linked observations; not all are training-eligible |
| `data/training_qualification.tsv`, `data/evidence_quality.tsv` | Qualification decisions and evidence limitations |
| `data/measurement_source_links.tsv` | Study, supplement sheet/row or other source locator |
| `data/protein_traceability.tsv`, `data/sequence_mapping_replay.tsv` | Gene-to-native-protein mapping and translation checks |
| `data/context/` | Study-level positive definitions, growth controls, host and assay context |
| `data/audit/` | Candidate decisions and negative endpoint-band checks |
| `data/literature_selection/` | Actual search expressions, retrieved-record reconciliation and source dispositions |
| `external/H3/` | Separate historical duckweed surface-colonization cohort; never training data |

`data/data_dictionary.tsv` describes original fields. Sequence SHA-256 values refer to the unwrapped amino-acid sequence. The `V27_part` field and `config/plan.json` define the released split; `original_split` in older trace tables is historical and must not replace them.

## Labels

Label 1 denotes a qualified genetic-perturbation phenotype linked to reduced colonization under a source experiment's conditions. Each source retains its own published effect direction, author call, statistical criteria, condition handling and evidence tier. The detailed per-study rules are included in `data/context/study_positive_and_growth_rules.tsv`; there is no fabricated universal positive p-value rule. General-growth/outgrowth control differs by study and is recorded rather than assumed.

Label 0 denotes a tested, quality-qualified small-effect non-hit. After source-level QC and negative qualification, each retained eligible endpoint must have a finite log2 effect within log2(0.8) to log2(1.2). That bound applies to the recorded source effect definition; it is not universally an absolute CFU ratio and is not an equivalence-test certificate. Unmeasured, missing or ambiguous proteins are not assigned zero. No 1:3 downsampling or score-based filtering was applied to the final database.

Conflicting observations, growth limitations and sequence mapping ambiguity have separate records. Measurements, label decisions and model predictions are different entities; browser evidence pages do not turn a predicted score into an experimental label.

## Literature accounting

The 50-source disposition table reconciles frozen historical source records and reviews; 21 contributed final proteins and 29 did not. It must not be represented as 50 prospectively full-text-screened studies. Retrieved-record totals and supplementary retrospective coverage checks are documented separately in the supplied literature audit. Source screening and protein-level eligibility are not the same count.

## SQLite

The tables are the authoritative public export. `python scripts/build_sqlite.py --root . --out bacrootfit.sqlite` creates an indexed local SQLite copy with samples, source observations, study metadata and source links. This avoids distributing another redundant binary database in the Git repository.
