# Study Data Dictionary

## Scope

This dictionary describes the fields used or retained by the Sprint 1 implementation. The analysis covers 28,583 specifications from 415 repositories in the broad-census portion of the SpecMine v1.1 sample.

Source revision: 9fbb61541046cb2fb770fa944192a3fc0b64a9b1

Source dictionary: https://github.com/shyamagarwal13/specmine-official/blob/9fbb61541046cb2fb770fa944192a3fc0b64a9b1/DATA_DICTIONARY.md

Separate Kiro tables and other dataset layers are not included in this implementation.

## Input Tables and Join Key

| Table | Records | Role |
| --- | --- | --- |
| spec_files | 28,583 | Specification inventory and repository context |
| spec_content_features | 28,583 | Existing content measurements |
| spec_file_commits | 42,376 | Observed specification commit history |

All three tables are linked through file_url_sha16. Specification and feature identifiers must be present, nonblank, and unique within their respective tables. Commit records are summarized by specification before joining.

## Relevant Retained Fields

Specification fields retain their original names. Content-feature fields receive a feature_ prefix in the analysis table.

The types below describe the supplied output schema. An object type does not mean that a timestamp has already been parsed.

| Output field | Source | Loaded type | Meaning |
| --- | --- | --- | --- |
| file_url_sha16 | spec_files | object | Specification identifier and join key |
| repo_name | spec_files | object | Repository name |
| file_path | spec_files | object | Path within the repository |
| spec_tool | spec_files | object | Tool attribution |
| spec_role | spec_files | object | Artifact lifecycle role |
| repo_stars | spec_files | int64 | Stars recorded at capture |
| repo_created_at | spec_files | object | Repository creation timestamp |
| file_first_commit_at | spec_files | object | Source-reported first file commit timestamp |
| file_last_commit_at | spec_files | object | Source-reported latest file commit timestamp |
| file_total_commits | spec_files | int64 | Source-reported file commit count |
| feature_branch | spec_files | object | Feature branch value, when available |
| feature_n_words | spec_content_features.n_words | int64 | Word count |
| feature_n_headings | spec_content_features.n_headings | int64 | Heading count |
| feature_n_todo | spec_content_features.n_todo | int64 | TODO count |
| feature_n_checkboxes | spec_content_features.n_checkboxes | int64 | Total checkbox count |
| feature_n_checked | spec_content_features.n_checked | int64 | Checked checkbox count |
| feature_has_unfilled_placeholder | spec_content_features.has_unfilled_placeholder | int64 | Unfilled-placeholder flag |

These content measurements were supplied by SpecMine. The pipeline does not recalculate them from raw Markdown.

## Pipeline-Derived Fields

| Field | Loaded type | Definition |
| --- | --- | --- |
| pipeline_has_feature_row | bool | Whether a matching feature row exists |
| pipeline_history_rows | Int64 | Number of observed history rows, including duplicate commits if present |
| pipeline_distinct_commit_count | Int64 | Number of distinct non-null commit_sha values |
| pipeline_first_observed_commit_at | datetime64[ns, UTC] | Earliest valid observed committed_at timestamp |
| pipeline_last_observed_commit_at | datetime64[ns, UTC] | Latest valid observed committed_at timestamp |
| pipeline_valid_commit_date_rows | Int64 | Number of parseable commit timestamps |
| pipeline_invalid_commit_date_rows | Int64 | Number of non-null commit timestamps that failed parsing |
| pipeline_has_history_rows | boolean | Whether at least one matching history row exists |
| pipeline_observed_history_span_days | float64 | Difference between the latest and earliest valid observed timestamps, in fractional days |

The observed history span measures revision-history coverage. It does not measure inactivity since the last commit. A zero span can result from a single valid observed timestamp.

## Implemented Exploratory Indicators

| Indicator | Rule | Valid observations |
| --- | --- | --- |
| TODO present | feature_n_todo > 0 | Nonnegative integer TODO counts |
| Placeholder present | feature_has_unfilled_placeholder = 1 | Flag values of 0 or 1 |
| Unchecked checkbox present | feature_n_checkboxes > feature_n_checked | Nonnegative integer counts, with checked count no greater than total |

Percentages use only valid observed records for each indicator. Missing or invalid values are reported as unknown rather than negative cases. The indicator groups may overlap.

These are indicators of unfinished content, not validated abandonment labels or verified counts of unfinished implementation tasks.

## Missing Values and Validation

Missing feature values are preserved rather than replaced with zero. For specifications without matched history, observed-history counts are zero and date-based measures remain missing.

The supplied run summary reports no unmatched specification/feature/history records, duplicate specification-and-commit records, or missing or unparseable commit timestamps. This does not establish complete historical coverage or complete values in every retained field.

## Proposed Measures and Future Decisions

Unchecked checkbox count and proportion, time since last revision, and contributor counts remain proposed measures unless implemented and documented separately. The current pipeline does not add these as output columns.

Predictor selection, abandonment labels, observation cutoffs, and inactivity thresholds are separate study decisions. The 177 retained output columns are not a finalized predictor list.

## Full Column Inventory and Provenance Note

analysis_schema.json lists the output fields and loaded types. pipeline_summary.json records processing counts and input-file hashes.

One source-category entry needs correction: feature_branch is retained from spec_files, although the supplied schema labels it as spec_content_features. Its name starts with feature_, which causes the current schema-generation rule to misclassify its source. The dictionary above records its actual provenance.
