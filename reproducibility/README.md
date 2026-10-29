# Reproducing the completion experiment

Run these instructions in **Windows PowerShell**, from the project repository. They reproduce the consolidated Parquets, review samples, saved annotations, cutoff datasets and status review queues. The optional final step rebuilds the four-page report.

The replay restores the original **AI-assisted annotation decisions**. Those decisions are inputs to the experiment: the scripts do not independently repeat the evidence review, confirm the labels with a human, or train a model. Once the source data and Python dependencies are present, the experiment replay runs locally without GitHub/API credentials.

## 1. Files to preserve and commit

Keep the directory structure shown below. Commit the experiment scripts, tests, annotation bundle, dependency files, `.gitattributes`, `.gitignore` and this guide. Keep the original project files as well.

```text
specmine-abandonment-analysis/
  .gitattributes
  .gitignore
  src/
    completion_reproduce.py
    completion_stage1_prepare.py
    completion_stage2_candidates.py
    completion_stage3_review_all.py
    completion_stage4_include_archived.py
    completion_apply_annotations.py
    completion_summarize_review.py
    completion_verify_expansion.py
    completion_stage5_cutoff.py
    completion_verify_cutoff.py
    completion_stage6_status.py
  tests/
    test_completion_stage1.py
    test_completion_exploration.py
    test_completion_cutoff.py
    test_completion_status.py
  reproducibility/
    README.md
    requirements-completion.txt
    completion_annotations/
      manifest.json
      decisions/
        <file_url_sha16>.json   (564 saved decisions)
```

`manifest.json` preserves cohort membership, original labels/counts and SHA-256 hashes for the source data, scripts and decisions. Commit **the entire `completion_annotations` folder**. Saving only the scripts or the manifest is insufficient to reproduce the labels. `.gitattributes` preserves the file-byte conventions used by the hash checks across Git checkouts.

For the report, also preserve:

```text
requirements-report.txt
src/completion_build_report.py
src/completion_render_report.py
reports/specmine_experiment_report.json
```

The generated DOCX, HTML, PDF and `reports/report_verification.json` can also be committed as deliverables. Keep `ROUND_2_LOG.md` and the `COMPLETION_*.md` / `CUTOFF_STATUS_EXPERIMENT.md` method notes with the project.

The raw SpecMine clone, virtual environment and generated experiment results are separate from the small replay bundle. Do not rely on Git-ignored results to preserve the annotations. For a later audit of the original evidence review, separately back up downloaded public evidence caches from the original experiment; these caches are not included in the decision bundle or recreated by the replay.

## 2. Open the repository and prepare Python

Git and Python 3.13 must be installed. The verified run used **Python 3.13.2**, NumPy 2.5.3, pandas 2.3.3 and PyArrow 23.0.1.

For your current checkout:

```powershell
Set-Location 'C:\Users\moham\workspace\21_ML\CSC580\round_2\specmine-abandonment-analysis'
```

For a different checkout, change that path to its repository root. Create the environment once:

```powershell
py -3.13 -m venv .venv-completion
$specminePython = '.\.venv-completion\Scripts\python.exe'
& $specminePython -m pip install -r reproducibility/requirements-completion.txt
& $specminePython --version
```

On later runs, reuse the environment and set `$specminePython` again in each new PowerShell session. Calling its Python executable directly avoids needing to activate the environment or change PowerShell execution policy.

Use **`reproducibility/requirements-completion.txt`** for this replay. The older root-level `requirements-completion.txt` contains the initial stage dependencies but does not pin NumPy; the replay dependency file pins all three numerical packages used in the verified run. The report dependency is installed separately in step 7.

If the launcher reports that Python 3.13 is unavailable, install that version, or use the full path to an existing Python 3.13 executable in place of `py -3.13` to create the environment.

On your current computer, the existing Python 3.13.2 installation can create the same environment with this alternative command. Run this **instead of** the `py -3.13 -m venv` line, then continue with `$specminePython` and the dependency installation above:

