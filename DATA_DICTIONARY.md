# Study Data Dictionary

## Scope and Source

This dictionary identifies candidate fields for our specification abandonment study using the selected SpecMine v1.1 500-repository sample. It does not claim that every listed table has already been loaded or selected for analysis.

Full source dictionary: https://github.com/shyamagarwal13/specmine-official/blob/main/DATA_DICTIONARY.md

## Core Tables

| Table | Contents |
| --- | --- |
| spec_files | Specification inventory and repository context |
| spec_file_commits | File revision history |
| spec_content_features | Parsed content features |
| spec_links | References to related artifacts |

## Candidate Fields

| Table | Field | Meaning |
| --- | --- | --- |
| spec_files | file_url_sha16 | Specification identifier |
| spec_files | repo_name | Repository identifier |
| spec_files | file_path | Repository-relative path |
| spec_files | spec_tool | Tool attribution |
| spec_files | spec_role | Artifact lifecycle role |
| spec_files | repo_stars | Stars at capture |
| spec_files | repo_created_at | Repository creation timestamp |
| spec_files | file_first_commit_at | First file commit timestamp |
| spec_files | file_last_commit_at | Latest file commit timestamp |
| spec_files | file_total_commits | Recorded file commit count |
| spec_file_commits | committed_at | Committer timestamp |
| spec_file_commits | author_login | Commit author login |
| spec_content_features | n_words | Word count |
| spec_content_features | n_headings | Heading count |
| spec_content_features | n_checkboxes | Checkbox count |
| spec_content_features | n_checked | Checked checkbox count |
| spec_content_features | n_todo | TODO count |
| spec_content_features | has_unfilled_placeholder | Placeholder flag |

## Join Keys

Broad specification tables use file_url_sha16. For spec_links, join spec_url_sha16 to spec_files.file_url_sha16.

Kiro has separate tables: kiro_files, kiro_repos, kiro_file_commits, and kiro_content_features. Kiro history and features join through kiro_file_id to kiro_files.id.

## Proposed Derived Measures

These are study measures, not additional source columns:

- Unchecked checkbox count: n_checkboxes minus n_checked.
- Unchecked proportion: unchecked count divided by n_checkboxes, only when n_checkboxes is greater than zero.
- Time since last recorded revision: a documented observation cutoff minus file_last_commit_at.
- Contributor count: distinct nonmissing author_login values in the available file history.

Missing values will remain missing unless a documented rule justifies another treatment. Negative counts, invalid timestamps, and unmatched joins will be investigated rather than silently corrected.

Checkbox and placeholder measures are candidate indicators of unfinished content. They do not establish abandonment by themselves. The team will document the abandonment rule separately and check competing explanations, including completed work and limited history.

## Validation and Current Status

The team must confirm which tables and fields the pipeline actually uses, their loaded data types, missingness, key uniqueness, join coverage, and retained record counts.

The source dictionary lists MySQL schema types. The actual Parquet and loaded types must be checked before analysis.

Any additional Kiro, OpenSpec, or pull-request fields used by the pipeline will be added with their source table, meaning, and join rules. The final dictionary will distinguish source fields from derived measures and outcome labels.
