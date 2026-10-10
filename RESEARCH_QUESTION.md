# Specification Abandonment Analysis — Research Framing

## Research Question

What predicts that a software specification will be abandoned, left with placeholders, or left with incomplete tasks?

We will study these outcomes separately. Unfinished content may suggest incomplete work, but it does not automatically mean that a specification has been abandoned.

## Motivation and Expected Contribution

Specifications can help developers describe requirements, plan changes, and track implementation. However, some may stop receiving attention while still containing placeholders or unfinished tasks.

Our study will examine whether document structure, revision activity, repository context, and tool family are associated with these outcomes. The expected contribution is a reproducible analysis with clearly documented indicators, supporting examples, and limitations. We will not interpret observed associations as proof of causation.

## Competing Explanations

A specification with no recent updates may describe completed, stable work. It may also have been replaced, deferred, or maintained elsewhere.

Unchecked tasks and placeholders may be outdated rather than evidence of ongoing incomplete work. Limited commit history or a short observation period can also make an active specification appear abandoned.

These explanations will guide the team's operational definition and review of candidate examples.

## Unit of Analysis, Population, and Sample

The planned unit of analysis is an individual specification artifact. Repository-level information will provide context. Because multiple artifacts may come from the same repository, they will not be treated as fully independent without justification.

The target population is open-source repositories using specification-driven development artifacts. Our accessible sample is the SpecMine v1.1 curated 500-repository sample selected by the team.

Dataset source: https://github.com/shyamagarwal13/specmine-official

The sample is curated rather than random, so results will be interpreted within its coverage. The final number of specifications and repositories retained for analysis will be reported after loading and filtering.

## Candidate Explanatory Variables

We will consider the following groups of variables where the selected data supports them:

- Document structure and content, such as length, headings, and requirement-related features.
- Specification revision activity, such as commit counts and revision timing.
- Repository context, such as age, activity, and popularity.
- Contributor context, such as participation in the available specification history.
- Tool family and artifact lifecycle role.

The final variable selection will depend on field availability, data quality, and the team's implemented analysis.

## Outcomes and Measurement

The planned outcomes are specification abandonment, unfilled placeholders, and incomplete tasks.

Placeholder flags and unchecked task measures are candidate indicators of unfinished content. The team will define abandonment separately, including the observation period, any inactivity threshold, and how completed or stable specifications are distinguished from abandoned ones.

For checkbox-based measures, unchecked count will be calculated as total checkboxes minus checked checkboxes. The unchecked proportion will be undefined when no checkboxes are present. Missing data will not automatically be treated as zero or as evidence of completion.

An outcome indicator will not also be used as a predictor of that same outcome. Any predictive analysis will require explanatory variables measured before the outcome period. If the available data cannot support that ordering, findings will be described as associations.

## Current Status

The research framing is drafted, and the team has selected the SpecMine v1.1 500-repository sample.

Final abandonment rules, retained sample counts, and analysis variables will be aligned with the team's operational definition and loading results. No results or validated abandonment labels are claimed at this stage.
