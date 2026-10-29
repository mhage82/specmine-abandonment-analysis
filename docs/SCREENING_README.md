# SpecMine retrospective screening add-on

## First run using your existing reproduction

From the project root in PowerShell:

```powershell
.\.venv-completion\Scripts\python.exe src/run_abandonment_pipeline.py --stage1-dir "results/completion_reproduction_01/stage1" --output-dir "results/abandonment_screen_01"
```

The wrapper runs screening, evaluation handling and reporting. Because no independent labels are supplied on the first run, evaluation explicitly reports not evaluated.

To include raw preparation in one command, use --data-dir "data/specmine-official/data" instead of --stage1-dir. This invokes your existing completion_stage1_prepare.py; the other completion experiment scripts are not modified or replayed.

## Rules, version screen-v1

Baseline: an explicit abandoned/cancelled/canceled/discontinued scalar status in the specification's opening frontmatter or supplied supplemental metadata.

Candidate rule: baseline OR at least 90 days without a recorded specification edit combined with unchecked specification checkboxes or an unfilled placeholder. Suppress candidate flags when statuses conflict, a completed status is present, or explicit supersession is recorded. Conflicts still enter the review queue. These are hypotheses for screening, not validated outcome definitions. Ninety days is configurable, not an empirically optimized threshold. Supersession detection from reasons is a literal keyword rule and can miss alternatives or mishandle negation; evaluate its errors.

No unrestricted keyword search is used to interpret arbitrary prose as a status. The frontmatter extractor deliberately accepts only a simple top-level scalar status. It is not a complete YAML parser. Unsupported forms remain undetected. Dates missing, invalid, or later than history collection cannot establish inactivity. Content-feature checkboxes describe the specification, not its linked tasks. Snapshot content and commit history may have different collection times: this is retrospective screening, never a temporally aligned predictive feature set.

## Outputs under screening/

- screening_all.csv: every record, indicators, flags, category, and separate reviewed outcome.
- review_queue.csv: candidates and status conflicts requiring human inspection.
- review_sample.json: deterministic samples of up to 15 flagged and 15 unflagged records, excluding supplied reviewed IDs. These sizes are configurable in abandonment_screen.py. Sampling is by record, not independent feature scope; inspect duplicates/shared scopes and repository clustering.
- evaluation.json: baseline and candidate confusion counts and metrics on resolved evaluation cases, or an explicit no-label status.
- report.md: summary, metrics and limitations.
- manifest.json: input, script and output hashes, configuration and counts.

## Review annotations

Copy review_sample.json to a separate reviewed_labels.json. Fill outcome, reviewer, reviewed_at, evidence_ref and rationale for each reviewed case. Remove unreviewed entries from the supplied file; preserve your original sample list separately. Outcome choices: abandoned, not_abandoned, completed, superseded, unclear, ineligible. Use not_abandoned only with affirmative reviewed evidence under your protocol, never for mere absence of a flag. Preserve unknown as unclear. Date format: YYYY-MM-DD. Use split=development for all cases used in rule design, including our prior walkthroughs; use split=evaluation only for independently assessed evaluation cases. No reviews or reviewer signatures are prefilled.

Do not change rules in response to evaluation results and then claim the same sample is held out. Review evidence independently of detector predictions where practical. Report unresolved cases and sampling limitations. Population recall is not established by this sample. Precision/recall/F1 emitted here are unweighted and conditional on the supplied resolved cases, not estimates for the whole population. A positive-reference-free sample cannot establish sensitivity.

Rerun with a fresh output directory:

```powershell
.\.venv-completion\Scripts\python.exe src/run_abandonment_pipeline.py --stage1-dir "results/completion_reproduction_01/stage1" --labels "docs/reviewed_labels.json" --output-dir "results/abandonment_screen_02"
```

## Supplemental evidence

The table alone does not contain sibling metadata.json. Optionally provide --evidence docs/supplemental_evidence.json containing a JSON array with file_url_sha16, source_status, source_reason and evidence_ref for each record. Capture evidence at an identified revision and cite it. These are source observations, not adjudicated labels. Do not copy final evaluation judgments into detector evidence. The script does not fetch metadata automatically; absence of supplemental evidence is not absence of a conflicting status or successor.

## Tests

```powershell
.\.venv-completion\Scripts\python.exe -m unittest discover -s tests -p "test_abandonment_screen.py" -v
```

Tests cover false keyword matches, conflicts, supersession, missing dates/counts, unknown labels, development/evaluation separation, metric arithmetic, and the CLI-stage outputs on a synthetic Parquet fixture. Synthetic tests validate implementation behavior, not real-world detection accuracy.

## Integration and remaining work

This is an additive runnable screening/evaluation stage, not a trained predictive model. It does not certify birth/path lineage or generate predictive eligibility windows. Reuse the preserved temporal experiment for that separate feasibility investigation. Existing stages cannot accept superseded as a manual_status without modification, so the new label schema remains separate.

To finish the research deliverable: run on your real stage-one table, freeze rules and evaluation sampling, complete independent review, rerun evaluation, inspect false positives/negatives and unresolved cases, and write the decision rationale. No failed prediction performance is claimed: reliable prospective labels/history have not yet been established.
