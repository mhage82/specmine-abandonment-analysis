# Specification Abandonment Analysis — Research Framing

## Research Question

What predicts that a software specification will be abandoned, left with placeholders, or left with incomplete tasks?

We will examine these outcomes separately. A placeholder or unchecked checkbox can indicate unfinished content, but neither establishes abandonment on its own.

## Motivation and Expected Contribution

Specifications help developers describe requirements, plan changes, and track work. Some may stop receiving attention while still containing unfinished content.

Our study will examine whether document structure, revision activity, repository context, and tool family are associated with these outcomes. We aim to provide a reproducible analysis with clear measurement rules, supporting examples, and limitations. Observed associations will not be interpreted as proof of causation.

Sprint 1 establishes the data foundation and explores candidate indicators. It does not yet evaluate abandonment prediction.

## Competing Explanations

A specification without recent updates may describe completed, stable work. It may also have been replaced, deferred, or maintained elsewhere.

Unchecked checkboxes and placeholders may occur in templates, examples, or outdated documents. Limited historical coverage and short observation periods can also make active work appear abandoned.

These explanations will guide the abandonment definition and review of candidate examples.

## Unit of Analysis, Population, and Sample

The unit of analysis is an individual specification artifact identified by file_url_sha16. Repository information provides context. Multiple specifications from the same repository may share development practices, so later comparisons and evaluation must account for that dependence.

The target population is specification-driven development artifacts in open-source repositories.

For Sprint 1, the implementation uses the broad-census portion of the SpecMine v1.1 curated 500-repository sample at revision 9fbb61541046cb2fb770fa944192a3fc0b64a9b1.

Source: https://github.com/shyamagarwal13/specmine-official

The analyzed sample contains 28,583 specifications from 415 repositories. It uses spec_files.parquet, spec_content_features.parquet, and spec_file_commits.parquet. Separate Kiro tables and other dataset layers are outside this implementation.

No additional row filtering or subsampling was applied within these three tables. All 28,583 specifications were retained. The source sample is curated rather than random, so findings describe the analyzed sample rather than population rates for all open-source specifications.

## Candidate Explanatory Variables

The study will consider these groups where the available data supports them:

- Document structure and content, including length, headings, and requirement-related features.
- Revision activity, including observed commit counts and timing.
- Repository context, including age, activity, and popularity.
- Contributor context, where suitable measures can be constructed from available history.
- Tool family and artifact lifecycle role.

The current pipeline retains metadata and existing content features and adds observed-history summaries. Contributor counts and time since last revision are not currently generated. The retained 177 columns are not a finalized predictor list.

## Outcomes and Measurement

The planned outcomes are abandonment, unfilled placeholders, and incomplete tasks.

The implemented exploratory analysis examines positive TODO counts, placeholder flags, and unchecked checkboxes. Missing or invalid measurements are treated as unknown, and percentages use valid observed records. Indicator groups may overlap.

Unchecked checkboxes are a proxy for unfinished content rather than a verified count of incomplete implementation tasks. No abandonment labels or inactivity thresholds have been applied.

The team must document the abandonment rule, observation period, and treatment of completed, stable, replaced, or incompletely observed specifications before evaluating that outcome.

A measure used to define an outcome will not also be used as a predictor of that same outcome. Predictive analysis requires explanatory variables measured before the outcome period. If the available data cannot support that ordering, findings will be described as associations.

The observed history span measures the interval between the earliest and latest valid recorded commits. It does not measure inactivity after the last commit.

## Sprint 1 Status

The supplied code and run summary document successful preparation of an analysis table with 28,583 rows and 177 columns. The source revision, loaded files, counts, and absence of additional filtering are recorded in DATA_ACQUISITION.md. Field meanings, output names, and derived measures are documented in DATA_DICTIONARY.md.

Research framing and dataset documentation are ready for teammate review. Final abandonment rules and predictor selection remain separate team decisions. This documentation does not claim validated abandonment labels, predictive results, or an independent rerun.
