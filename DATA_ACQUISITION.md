# Dataset Acquisition and Sampling

## Selected Dataset

Our team selected the SpecMine v1.1 curated 500-repository sample for the specification abandonment study.

Source: https://github.com/shyamagarwal13/specmine-official

This documentation describes the selected GitHub sample. The full SpecMine release and its mirrors are separate sources and are not the dataset selected for this sprint.

## Acquisition Instructions

1. Clone or download the source repository linked above.
2. Record the source commit hash and acquisition date so the same dataset revision can be retrieved later.
3. Preserve the original data folder and supporting files, including README.md, DATA_DICTIONARY.md, schema.sql, and sample_repos.txt.
4. Use the source data dictionary and schema to identify the relevant tables, fields, and join keys.
5. Keep the original files unchanged. Save any filtered or derived outputs separately.
6. Document the dependencies, commands, and paths used by the team's loading pipeline.

The source repository provides load.py and example.ipynb as loading examples. Our team's execution instructions and successful loading results will be documented with the implemented pipeline.

## Sampling and Study Scope

The 500-repository sample was curated by the dataset authors. Our team is using this existing sample rather than drawing a new random sample.

The sample is not representative of all open-source repositories. Findings will therefore be interpreted within the selected sample, with its coverage and selection limits stated explicitly.

An individual specification is the planned unit of analysis. The number of repositories in the release does not establish the number of specifications retained for our study.

Any additional selection rules, exclusions, or filters will be documented with their reasons and resulting record counts. Missing content, unmatched records, and limited commit history will also be reported where they affect the analysis.

## Reproducibility Records

The final acquisition record will include:

- Source URL, dataset version, source commit hash, and acquisition date.
- Files and tables actually loaded.
- Relevant fields and join keys used.
- Loading dependencies and execution commands.
- Record counts before and after filtering.
- Selection rules, exclusions, and data coverage limitations.

## Current Status

Jeremiah confirmed that the team is using the SpecMine v1.1 500-repository sample from the source repository linked above.

The exact acquisition revision, successfully loaded tables, record counts, and any additional filters have not yet been provided for this documentation. These details will be added once the loading results are available.
