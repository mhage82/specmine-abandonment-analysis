"""Add supported cutoff-status flags without treating quiet specs as inactive.

The saved judgments can establish prior completion of the reviewed scope. They
cannot establish that every other specification was actively being implemented.
Unknown stays unknown, and the full cutoff cohort is preserved.
"""

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


KEY = "file_url_sha16"
STATUS_COLUMNS = ["status_at_cutoff", "completed_by_cutoff", "has_recent_spec_commit",
                  "cutoff_status_reason", "cutoff_status_evidence_date",
                  "cutoff_status_evidence_url", "training_row_action"]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8")


def require_table(frame, required, name):
    if not set(required).issubset(frame.columns):
        raise ValueError(f"{name} is missing required columns: {sorted(set(required) - set(frame.columns))}")
    if (frame.empty or frame[KEY].isna().any() or frame[KEY].eq("").any()
            or frame[KEY].duplicated().any()):
        raise ValueError(f"{name} requires nonempty unique identifiers")


def add_cutoff_status(dataset, audit, review):
    """Preserve every input row/value and add evidence-based review metadata.

    A dated completion is an upper bound on first completion, not a full state
    history. This concerns first delivery of the reviewed scope, not later use,
    maintenance, or reopened work. No current-active/inactive flag is inferred.
    """
    require_table(dataset, [KEY, "manual_status", "prediction_at", "window_observed",
                            "prefix_commits_last_7_days"], "dataset")
    require_table(audit, [KEY], "audit")
    require_table(review, [KEY, "manual_status", "manual_outcome_date", "manual_evidence_url"], "review")
    ids = set(dataset[KEY])
    if ids != set(audit[KEY]) or ids != set(review[KEY]):
        raise ValueError("Dataset/audit/review identifiers disagree")
    if set(STATUS_COLUMNS) & set(dataset.columns):
        raise ValueError("Input already contains cutoff status fields; use the original stage-5 dataset")
    allowed = {"completed", "abandoned", "in_progress", "deferred", "unclear"}
    if not set(review.manual_status).issubset(allowed):
        raise ValueError("Unrecognized manual_status")
    aligned = review.set_index(KEY).loc[dataset[KEY]].reset_index()
    if dataset.manual_status.tolist() != aligned.manual_status.tolist():
        raise ValueError("Dataset/review labels disagree")
    if "manual_status" in audit:
        if audit.set_index(KEY).loc[dataset[KEY], "manual_status"].tolist() != aligned.manual_status.tolist():
            raise ValueError("Audit/review labels disagree")
    dates = aligned.manual_outcome_date.fillna("").astype(str)
    nonempty = dates[dates.ne("")]
    if (not nonempty.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all()
            or pd.to_datetime(nonempty, format="%Y-%m-%d", errors="coerce").isna().any()):
        raise ValueError("Invalid manual_outcome_date; use YYYY-MM-DD or blank")
    cutoffs = pd.to_datetime(dataset.prediction_at, utc=True, format="mixed", errors="coerce")
    if cutoffs.isna().any():
        raise ValueError("Invalid prediction_at timestamp")
    if (not pd.api.types.is_bool_dtype(dataset.window_observed.dtype)
            or dataset.window_observed.isna().any()):
        raise ValueError("window_observed must contain non-null booleans")
    counts = pd.to_numeric(dataset.prefix_commits_last_7_days, errors="coerce")
    observed_counts = counts[dataset.window_observed]
    if (observed_counts.isna().any() or observed_counts.lt(0).any()
            or observed_counts.mod(1).ne(0).any()):
        raise ValueError("Observed recent-commit counts must be finite nonnegative integers")
    records = []
    for position, row in enumerate(aligned.to_dict("records")):
        cutoff = cutoffs.iloc[position]
        date = dates.iloc[position]
        complete_label = row["manual_status"] == "completed"
        before = bool(complete_label and date and pd.Timestamp(date).date() < cutoff.date())
        observed = bool(dataset.window_observed.iloc[position])
        if before:
            evidence_url = row["manual_evidence_url"]
            if not isinstance(evidence_url, str) or not evidence_url.strip():
                raise ValueError(f"Dated completed judgment lacks evidence URL: {row[KEY]}")
            if "manual_scope_match" in row and row["manual_scope_match"] != "yes":
                raise ValueError(f"Dated completed judgment lacks scope confirmation: {row[KEY]}")
            reason = "reviewed_scope_has_completion_evidence_before_cutoff_day"
        elif complete_label and not date:
            reason = "completed_in_full_review_but_completion_date_unknown"
        elif complete_label and pd.Timestamp(date).date() == cutoff.date():
            reason = "completion_evidence_on_cutoff_day_exact_time_unknown"
        elif complete_label:
            reason = "later_completion_evidence_does_not_establish_prior_in_progress_state"
        else:
            reason = "no_reviewed_dated_baseline_state_evidence"
        records.append({
            "status_at_cutoff": "completed" if before else "unknown",
            "completed_by_cutoff": True if before else pd.NA,
            "has_recent_spec_commit": bool(counts.iloc[position] > 0) if observed else pd.NA,
            "cutoff_status_reason": reason,
            "cutoff_status_evidence_date": date if before else "",
            "cutoff_status_evidence_url": row["manual_evidence_url"] if before else "",
            "training_row_action": "exclude_already_completed" if before else (
                "exclude_incomplete_window" if not observed else "needs_baseline_review"),
        })
    flags = pd.DataFrame(records, columns=STATUS_COLUMNS, index=dataset.index)
    for name in ["completed_by_cutoff", "has_recent_spec_commit"]:
        flags[name] = flags[name].astype("boolean")
    return pd.concat([dataset.copy(), flags], axis=1)


