# SpecMine Dataset Documentation

## Purpose

This document identifies the SpecMine data needed for our specification abandonment study. The study examines specification activity, unfilled placeholders, and incomplete tasks. These are separate indicators; none alone proves that a specification has been abandoned.

This is a source-based dictionary. The team must verify the downloaded files before treating it as the final description of the analysis dataset.

## Dataset Sources

- Official project: https://github.com/shyamagarwal13/specmine-official
- Dataset files: https://huggingface.co/datasets/ShyAgarwal/specmine/tree/main
- Official field dictionary: https://github.com/shyamagarwal13/specmine-official/blob/main/DATA_DICTIONARY.md
- Official schema: https://github.com/shyamagarwal13/specmine-official/blob/main/schema.sql

The official repository distinguishes the full release from a curated sample. These should not be treated as interchangeable. Our planned approach is to use the full dataset if loading succeeds. The final release, downloaded files, and retained sample will be recorded after acquisition.

## Relevant Files

| File | Planned use |
| --- | --- |
| `spec_files.parquet` | Specification inventory and repository context |
| `spec_file_commits.parquet` | Specification revision history |
| `spec_content_features.parquet` | Extracted text and structure indicators |
| `spec_links.parquet` | Relationships between specifications and other artifacts |
| `pull_requests.parquet` | Supporting pull request information |
| `pr_files.parquet` | Files changed in those pull requests |
| `openspec_artifact_files.parquet` | OpenSpec artifacts and task counts |
| `openspec_code_refs.parquet` | Code references associated with OpenSpec artifacts |
| `repo_trees.parquet` | Repository tree collection metadata |
| `kiro_files.parquet` | Kiro file inventory |

The first four files form the proposed core dataset. Supporting files will be included only where they help answer the research question and can be linked reliably.

## Relevant Fields

Types below describe the intended values. Actual Parquet types must be checked during loading.

### Specification and Repository Information

| Field in `spec_files` | Type | Meaning |
| --- | --- | --- |
| `file_url_sha16` | Text | Specification identifier |
| `repo_name` | Text | Repository owner/name |
| `file_path` | Text | Path within the repository |
| `spec_tool` | Text | Attributed specification tool or path category |
| `spec_role` | Text | Artifact role |
| `repo_stars` | Integer | Recorded star count |
| `repo_archived` | Flag | Repository archive status |
| `repo_created_at` | Timestamp text | Repository creation time |
| `repo_pushed_at` | Timestamp text | Recorded repository push time |
| `file_first_commit_at` | Timestamp text | First recorded file commit |
| `file_last_commit_at` | Timestamp text | Last recorded file commit |
| `file_total_commits` | Integer | Recorded file commit count |

### Revision History

Relevant fields in `spec_file_commits` are `file_url_sha16`, `commit_sha`, `authored_at`, `committed_at`, and `author_login`. They connect revisions to specifications and provide commit timing and contributor information.

### Content Indicators

| Field in `spec_content_features` | Type | Intended interpretation |
| --- | --- | --- |
| `n_words` | Integer | Word count |
| `n_headings` | Integer | Heading count |
| `n_checkboxes` | Integer | Checkbox count |
| `n_checked` | Integer | Checked checkbox count |
| `n_todo` | Integer | Extracted TODO indicator count |
| `has_unfilled_placeholder` | Flag | Extracted placeholder indicator |
| `has_requirements` | Flag | Extracted requirements indicator |
| `has_acceptance_criteria` | Flag | Extracted acceptance criteria indicator |

These are parser-generated indicators. Examples and extraction rules should be checked before using them as study labels.

### Supporting Fields

- `spec_links`: `spec_url_sha16`, `rel`, `target`, and `provenance` describe artifact relationships.
- `pull_requests`: `repo_name`, `pr_number`, `tool`, `state`, and `is_merged` describe pull requests.
- `pr_files`: `repo_name`, `pr_number`, `tool`, and `file_path` identify changed files.
- `openspec_artifact_files`: `n_tasks` and `n_tasks_done` provide task counts.
- `openspec_code_refs`: `anchor_sha` and `exists_at_anchor` describe code reference checks at an anchoring commit.

## Proposed Measures

These measures are proposed for our study, rather than supplied abandonment labels:

- **Unchecked items:** `n_checkboxes - n_checked`, when both counts are valid.
- **Unchecked proportion:** unchecked items divided by `n_checkboxes`; undefined when there are no checkboxes.
- **Incomplete OpenSpec tasks:** `n_tasks - n_tasks_done`, when both counts are valid.
- **Time since last specification change:** observation cutoff minus the last recorded file commit.
- **Potential abandonment:** a candidate classification requiring an agreed observation window and manual validation.

Stable, completed specifications may receive no recent changes. Repository inactivity, replacements, and insufficient follow-up must also be considered.

## Linking and Validation

Join content features and file commits to specifications using `file_url_sha16`. Link relationships using `spec_links.spec_url_sha16`.

Before joining supporting tables, check key uniqueness and matching coverage. Repository paths can change, and one specification can have multiple commits or links. Joins must not silently inflate the number of specifications.

Missing values must remain distinguishable from zero. Invalid timestamps, duplicate records, failed retrievals, and inconsistent task counts should be reported.

If a content indicator defines an outcome, that same indicator should not also be used to predict that outcome. Time-based predictors must use information available before the outcome observation period.

## Acquisition and Completion Record

The team will download the selected release from an official source and record:

- Release or dataset revision and download date.
- Files successfully loaded.
- Actual columns and data types.
- Row counts before and after filtering.
- Missing values and join coverage.
- Observation cutoff and inclusion rules.

**Current status:** Source documentation is drafted. Successful loading, the final analysis sample, and the abandonment labeling rule remain unconfirmed.
