# SpecMine Specification Abandonment Analysis

## Selected Research Topic

This project investigates specification abandonment in open-source software repositories represented in the SpecMine dataset. The study focuses on identifying observable characteristics associated with specifications that appear to be abandoned, contain unresolved placeholders, or retain incomplete tasks.

## Research Question

**What predicts that a software specification will be abandoned, left with placeholders, or left with incomplete tasks?**

## Motivation

Software specifications are intended to guide development by documenting expected behavior, requirements, and implementation plans. However, some specifications are created and later receive little or no additional attention. Others continue to contain TODO comments, placeholder text, unresolved tasks, or incomplete sections.

Understanding these patterns may help researchers and software teams identify specifications that are at risk of becoming outdated or unfinished. This is especially important because an abandoned specification can create confusion about whether its requirements are still valid, whether its associated implementation was completed, or whether the planned work was discontinued.

The SpecMine dataset provides an opportunity to examine these patterns across a large collection of specification artifacts and repositories rather than relying on a small number of manually selected projects.

## Expected Contribution

The expected contribution of this project is a reproducible analysis of observable factors associated with possible specification abandonment. The project will:

1. Develop measurable indicators for potential specification abandonment.
2. Keep placeholders and incomplete tasks separate from abandonment rather than treating them as identical conditions.
3. Examine whether specification structure, revision history, repository activity, tool family, and contributor-related characteristics are associated with the observed outcomes.
4. Compare multiple inactivity thresholds to determine whether conclusions remain consistent under different definitions of abandonment.
5. Produce a baseline predictive analysis that can be reproduced and evaluated by other researchers.

The analysis will identify associations and predictive patterns. It will not claim to determine a developer’s intent or prove that any factor directly caused a specification to be abandoned.

## Competing or Simpler Explanations

Several alternative explanations must be considered before a specification is classified as potentially abandoned:

- A specification may be complete and therefore no longer require changes.
- A repository may have become inactive as a whole.
- Development may have moved to another branch, repository, document, or tracking system.
- A specification may have been replaced by a newer artifact.
- A TODO or placeholder may be intentionally retained for future work.
- A recently created specification may not have had enough time to receive additional revisions.
- Different specification tools may use placeholders or task markers differently.
- Missing history or incomplete metadata may make an active specification appear inactive.

These explanations will be addressed by using repository context, revision history, multiple inactivity thresholds, and an unknown or right-censored category for records that do not contain enough follow-up history.

## Unit of Analysis

The unit of analysis is an individual specification artifact represented in the SpecMine dataset.

Each specification will be analyzed using available information about the artifact itself, its revision history, and the repository in which it appears. Repository-level information may be used as context, but the primary observation remains the individual specification artifact.

## Population

The target population consists of software specification artifacts created in open-source repositories that use specification-oriented development practices.

The accessible population for this project consists of specification artifacts included in the official SpecMine dataset.

## Sprint 1 Sample

The study sample will include SpecMine records that can be loaded through the project’s documented data pipeline and contain the minimum information required for the analysis.

A record must contain enough information to identify the specification and evaluate the selected predictors or outcomes. Records with insufficient observation time will not automatically be classified as abandoned. They will be retained as right-censored or unknown when appropriate.

The final sample size will be recorded after the dataset loader is completed and the inclusion rules are applied.

## Predictor Variables

The proposed predictor groups are:

### Specification Structure

- Specification length or size
- Number of sections or structured components
- Presence of empty or incomplete sections
- Presence of TODO markers
- Presence of placeholder text
- Presence of unresolved task indicators

### Revision Activity

- Number of revisions
- Time between revisions
- Time since the most recent revision
- Frequency of changes
- Age of the specification

### Repository Activity and Maturity

- Repository age
- Commit activity
- Contributor activity
- Whether repository development continued after specification activity stopped
- Other available repository-level activity measures

### Tool Family

- Specification tool or framework associated with the artifact
- Differences in patterns across supported tool families

### Contributor or Team Context

- Number of contributors associated with the repository
- Number of contributors associated with the specification, when available
- Other non-identifying team-level measures available in the dataset

Only information available at or before the selected outcome cutoff will be used as a predictor. Information created after the outcome will be excluded to prevent data leakage.

## Outcome Measures

The project will examine related but distinct outcomes.

### Potential Specification Abandonment

A specification may be classified as potentially abandoned when observable evidence indicates unfinished work and the artifact receives no meaningful revision for a defined period while sufficient repository history remains available.

Candidate inactivity thresholds of 30, 60, 90, and 180 days will be evaluated where the available history permits. The final primary threshold will be documented and compared with alternative thresholds through sensitivity analysis.

### Placeholders

The presence of placeholder text will be recorded separately. A placeholder alone will not automatically prove that a specification was abandoned.

### Incomplete Tasks

The presence of TODO markers, unresolved checklist items, or similar unfinished-task indicators will also be recorded separately. An incomplete task alone will not automatically prove abandonment.

### Unknown or Right-Censored Outcome

A specification will be categorized as unknown or right-censored when the available history does not provide enough follow-up time to determine whether it became inactive under the selected threshold.

## Assumptions and Scope

This study is based on observable repository and specification data. It cannot directly determine why a developer stopped modifying a specification.

The analysis therefore uses the term **potential abandonment** for classifications inferred from inactivity and unfinished-work indicators. Results will be reported as associations or predictions rather than causal conclusions.

The project is limited to the information available in SpecMine and its associated metadata. Findings may not generalize to private repositories, repositories not represented in the dataset, or specification practices that are not captured by SpecMine.

## Sprint 1 Decisions Still Requiring Dataset Verification

The following items must be confirmed after the official dataset is loaded:

- Exact sample size
- Exact