def status_summary(frame, days):
    completed = frame.status_at_cutoff.eq("completed")
    recent = frame.has_recent_spec_commit.fillna(False)
    return {
        "window_days": int(days), "rows": len(frame),
        "documented_completed_by_cutoff": int(completed.sum()),
        "unknown_status_at_cutoff": int((~completed).sum()),
        "verified_in_progress_at_cutoff": 0,
        "recent_spec_commit_yes": int(recent.sum()),
        "recent_spec_commit_no": int(frame.has_recent_spec_commit.eq(False).sum()),
        "recent_spec_commit_unknown": int(frame.has_recent_spec_commit.isna().sum()),
        "recent_edits_and_already_completed": int((recent & completed).sum()),
        "exclude_already_completed": int(frame.training_row_action.eq("exclude_already_completed").sum()),
        "exclude_incomplete_window": int(frame.training_row_action.eq("exclude_incomplete_window").sum()),
        "needs_baseline_review": int(frame.training_row_action.eq("needs_baseline_review").sum()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff-dir", type=Path, default=Path("results/completion_exploration/cutoff"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/completion_exploration/cutoff_status"))
    args = parser.parse_args()
    if args.cutoff_dir.resolve() == args.output_dir.resolve():
        raise ValueError("Preserve stage 5 by using a separate output directory")
    parent_path = args.cutoff_dir / "manifest.json"
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    review_path = Path(parent["input_paths"]["review_csv"])
    if sha256(review_path) != parent["input_sha256"]["review_csv"]:
        raise ValueError("Review changed since stage-5 export")
    input_paths = {"parent_manifest": parent_path, "review_csv": review_path}
    for relative, expected in parent["outputs_sha256"].items():
        path = args.cutoff_dir / relative
        if not path.resolve().is_relative_to(args.cutoff_dir.resolve()):
            raise ValueError("Parent output path escapes cutoff directory")
        if sha256(path) != expected:
            raise ValueError(f"Parent artifact changed: {relative}")
        input_paths[relative] = path
    input_hashes = {name: sha256(path) for name, path in input_paths.items()}
    existing_path = args.output_dir / "manifest.json"
    if existing_path.exists():
        existing = json.loads(existing_path.read_text(encoding="utf-8"))
        if existing["input_sha256"] != input_hashes:
            raise ValueError("Use a fresh output directory for changed inputs")
    review = pd.read_csv(review_path, dtype=str, keep_default_na=False)
    days_list = parent["configuration"]["windows"]
    primary = parent["configuration"]["primary_days"]
    products = {}
    for days in days_list:
        folder = args.cutoff_dir / f"day_{days:03d}"
        dataset = pd.read_parquet(folder / "cutoff_dataset.parquet")
        audit = pd.read_parquet(folder / "eligibility_audit.parquet")
        products[days] = add_cutoff_status(dataset, audit, review)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    checks = []
    for days, frame in products.items():
        directory = args.output_dir / f"day_{days:03d}"
        directory.mkdir(exist_ok=True)
        for name, subset in [("cutoff_dataset", frame),
                             ("needs_baseline_review", frame.loc[frame.training_row_action.eq("needs_baseline_review")])]:
            parquet_path = directory / f"{name}.parquet"
            csv_path = directory / f"{name}.csv"
            subset.to_parquet(parquet_path, index=False)
            subset.to_csv(csv_path, index=False, encoding="utf-8-sig", lineterminator="\n")
            outputs.extend([parquet_path, csv_path])
            # Verify round-trip and preservation of every pre-existing value.
            reloaded = pd.read_parquet(parquet_path)
            pd.testing.assert_frame_equal(reloaded, subset.reset_index(drop=True))
        original = pd.read_parquet(args.cutoff_dir / f"day_{days:03d}/cutoff_dataset.parquet")
        pd.testing.assert_frame_equal(frame[original.columns], original)
        checks.append({"window_days": days, "rows_preserved": len(frame),
                       "original_values_preserved": True, "parquet_round_trip_passed": True})
    summary = pd.DataFrame([status_summary(frame, days) for days, frame in products.items()])
    summary_path = args.output_dir / "cutoff_status_summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig", lineterminator="\n")
    outputs.append(summary_path)
    contract = json.loads((args.cutoff_dir / "feature_contract.json").read_text(encoding="utf-8"))
    contract["metadata_columns_not_predictors"] += STATUS_COLUMNS
    contract["cutoff_status_policy"] = {
        "scope": "First delivery of the reviewed implementation scope; does not describe ongoing use, maintenance, or reopening.",
        "status_at_cutoff": "completed when reviewed completion evidence is dated strictly before cutoff UTC day; otherwise unknown.",
        "completed_by_cutoff": "Nullable Boolean: true when supported; null means unknown, not false. No false values are inferred in this stage.",
        "has_recent_spec_commit": "Nullable Boolean: at least one spec commit in (cutoff minus 7 days, cutoff]; null when window unobserved. Does not establish in-progress state.",
        "cutoff_status_reason": "Reason for the supported completion or unresolved baseline judgment.",
        "cutoff_status_evidence_date": "Reviewed completion evidence date when completed by cutoff is supported.",
        "cutoff_status_evidence_url": "Copied reviewed source links for the supported judgment; no new independent annotation.",
        "training_row_action": "Exclude already completed from future first-completion forecasting; otherwise exclude incomplete windows or request baseline review. No row automatically included for training.",
        "same_day": "Unknown because outcome dates have day precision and cutoffs have time precision.",
        "later_completion": "Does not establish that completion had not occurred earlier.",
        "row_preservation": "All 564-style source records remain in the master; needs_baseline_review subset is a review queue, not training data.",
        "future_information": "Status evidence and selection diagnostics are retrospective metadata, never X. Predictor allowlist unchanged.",
        "activity_rule": "No exclusion based on full-history last commit, later commits, or recent-edit flag.",
        "confidence": "Inherits AI-assisted annotation evidence and its pending human confirmation.",
    }
    contract_path = args.output_dir / "feature_contract.json"
    write_json(contract_path, contract)
    outputs.append(contract_path)
    manifest = {
        "input_paths": {name: path.as_posix() for name, path in input_paths.items()},
        "input_sha256": input_hashes, "script_sha256": sha256(Path(__file__)),
        "configuration": parent["configuration"],
        "primary_dataset": f"day_{primary:03d}/cutoff_dataset.parquet",
        "status_columns": STATUS_COLUMNS, "summary": summary.to_dict("records"),
        "outputs_sha256": {path.relative_to(args.output_dir).as_posix(): sha256(path) for path in outputs},
        "validation": checks,
        "interpretation": "Supported prior completion plus unknown baseline status; no verified active/in-progress classification. "
                          "Recent editing and completion are separate concepts. No forecast training set is certified.",
    }
    write_json(args.output_dir / "manifest.json", manifest)
    print(json.dumps({"output_dir": args.output_dir.as_posix(), "summary": manifest["summary"],
                      "preservation_checks_passed": len(checks)}, indent=2))


if __name__ == "__main__":
    main()
