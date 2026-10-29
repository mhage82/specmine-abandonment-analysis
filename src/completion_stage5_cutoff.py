"""Rebuild commit-history features at a cutoff, preserving full-history labels.

This exports the reviewed cohort, not a training-ready binary classification set.
Only FEATURE_COLUMNS may become X. Outcome evidence and eligibility diagnostics
live in a separate audit. No current content, checklist or PR features are copied.
"""

import argparse
import hashlib
import json
import platform
from numbers import Integral
from pathlib import Path

import pandas as pd
import pyarrow


KEY = "file_url_sha16"
REVIEW_FIELDS = ["manual_status", "manual_scope_match", "manual_evidence_url",
                 "manual_outcome_date", "manual_notes", "reviewer", "reviewed_at"]
FEATURE_DEFINITIONS = {
    "prefix_commit_count": "Distinct specification commits in [anchor, cutoff].",
    "prefix_active_commit_days": "Distinct UTC calendar days with a prefix commit.",
    "prefix_author_name_count": "Distinct stripped, casefolded nonempty Git author names; a contributor proxy.",
    "prefix_missing_author_count": "Prefix commits without a nonempty Git author name.",
    "prefix_activity_span_days": "Elapsed days between first and last prefix commits.",
    "prefix_inactive_days_at_cutoff": "Elapsed days between last prefix commit and cutoff.",
    "prefix_mean_commit_gap_days": "Mean gap between consecutive prefix commits, including zero gaps; null with one commit.",
    "prefix_max_commit_gap_days": "Maximum gap between consecutive prefix commits; null with one commit.",
    "prefix_commits_first_half": "Commits at or before anchor + window/2.",
    "prefix_commits_second_half": "Commits after anchor + window/2 and at or before cutoff.",
    "prefix_commits_last_3_days": "Prefix commits in (cutoff - 3 days, cutoff].",
    "prefix_commits_last_7_days": "Prefix commits in (cutoff - 7 days, cutoff].",
}
FEATURE_COLUMNS = list(FEATURE_DEFINITIONS)
HISTORY_COLUMNS = [KEY, "commit_sha", "committed_at", "author_name"]
METADATA_COLUMNS = [KEY, "manual_status", "first_observed_commit_at", "prediction_at",
                    "observation_end_at", "window_days", "window_observed"]


def require_columns(frame, columns, name):
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{name} missing columns: {sorted(missing)}")


def require_unique_ids(frame, name):
    require_columns(frame, [KEY], name)
    if (frame.empty or frame[KEY].isna().any() or frame[KEY].eq("").any()
            or frame[KEY].duplicated().any()):
        raise ValueError(f"{name} must have unique, nonempty identifiers")


def utc_dates(values, name):
    parsed = pd.to_datetime(values, utc=True, errors="coerce", format="mixed")
    if parsed.isna().any():
        raise ValueError(f"Missing or invalid {name}")
    return parsed


def completion_timing(status, outcome_date, cutoff):
    if status != "completed":
        return "not_completed_label"
    if not outcome_date:
        return "missing_date"
    day = pd.Timestamp(outcome_date).date()
    if day < cutoff.date():
        return "before_cutoff"
    if day == cutoff.date():
        return "same_day_timing_uncertain"
    return "after_cutoff"


