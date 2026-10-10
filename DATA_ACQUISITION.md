# SpecMine Dataset Acquisition

## Purpose

This guide documents how to obtain the SpecMine data for our specification abandonment study. Relevant fields are described in [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

## Official Sources

- Project documentation: https://github.com/shyamagarwal13/specmine-official
- Parquet files: https://huggingface.co/datasets/ShyAgarwal/specmine/tree/main

The official project distinguishes the full release from a curated sample. Record which version is used because their coverage and selection differ.

## Download Steps

1. Open the Parquet files link above.
2. Open the dataset commit history and select the revision the team will use.
3. Record the complete revision identifier and download date.
4. Download the required files from that same revision using each file's download option.
5. Preserve the original filenames and store the files locally in `data/raw/`.

The proposed core files are:

- `spec_files.parquet`
- `spec_file_commits.parquet`
- `spec_content_features.parquet`
- `spec_links.parquet`

Supporting files may be needed for task completion, pull request information, and artifact relationships:

- `pull_requests.parquet`
- `pr_files.parquet`
- `openspec_artifact_files.parquet`
- `openspec_code_refs.parquet`
- `repo_trees.parquet`
- `kiro_files.parquet`

Check that each download is a complete Parquet file rather than an HTML page or Git LFS pointer. Keep the raw files unchanged.

## Loading Checks

Use a Parquet-compatible reader to inspect each downloaded table. Record:

- Filename, file size, and SHA-256 checksum.
- Row and column counts.
- Column names and actual data types.
- Missing values in required fields.
- Duplicate identifiers and key uniqueness.
- Timestamp parsing problems.
- Matching coverage between joined tables.

Compare the observed schema with `DATA_DICTIONARY.md` and resolve differences before analysis.

## Sampling Procedure

The planned approach is to use the full dataset if loading succeeds. If a smaller development sample is needed:

1. Obtain and sort the distinct repository names in `spec_files`.
2. Select a fixed number of repositories without replacement using a recorded random seed.
3. Retain all specifications from those repositories.
4. Filter content features and commit history using the retained specification identifiers.
5. Retain links whose source specification is selected, while recording targets outside the sample.
6. Filter supporting tables consistently and check join coverage.

Record the sample size, seed, filters, and retained row counts. The team must approve and document the final analysis sample.

If the official curated sample is used instead, record its release and explain its selection limitations.

## Storage and Reproducibility

Keep large raw files outside Git commits. Ensure `data/raw/` is excluded through `.gitignore`.

Commit these instructions, the loading code, and a download manifest recording the dataset revision, filenames, checksums, and observed row counts.

## Current Status

These are proposed acquisition instructions. Successful downloading and loading have not yet been confirmed.

The final documentation must match the release, files, sample, and filters actually used by the team's pipeline.