```powershell
& 'C:\Users\moham\AppData\Local\Programs\Python\Python313\python.exe' -m venv .venv-completion
```

## 3. Restore the exact raw dataset

The original experiment used the GitHub SpecMine sample, pinned to commit:

```text
9fbb61541046cb2fb770fa944192a3fc0b64a9b1
```

If `data/raw/specmine-official` does not exist, clone it:

```powershell
git clone https://github.com/shyamagarwal13/specmine-official.git data/raw/specmine-official
```

For a new clone or an existing source clone, select and confirm the pinned snapshot:

```powershell
git -C data/raw/specmine-official checkout --detach 9fbb61541046cb2fb770fa944192a3fc0b64a9b1
git -C data/raw/specmine-official rev-parse HEAD
```

The second command should print the commit above. The replay also verifies the contents of all nine required raw inputs, so a matching repository name alone is insufficient.

Required layout:

```text
data/raw/specmine-official/
  specs.jsonl.gz
  data/
    spec_files.parquet
    spec_content_features.parquet
    spec_file_commits.parquet
    spec_links.parquet
    openspec_artifact_files.parquet
    pull_requests.parquet
    pr_files.parquet
    openspec_code_refs.parquet
```

**`specs.jsonl.gz` belongs one directory above `data/`.** Keep it compressed. It supplies the specification Markdown. The other inputs provide specification records/features, specification-file commits, task/artifact links, task text, PR leads and code references. The Kiro tables and the full Hugging Face mirror are not inputs to this exact experiment.

If your source clone is elsewhere, add `--data-dir 'C:\path\to\specmine-official\data'` to the replay command. Its `specs.jsonl.gz` must still be in that directory's parent.

## 4. Run the entire experiment

Choose a new output folder for each run. This timestamped folder stays under the Git-ignored reproduction directory:

```powershell
$runDir = Join-Path 'results/completion_reproduction' ('run_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
& $specminePython src/completion_reproduce.py --output-root $runDir
if ($LASTEXITCODE -ne 0) { throw 'Replay failed; inspect the terminal error and reproduction.log if created.' }
```

Keep `$runDir` in the same PowerShell session for the following commands. If you reopen PowerShell, set it to the actual output folder you want to inspect.

The wrapper checks the script, raw-input and decision hashes before creating outputs. It then runs **13 commands** using the same Python interpreter. The terminal shows each command number; detailed output is written to `reproduction.log`.

You do not need to execute the individual stages separately when using the wrapper. It supplies the correct input/output paths and restores each cohort's saved decisions before applying them. Running the stage scripts without these arguments uses their original `results/completion_exploration/` defaults instead.

The wrapper's default output, if `--output-root` is omitted, is `results/completion_reproduction/`. That directory already exists in the current working repository. Use the explicit fresh subfolder above for repeat runs; an existing output folder is deliberately rejected, even after a partial failed run.

## 5. Verify the run

Run the completion tests:

```powershell
& $specminePython -m unittest discover -s tests -p 'test_completion*.py' -q
if ($LASTEXITCODE -ne 0) { throw 'Completion tests failed.' }
```

The preserved version has **54 tests**. Inspect the replay's verification record:

```powershell
$verificationPath = Join-Path $runDir 'reproduction_verification.json'
$verification = Get-Content -LiteralPath $verificationPath -Raw | ConvertFrom-Json
$verification.successful_script_commands
$verification.cutoff_counts_match
$verification.cutoff_status_counts_match
$verification.cohort_checks | ConvertTo-Json -Depth 6
```

Expected results are `13`, `True`, `True`, plus these cohort counts:

| Review output | Records | Completed | Unclear |
|---|---:|---:|---:|
| `stage2` | 10 | 7 | 3 |
| `all140` | 140 | 69 | 71 |
| `all564` | 564 | 305 | 259 |

Each cohort should report `identifiers_order_and_all_manual_fields_match: true` and `csv_bytes_match_original: true`. The verified original replay produced byte-identical review CSVs. Other artifacts contain run paths, times or generated metadata, so the workflow also checks their data values and provenance rather than promising every output file will be byte-identical.