def prefix_features(prefix, anchor, cutoff):
    times = prefix.committed_at
    gaps = times.diff().dropna().dt.total_seconds() / 86400
    names = prefix.author_name.fillna("").astype(str).str.strip().str.casefold()
    midpoint = anchor + (cutoff - anchor) / 2
    return {
        "prefix_commit_count": len(prefix),
        "prefix_active_commit_days": times.dt.normalize().nunique(),
        "prefix_author_name_count": names[names.ne("")].nunique(),
        "prefix_missing_author_count": names.eq("").sum(),
        "prefix_activity_span_days": (times.iloc[-1] - anchor).total_seconds() / 86400,
        "prefix_inactive_days_at_cutoff": (cutoff - times.iloc[-1]).total_seconds() / 86400,
        "prefix_mean_commit_gap_days": gaps.mean(),
        "prefix_max_commit_gap_days": gaps.max(),
        "prefix_commits_first_half": times.le(midpoint).sum(),
        "prefix_commits_second_half": times.gt(midpoint).sum(),
        "prefix_commits_last_3_days": times.gt(cutoff - pd.Timedelta(3, unit="D")).sum(),
        "prefix_commits_last_7_days": times.gt(cutoff - pd.Timedelta(7, unit="D")).sum(),
    }


def build_cutoff_dataset(review, specifications, history, window_days):
    """Return (same-cohort dataset, bounded history, outcome/eligibility audit).

    A cutoff beyond history collection is retained, but its predictors are null.
    The earliest observed path commit is an anchor, not verified spec creation.
    """
    if isinstance(window_days, bool) or not isinstance(window_days, Integral) or window_days <= 0:
        raise ValueError("window_days must be a positive integer")
    require_unique_ids(review, "review")
    require_unique_ids(specifications, "specifications")
    require_columns(review, ["manual_status", "manual_outcome_date", "repo_name",
                             "file_path", "review_group_id"], "review")
    require_columns(specifications, ["commit_history_status", "commit_history_fetched_at"], "specifications")
    require_columns(history, HISTORY_COLUMNS, "history")
    valid_statuses = {"completed", "abandoned", "in_progress", "deferred", "unclear"}
    if not set(review.manual_status).issubset(valid_statuses):
        raise ValueError("Review contains missing or unrecognized manual_status")
    dates = review.manual_outcome_date.fillna("").astype(str)
    nonempty_dates = dates[dates.ne("")]
    if (not nonempty_dates.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all()
            or pd.to_datetime(nonempty_dates, format="%Y-%m-%d", errors="coerce").isna().any()):
        raise ValueError("manual_outcome_date must be blank or a valid YYYY-MM-DD date")
    ids = set(review[KEY])
    if not ids.issubset(set(specifications[KEY])):
        raise ValueError("Review identifiers missing from specifications")
    specs = specifications.loc[specifications[KEY].isin(ids)].copy().set_index(KEY)
    if not specs.commit_history_status.eq("done").all():
        raise ValueError("All selected histories must have status done")
    specs["observation_end_at"] = utc_dates(specs.commit_history_fetched_at, "history fetch time")
    events = history.loc[history[KEY].isin(ids)].copy()
    if set(events[KEY]) != ids:
        raise ValueError("Each reviewed specification needs recorded history")
    if events.duplicated([KEY, "commit_sha"]).any():
        raise ValueError("Duplicate specification/commit pair in history")
    if not events.commit_sha.fillna("").str.fullmatch(r"[0-9a-f]{40}").all():
        raise ValueError("Expected full lowercase Git commit SHAs")
    events["committed_at"] = utc_dates(events.committed_at, "commit time")
    if events.groupby("commit_sha").committed_at.nunique().gt(1).any():
        raise ValueError("Conflicting timestamps for the same commit SHA")
    observation_ends = events[KEY].map(specs.observation_end_at)
    if events.committed_at.gt(observation_ends).any():
        raise ValueError("Commit history contains an event after its collection boundary")
    events = events.sort_values([KEY, "committed_at", "commit_sha"], kind="stable")
    grouped = {ident: group for ident, group in events.groupby(KEY, sort=False)}
    result_rows, audit_rows, histories = [], [], []
    for row in review.to_dict("records"):
        ident = row[KEY]
        full = grouped[ident]
        anchor = full.committed_at.iloc[0]
        cutoff = anchor + pd.Timedelta(int(window_days), unit="D")
        observation_end = specs.at[ident, "observation_end_at"]
        observed = cutoff <= observation_end
        prefix = full.loc[full.committed_at.le(cutoff)]
        histories.append(prefix[HISTORY_COLUMNS])
        predictors = prefix_features(prefix, anchor, cutoff) if observed else {
            name: float("nan") for name in FEATURE_COLUMNS
        }
        metadata = {KEY: ident, "manual_status": row["manual_status"],
                    "first_observed_commit_at": anchor, "prediction_at": cutoff,
                    "observation_end_at": observation_end, "window_days": int(window_days),
                    "window_observed": bool(observed)}
        result_rows.append({**metadata, **predictors})
        outcome_date = row["manual_outcome_date"]
        outcome_date = "" if pd.isna(outcome_date) else str(outcome_date)
        timing = completion_timing(row["manual_status"], outcome_date, cutoff)
        reasons = ["specification_birth_and_baseline_state_unverified"]
        if not observed:
            reasons.append("cutoff_not_observed")
        if row["manual_status"] == "unclear":
            reasons.append("unresolved_outcome_not_a_negative")
        elif row["manual_status"] != "completed":
            reasons.append("outcome_target_and_horizon_need_review")
        else:
            reasons.append({"missing_date": "completion_evidence_date_missing",
                            "before_cutoff": "completion_evidence_precedes_cutoff",
                            "same_day_timing_uncertain": "completion_time_within_cutoff_day_unknown",
                            "after_cutoff": "later_evidence_does_not_establish_first_completion"}[timing])
        first_events = full.loc[full.committed_at.eq(anchor)]
        archive_message = (first_events.message.fillna("").str.contains(
            r"\barchiv\w*\b", case=False, regex=True).any() if "message" in full else False)
        path_archive = any(part.casefold() in {"archive", "archived", "archives", "_archive"}
                           for part in str(row["file_path"]).replace("\\", "/").split("/"))
        audit_rows.append({
            **metadata, "repo_name": row["repo_name"], "file_path_at_collection": row["file_path"],
            "review_group_id": row["review_group_id"], "manual_outcome_date": outcome_date,
            "completion_timing": timing,
            "completion_evidence_before_observed_start": bool(
                row["manual_status"] == "completed" and outcome_date
                and pd.Timestamp(outcome_date).date() < anchor.date()),
            "anchor_message_mentions_archive": bool(archive_message),
            "collected_path_has_archive_segment": path_archive,
            "anchor_is_verified_creation": False,
            "full_history_commit_count": len(full), "retained_history_commit_count": len(prefix),
            "post_cutoff_commit_count": len(full) - len(prefix),
            "full_history_signature": hashlib.sha256(
                "\n".join(sorted(full.commit_sha)).encode()).hexdigest(),
            "prospective_training_eligible": False,
            "eligibility_reasons": ";".join(reasons),
        })
    dataset = pd.DataFrame(result_rows, columns=METADATA_COLUMNS + FEATURE_COLUMNS)
    # One numeric type across windows and null/missing gap statistics.
    dataset[FEATURE_COLUMNS] = dataset[FEATURE_COLUMNS].astype("float64")
    bounded_history = pd.concat(histories, ignore_index=True)
    audit = pd.DataFrame(audit_rows)
    return dataset, bounded_history, audit


