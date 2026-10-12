# Dataset Acquisition and Sampling

## Source and Selected Revision

We used the broad-census portion of the SpecMine v1.1 curated 500-repository sample.

Source: https://github.com/shyamagarwal13/specmine-official

Exact source revision: 9fbb61541046cb2fb770fa944192a3fc0b64a9b1

The implemented analysis covers 28,583 specifications from 415 repositories. Separate Kiro tables and other dataset layers are outside this run.

## Acquisition and Execution Instructions

Run these commands from the team project directory, with Python 3.10+ and Git installed.

1. Install the project dependencies:

    python -m pip install -r requirements.txt

2. Clone the source repository:

    git clone https://github.com/shyamagarwal13/specmine-official.git data/specmine-official

3. Check out the selected revision:

    git -C data/specmine-official checkout 9fbb61541046cb2fb770fa944192a3fc0b64a9b1

4. Run the loading and preparation code:

    python src/feature_pipeline.py --data-dir data/specmine-official/data --output-dir results

If the source repository is already present at that path, reuse it and check out the specified revision rather than cloning it again.

The loader reads the three required Parquet files from the source data directory. The preparation code combines them into one analysis table without modifying the original files.

## Loaded Files

| Input file | Records |
| --- | --- |
| spec_files.parquet | 28,583 |
| spec_content_features.parquet | 28,583 |
| spec_file_commits.parquet | 42,376 |

## Sampling and Preparation Decisions

We retained all specification rows from the selected broad-census tables. No additional row filtering or subsampling was applied.

Content features are left-joined to specifications using file_url_sha16. Commit history is summarized by that identifier before joining, so multiple commits do not create multiple analysis rows for the same specification.

Missing feature values remain missing. Where a specification has no matched history, observed-history counts are set to zero and date-based measures remain missing. This records the absence of observed history rather than assuming that no development activity occurred.

The source sample was curated rather than randomly selected. Findings therefore describe the analyzed sample and should not be interpreted as population rates for all open-source specifications.

## Supplied Run Results

The supplied pipeline_summary.json records an output of 28,583 rows and 177 columns.

Every specification matched a content-feature record and at least one history record. The summary reported zero:

- Feature or commit records without a matching specification.
- Specifications without matched features or history.
- Duplicate specification-and-commit records.
- Missing or unparseable commit timestamps.

These checks support the loading and preparation process. They do not establish complete historical coverage or complete values in every field.

No abandonment labels, inactivity thresholds, or predictive models were applied by this pipeline.

## Reproducibility Evidence

The preparation code writes:

- results/analysis_table.parquet: the combined table with preserved data types.
- results/analysis_table.csv: a copy for inspection.
- results/analysis_schema.json: output columns, loaded types, and source categories.
- results/pipeline_summary.json: record counts, processing checks, and input-file SHA-256 hashes.

The source revision identifies the selected dataset version, and the recorded hashes allow comparison of the three input files across runs. The project README documents setup and execution.

This documentation reflects Jeremiah's supplied code and run outputs. It does not claim an independent rerun by another team member.