| Cutoff in days | Observed windows | Retained spec/commit rows | Completed before cutoff | Baseline-review queue |
|---|---:|---:|---:|---:|
| 7 | 561 | 814 | 77 | 486 |
| 14 | 560 | 898 | 82 | 480 |
| 30 | 552 | 1,028 | 86 | 473 |
| 60 | 410 | 1,249 | 86 | 361 |
| 90 | 368 | 1,304 | 86 | 332 |

`commands.json` saves the exact argument list and exit code of every subprocess. To inspect it or the detailed log:

```powershell
Get-Content -LiteralPath (Join-Path $runDir 'commands.json') -Raw
Get-Content -LiteralPath (Join-Path $runDir 'reproduction.log') -Tail 60
```

These checks establish reproducibility and implementation consistency. Human confirmation of labels and evaluation of a predictive model are separate work.

## 6. Scripts executed and files to open

All script names below are under `src/`. The command numbers correspond to `commands.json`.

| Command | Script | What it does |
|---|---|---|
| 1 | `completion_stage1_prepare.py` | Builds the consolidated specification Parquet and separate history, task, reference, PR and code-evidence tables. |
| 2 | `completion_stage2_candidates.py` | Finds 140 non-archived candidates with at least two specification commits and fully checked linked task lists; selects a ten-record pilot with seed 42. |
| 3 | `completion_apply_annotations.py` | Applies the saved pilot decisions restored by the wrapper. |
| 4 | `completion_stage3_review_all.py` | Prepares review of all 140 candidates and carries forward the pilot decisions. |
| 5 | `completion_apply_annotations.py` | Applies the saved decisions for all 140 records. |
| 6 | `completion_summarize_review.py` | Exports the annotated 140-record Parquet and summaries. |
| 7 | `completion_stage4_include_archived.py` | Expands to 564 records, admitting archived paths and carrying forward earlier decisions. |
| 8 | `completion_apply_annotations.py` | Applies the saved decisions for all 564 records. |
| 9 | `completion_summarize_review.py` | Exports the annotated 564-record Parquet and summaries. |
| 10 | `completion_verify_expansion.py` | Checks population coverage, annotation agreement, preserved prior decisions and provenance. |
| 11 | `completion_stage5_cutoff.py` | Recomputes 12 specification-commit predictors using only history through days 7, 14, 30, 60 and 90; preserves the outcome labels. |
| 12 | `completion_verify_cutoff.py` | Independently checks cutoff history, features, labels and source/output provenance. |
| 13 | `completion_stage6_status.py` | Adds supported completion-at-cutoff metadata and creates baseline-review queues. |

`completion_reproduce.py` orchestrates these calls and performs the final comparison against the preserved experiment. Keep these scripts together in `src/`: some stages import shared functions from the other completion scripts. This workflow does not require running the original `feature_pipeline.py` or the earlier abandonment-labeler experiments.

The following paths are **relative to `$runDir`**:

