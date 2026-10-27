# SpecMine Abandonment Analysis

CSC 580 research project investigating specification abandonment in the SpecMine dataset.

The project includes data loading, feature preparation, exploratory analysis, a reproducible completion-review experiment, and retrospective abandonment screening.

## Documentation

| Component | Guide |
|---|---|
| Data loading and feature pipeline | [Data and feature pipeline](src/README.md) |
| Data quality and exploratory analysis | [Exploratory analysis](README_EDA.md) |
| Completion-review experiment | [Reproduction guide](reproducibility/README.md) |
| Abandonment screening and evaluation | [Screening guide](docs/SCREENING_README.md) |

The completion-review reproduction guide documents the raw dataset snapshot, preserved annotation decisions, required scripts, expected outputs, and report-generation steps.

## Run the abandonment screening pipeline

Follow the environment and dataset setup instructions in the reproduction and screening guides first.

From the repository root, run this command in PowerShell:

    .\.venv-completion\Scripts\python.exe src/run_abandonment_pipeline.py --data-dir "data/specmine-official/data" --output-dir "results/abandonment_full_check_01" --labels "docs/reviewed_labels.json" --stale-days 90

Use a new output directory for each run.

This command prepares the raw sample, applies screening rules, evaluates the supplied review labels, and generates reports. Prepared data is written under `stage1/`; screening results and evaluation reports are written under `screening/`.

The source sample revision is:

    9fbb61541046cb2fb770fa944192a3fc0b64a9b1

## Verified run and preliminary findings

The complete raw-data run processed 28,583 specification records across 415 repositories and reproduced the earlier screening and evaluation results.

- The broader candidate rule flagged 742 records.
- The explicit-discontinuation baseline flagged 12 records.
- Eight cases were reviewed: four flagged and four unflagged.
- Six cases were resolved as completed; two remained unclear.
- On the six resolved cases, the broader rule produced two false positives and four true negatives.
- The baseline flagged none of the six resolved cases.
- No confirmed abandoned cases were present, so recall could not be estimated.
- All seven screening tests passed.

These results describe a small reviewed subset, not population-wide detector performance. The current implementation supports maintainer review; screening flags are not confirmed abandonment decisions.

Predictive modeling remains unsupported by the available verified outcome labels and temporal evidence. This does not establish that repository features lack predictive power.

## Review records

`docs/reviewed_labels.json` contains the eight-case evaluation labels.

`docs/targeted_validation_labels.json` records a separate development review of a reusable template that triggered the stale-content rule. That case is excluded from the eight-case evaluation and is not automatically loaded by the command above.

The evaluation used E01–E04 and E16–E19 from the original review sample. Review capacity reduced the planned sample after review had begun. Unclear cases were retained and excluded from classification metrics.

## Run the screening tests

    .\.venv-completion\Scripts\python.exe -m unittest discover -s tests -p "test_abandonment_screen.py" -v

## Version control

Source code, tests, documentation, review samples, and human-reviewed labels are committed.

Downloaded raw data, virtual environments, and reproducible generated result directories are excluded. See the component guides for reproduction instructions.