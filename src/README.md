#  SpecMine: Data loading and feature pipeline




## What it does
This package includes a data loader that reads the actual SpecMine sample Parquet files into pandas
DataFrames and a feature pipeline that combines the three loaded tables into one analysis table, with one row per specification.


1. Calls data_loader.py to read `spec_files.parquet`,
`spec_content_features.parquet`, and `spec_file_commits.parquet`.
2. Checks the specification keys. Missing/blank keys or duplicate keys in the
   specification or feature tables stop the run rather than multiply rows.
3. Left-joins features to specifications using `file_url_sha16`.
4. Summarizes commit history per specification, then left-joins that summary.
5. Writes a table with one row per input specification, plus a schema and run summary.


The specification table defines the population for this run. No source spec rows
are filtered. Unmatched feature/history rows are counted in the summary but do
not create extra specs. Missing feature values stay missing, not zero.
This first implementation covers the broad census only; Kiro integration and
the team's final predictor selection remain separate decisions.

## Outputs (replaced on each run)

| File | Purpose |
| --- | --- |
| `results/analysis_table.parquet` | Primary analysis table, preserving types |
| `results/analysis_table.csv` | Inspectable copy; use Parquet for subsequent code |
| `results/analysis_schema.json` | Column names, types, and source categories |
| `results/pipeline_summary.json` | Input/output counts, join/date issues, input SHA-256 hashes |

## Column definitions and decisions

Original `spec_files` columns retain their names and values. Every feature
column is prefixed with `feature_` to identify its source. For example,
`n_todo` becomes `feature_n_todo`; it is the dataset's existing measurement,
not a count newly computed by this pipeline. Consult the source data dictionary
for original field meanings.

| New column | Definition |
| --- | --- |
| `pipeline_has_feature_row` | A matching feature record was present; not a completeness check |
| `pipeline_history_rows` | Number of observed history rows for this spec, including duplicate commits |
| `pipeline_distinct_commit_count` | Distinct non-null commit SHAs in observed history |
| `pipeline_first_observed_commit_at` | Earliest valid `committed_at`, converted to UTC |
| `pipeline_last_observed_commit_at` | Latest valid `committed_at`, converted to UTC |
| `pipeline_valid_commit_date_rows` | Number of parseable commit timestamps |
| `pipeline_invalid_commit_date_rows` | Non-null timestamps that failed parsing |
| `pipeline_has_history_rows` | At least one matching history row exists |
| `pipeline_observed_history_span_days` | Last minus first observed valid timestamp, in fractional days |


## Setup and run
## First-time setup: Windows CMD

Requires Python 3.10+ and Git.
1. Download or clone specmine-abandonment-analysis repository.
2. Open CMD
3. Change directory to this package directory. 

```bat
cd "C:\your\actual\folder\path\"  
```
4. Install the dependencies:

```bat
python -m pip install -r requirements.txt
```

5. Download the SpecMine sample:

```bat
git clone https://github.com/shyamagarwal13/specmine-official.git data/specmine-official
```

6. Select the exact version:

```bat
git -C data/specmine-official checkout 9fbb61541046cb2fb770fa944192a3fc0b64a9b1
```

7. Run feature_pipeline:

```bat
python  src/feature_pipeline.py --data-dir data/specmine-official/data --output-dir results
```

## Subsequent runs
Once the dependencies and sample are available, run only:

```bat
python src/feature_pipeline.py --data-dir data/specmine-official/data --output-dir results
```

For the verified sample, expected output is:

```text
Created analysis table: 28,583 rows, 177 columns
Specifications without feature rows: 0
Specifications without history rows: 0
Outputs saved to: results
```