| File or folder | What to use it for |
|---|---|
| `stage1/specifications.parquet` | Consolidated full-history base: 28,583 rows and 174 columns. |
| `stage1/spec_history.parquet` | Recorded specification-file commits. |
| `stage1/task_documents.parquet`, `task_links.parquet`, `spec_references.parquet`, `spec_pr_evidence.parquet`, `artifact_code_refs.parquet` | Separate related-evidence tables, all in `stage1/`. |
| `stage2/completion_candidates.parquet` | The 140 initial candidates before outcome annotation. |
| `stage2/completion_review.csv` | The ten-record pilot with its restored review fields. |
| `all140/completion_review_annotated.parquet` | Annotated non-archived cohort. |
| `all564/review_population.parquet` | Expanded selection metadata before joining the manual review fields. |
| `all564/completion_review.csv` | All 564 records and saved review decisions; convenient for inspection in Excel. |
| `all564/completion_review_annotated.parquet` | Selected population metadata joined with the review fields. |
| `all564/REVIEW_GUIDE.md`, `review_packets/`, `ANNOTATION_INDEX.md`, `annotation_evidence/` | Review instructions, per-record evidence packets, annotation index and restored decision JSONs; all under `all564/`. |
| `cutoff/day_007/cutoff_dataset.parquet` | All 564 records with labels and predictors computed through day 7. |
| `cutoff/day_007/cutoff_history.parquet` | The bounded specification history used for the day-7 predictors. |
| `cutoff/feature_contract.json` | Explicit list of the 12 columns permitted as predictor inputs. |
| `cutoff_status/day_007/cutoff_dataset.parquet` | Latest day-7 master: 564 rows, 26 columns, including status metadata. |
| `cutoff_status/day_007/needs_baseline_review.csv` | Records requiring baseline-state review before considering training eligibility. |
| `cutoff/cutoff_comparison.csv`, `cutoff_status/cutoff_status_summary.csv` | Comparisons across all five observation windows. |
| `commands.json`, `reproduction.log`, `reproduction_verification.json` | Exact execution record and final checks. |

The cutoff directories also contain `day_014`, `day_030`, `day_060` and `day_090`, with matching CSV/Parquet exports. For 90 days, open `cutoff_status/day_090/cutoff_dataset.parquet`.

The cutoff master is preparation for later modeling. `unclear` is not a confirmed negative label; `window_observed` is collection coverage, not proof of active work. Use only the predictor list in `feature_contract.json` as model inputs. The current data still require resolved outcomes and verified baseline states before a defensible forecasting evaluation.

## 7. Rebuild the report, if needed

The report uses the saved text in `reports/specmine_experiment_report.json`. Replaying the data does not automatically rewrite that narrative. If you intentionally change the experiment, review its counts and interpretation before rebuilding the report.

From the repository root:

```powershell
& $specminePython -m pip install -r requirements-report.txt
& $specminePython src/completion_build_report.py
if ($LASTEXITCODE -ne 0) { throw 'Report build failed.' }
& $specminePython src/completion_render_report.py
if ($LASTEXITCODE -ne 0) { throw 'Report PDF rendering or layout verification failed.' }
```

The first script generates `reports/SpecMine_Experiment_Report.docx` and `.html`. The renderer requires installed Chrome or Edge; it renders the local HTML with a separate temporary profile, writes `reports/SpecMine_Experiment_Report.pdf`, and verifies exactly four PDF pages and no content overflow. `reports/report_verification.json` records the checks. If the browser is installed outside the detected locations, supply its full executable path using `--browser`.

Unlike the experiment replay, these report commands rebuild the same named report files. DOCX is the editable counterpart; the PDF is the independently verified four-page version. Word is not required for this rendering path.

## 8. Common problems

| Message or situation | What to do |
|---|---|
| `Output root already exists` | Choose another new `$runDir`; keep the existing results. |
| `Missing or different raw snapshot input` | Check the pinned source commit, all nine required files, `--data-dir`, and the location of `specs.jsonl.gz`. |
| `Experiment script differs from the preserved version` | Use the committed experiment version matching the manifest. Check that `.gitattributes` was included and script line endings were preserved. An intentional code change is a new experiment version, not an exact replay of this one. |
| `Preserved annotation bytes changed` or a missing decision JSON | Restore the original bundle for exact replay. Keep revised human decisions as a separately versioned review rather than editing the preserved bundle in place. |
| A stage exits with an error | Read `reproduction.log` and `commands.json` in that run folder; fix the cause and retry with a fresh destination. |
| A dependency is missing | Confirm `$specminePython` points to the environment where the replay requirements were installed. |

The last verified replay passed all 13 commands, preserved the three annotation CSVs byte for byte, and matched the cutoff/status summaries. The completion test suite passed all 54 tests. The full record of that run is in the existing `results/completion_reproduction/` directory; each new run writes its own evidence under the chosen destination.