def sha256(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def window_summary(dataset, history, audit):
    completed = audit.manual_status.eq("completed")
    return {
        "window_days": int(dataset.window_days.iloc[0]), "cohort_rows": len(dataset),
        "observed_window_rows": int(dataset.window_observed.sum()),
        "incomplete_window_rows": int((~dataset.window_observed).sum()),
        "retained_history_rows": len(history),
        "records_with_later_spec_commits": int(audit.post_cutoff_commit_count.gt(0).sum()),
        "observed_rows_with_one_prefix_commit": int(dataset.prefix_commit_count.eq(1).sum()),
        "completed_before_cutoff": int((completed & audit.completion_timing.eq("before_cutoff")).sum()),
        "completed_same_day_uncertain": int((completed & audit.completion_timing.eq("same_day_timing_uncertain")).sum()),
        "completed_evidence_after_cutoff": int((completed & audit.completion_timing.eq("after_cutoff")).sum()),
        "completed_without_evidence_date": int((completed & audit.completion_timing.eq("missing_date")).sum()),
        "unclear_outcomes": int(audit.manual_status.eq("unclear").sum()),
        "prospective_training_eligible_rows": int(audit.prospective_training_eligible.sum()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage1-dir", type=Path, default=Path("results/completion_exploration/stage1"))
    parser.add_argument("--review-dir", type=Path, default=Path("results/completion_exploration/all564"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/completion_exploration/cutoff"))
    parser.add_argument("--primary-days", type=int, default=7)
    parser.add_argument("--windows", type=int, nargs="+", default=[7, 14, 30, 60, 90])
    args = parser.parse_args()
    windows = sorted(set(args.windows + [args.primary_days]))
    if min(windows) <= 0:
        raise ValueError("Every window must be positive")
    if args.output_dir.resolve() in {args.stage1_dir.resolve(), args.review_dir.resolve()}:
        raise ValueError("Use a separate output directory")
    inputs = {
        "review_csv": args.review_dir / "completion_review.csv",
        "annotated_parquet": args.review_dir / "completion_review_annotated.parquet",
        "annotation_summary": args.review_dir / "annotation_summary.json",
        "population_manifest": args.review_dir / "population_manifest.json",
        "specifications": args.stage1_dir / "specifications.parquet",
        "history": args.stage1_dir / "spec_history.parquet",
    }
    input_hashes = {name: sha256(path) for name, path in inputs.items()}
    annotation_summary = json.loads(inputs["annotation_summary"].read_text(encoding="utf-8"))
    for name, summary_key in [("review_csv", "csv_sha256"), ("annotated_parquet", "annotated_parquet_sha256")]:
        if input_hashes[name] != annotation_summary[summary_key]:
            raise ValueError("Reviewed inputs changed; verify/export annotations before creating cutoff data")
    population_manifest = json.loads(inputs["population_manifest"].read_text(encoding="utf-8"))
    for name, packet_key in [("specifications", "stage1/specifications.parquet"),
                             ("history", "stage1/spec_history.parquet")]:
        if input_hashes[name] != population_manifest["packet_input_sha256"][packet_key]:
            raise ValueError("Stage-1 inputs differ from those used for annotation")
    config = {"primary_days": args.primary_days, "windows": windows}
    manifest_path = args.output_dir / "manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if previous["input_sha256"] != input_hashes or previous["configuration"] != config:
            raise ValueError("Use a new output directory for changed inputs or cutoff configuration")
    review = pd.read_csv(inputs["review_csv"], dtype=str, keep_default_na=False)
    annotated = pd.read_parquet(inputs["annotated_parquet"])
    require_unique_ids(review, "review")
    require_unique_ids(annotated, "annotated Parquet")
    if set(review[KEY]) != set(annotated[KEY]):
        raise ValueError("CSV/Parquet cohort disagreement")
    left = review.set_index(KEY)[REVIEW_FIELDS]
    right = annotated.set_index(KEY).loc[left.index, REVIEW_FIELDS].fillna("").astype(str)
    if not left.equals(right):
        raise ValueError("CSV/Parquet annotation disagreement")
    specs = pd.read_parquet(inputs["specifications"], columns=[
        KEY, "commit_history_status", "commit_history_fetched_at"])
    history = pd.read_parquet(inputs["history"], columns=[*HISTORY_COLUMNS, "message"])
    # Validate and compute every window before creating any files.
    products = {days: build_cutoff_dataset(review, specs, history, days) for days in windows}
    comparison = pd.DataFrame([window_summary(*products[days]) for days in windows])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = []
    for days, (dataset, prefix, audit) in products.items():
        directory = args.output_dir / f"day_{days:03d}"
        directory.mkdir(exist_ok=True)
        for name, frame in [("cutoff_dataset", dataset), ("cutoff_history", prefix), ("eligibility_audit", audit)]:
            path = directory / f"{name}.parquet"
            frame.to_parquet(path, index=False)
            output_paths.append(path)
            if name != "cutoff_history":
                csv_path = directory / f"{name}.csv"
                frame.to_csv(csv_path, index=False, encoding="utf-8-sig", lineterminator="\n")
                output_paths.append(csv_path)
    comparison_path = args.output_dir / "cutoff_comparison.csv"
    comparison.to_csv(comparison_path, index=False, encoding="utf-8-sig", lineterminator="\n")
    output_paths.append(comparison_path)
    contract = {
        "feature_columns": FEATURE_COLUMNS, "feature_definitions": FEATURE_DEFINITIONS,
        "metadata_columns_not_predictors": METADATA_COLUMNS,
        "label_column": "manual_status",
        "label_policy": "Preserved AI-assisted full-history judgments; unclear is unlabeled, not zero or abandoned.",
        "anchor": "Earliest committed_at in collected specification-path history; not verified birth.",
        "cutoff": "anchor + window_days * 24 hours, inclusive, UTC",
        "observation_boundary": "commit_history_fetched_at",
        "incomplete_window_policy": "Retain row and intended cutoff; all predictors null. History contains only observed prefix events.",
        "single_commit_policy": "Gap mean/max null; count and other prefix summaries remain valid when window observed.",
        "history_columns": HISTORY_COLUMNS,
        "audit_policy": "Every audit column is excluded from predictors, including full-history counts and evidence timing.",
        "snapshot_features_excluded": ["current specification content", "feature_* content metrics",
                                       "checked/unchecked task counts", "archive status and paths",
                                       "repository popularity", "latest PR state", "commit comment/verification fields"],
        "future_training_requirements": ["Confirm target and prediction horizon",
                                         "Verify birth/path lineage and incomplete baseline state at cutoff",
                                         "Adjudicate outcomes and obtain a confirmed negative class",
                                         "Expand beyond full-history checked-task-selected cohort",
                                         "Separate repositories across training/evaluation"],
    }
    contract_path = args.output_dir / "feature_contract.json"
    write_json(contract_path, contract)
    output_paths.append(contract_path)
    primary = products[args.primary_days]
    manifest = {
        "configuration": config, "input_paths": {name: path.as_posix() for name, path in inputs.items()},
        "input_sha256": input_hashes, "script_sha256": sha256(Path(__file__)),
        "software": {"python": platform.python_version(), "pandas": pd.__version__, "pyarrow": pyarrow.__version__},
        "rows": len(review), "status_counts": review.manual_status.value_counts().sort_index().to_dict(),
        "primary_dataset": f"day_{args.primary_days:03d}/cutoff_dataset.parquet",
        "distinct_repositories": int(review.repo_name.nunique()),
        "distinct_history_signatures": int(primary[2].full_history_signature.nunique()),
        "completion_evidence_before_observed_start": int(primary[2].completion_evidence_before_observed_start.sum()),
        "comparison": comparison.to_dict("records"),
        "outputs_sha256": {p.relative_to(args.output_dir).as_posix(): sha256(p) for p in output_paths},
        "interpretation": "Exploratory cutoff cohort, not a training-ready binary outcome dataset. "
                          "The 7-day default is a coverage choice, not a validated optimal cutoff. "
                          "Filtering predictors does not remove full-history cohort-selection bias.",
    }
    write_json(manifest_path, manifest)
    print(json.dumps({"output_dir": args.output_dir.as_posix(), "rows": len(review),
                      "primary_dataset": manifest["primary_dataset"],
                      "status_counts": manifest["status_counts"], "comparison": manifest["comparison"]}, indent=2))


if __name__ == "__main__":
    main()
