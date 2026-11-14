# SpecMine Abandonment Analysis

CSC 580 research project investigating specification abandonment in the SpecMine dataset.

The project includes data loading, feature preparation, exploratory analysis, a reproducible completion-review experiment, 
and retrospective abandonment screening.

## Documentation

| Component                                                              | Guide                                                                           |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Data loading and feature pipeline                                      | [Data and feature pipeline](src/README.md)                                      |
| Data quality and exploratory analysis                                  | [Exploratory analysis](README_EDA.md)                                           |
| Completion-review experiment                                           | [Reproduction guide](reproducibility/README.md)                                 |
| Abandonment screening and evaluation                                   | [Screening guide](docs/SCREENING_README.md)                                     |
| Preliminary result figures                                             | [Figure generation guide](docs/FIGURES_README.md)                               |
| Sensitivity and error analysis             | [Sensitivity analysis and existing-case comparison](docs/SENSITIVITY_README.md) |

The completion-review reproduction guide documents the raw dataset snapshot, preserved annotation decisions, 
required scripts, expected outputs, and report-generation steps.

## Run the abandonment screening pipeline

### First-time setup

Install Python 3.13 and Git. Open a terminal in the repository root.

Create the project environment:

```powershell
py -3.13 -m venv .venv-completion
```

Install the screening, completion-preparation, and figure dependencies:

```powershell
.\.venv-completion\Scripts\python.exe -m pip install -r reproducibility/requirements-completion.txt -r requirements-figures.txt
```

If the sample has not already been downloaded:

```powershell
git clone https://github.com/shyamagarwal13/specmine-official.git data/specmine-official
git -C data/specmine-official checkout 9fbb61541046cb2fb770fa944192a3fc0b64a9b1
```

The command below starts from the raw dataset. A prior completion-experiment run is not required. 
Saved evaluation labels are already included in `docs/reviewed_labels.json`; reproducing the 
reported results does not require new manual reviews.

The loader/feature and EDA workflows have their own dependency instructions in the linked guides.

From the repository root, run this command in PowerShell:
    .\.venv-completion\Scripts\python.exe src/run_abandonment_pipeline.py --data-dir "data/specmine-official/data" --output-dir "results/abandonment_full_check_01" --labels "docs/reviewed_labels.json" --stale-days 90

Use a new output directory for each run.

This command prepares the raw sample, applies screening rules, evaluates the supplied review labels, 
and generates reports. Prepared data is written under `stage1/`; screening results and evaluation 
reports are written under `screening/`.

The source sample revision is:
    9fbb61541046cb2fb770fa944192a3fc0b64a9b1

## Reproduce the sensitivity analysis

After the abandonment screening command above completes, run the following command from the repository root:

```powershell
.\.venv-completion\Scripts\python.exe src/run_abandonment_sensitivity.py --stage1-dir results/abandonment_full_check_01/stage1 --labels docs/reviewed_labels.json --output-dir results/abandonment_sensitivity_01
```

This reuses the prepared data from the previous run. It evaluates 30-, 60-, 90-, and 180-day inactivity thresholds using identical screening rules and the same saved review labels. No additional manual reviews are required.

The output directory must not already exist. Do not create it manually. For subsequent runs, choose a new output directory name.

### Expected results

| Inactivity threshold | Candidate records | Percentage of dataset | Explicit-status baseline |
| --- | ---: | ---: | ---: |
| 30 days | 1,784 | 6.24% | 12 |
| 60 days | 1,128 | 3.95% | 12 |
| 90 days | 742 | 2.60% | 12 |
| 180 days | 128 | 0.45% | 12 |

Each run processes 28,583 specification records across 415 repositories.

### Generated outputs

The following files are written to `results/abandonment_sensitivity_01/`:

- `sensitivity_summary.csv` and `sensitivity_summary.json`: candidate counts, percentages, changes relative to 90 days, and reviewed-case evaluation metrics.
- `threshold_comparison.png` and `threshold_comparison.pdf`: the threshold-comparison figure.
- `reviewed_case_comparison.csv`: the same eight reviewed cases evaluated across all four thresholds, including their saved evidence and rationales.
- `captions.md` and `report.md`: figure caption, results summary, and interpretation limits.
- `sensitivity_manifest.json`: input, script, and output hashes, execution commands, and software versions.
- `days_30/`, `days_60/`, `days_90/`, and `days_180/`: individual screening runs.
- `days_*.log`: execution logs for each threshold.

These results measure how inactivity thresholds affect screening volume. They do not establish confirmed abandonment rates or an optimal threshold. Recall remains undefined because the resolved evaluation subset contains no confirmed abandoned cases. The 32 rows in the case-comparison file represent eight cases across four thresholds, not 32 independent reviews.

For additional details and test commands, see the [sensitivity analysis guide](docs/SENSITIVITY_README.md).


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
