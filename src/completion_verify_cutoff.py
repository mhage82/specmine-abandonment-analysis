"""Independently verify exported cutoff cohorts against immutable source tables.

This verifier does not import or call the stage-5 feature builder. Input paths
in manifest.json are resolved relative to the current working directory.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


KEY = "file_url_sha16"
EXPECTED_FEATURES = [
    "prefix_commit_count", "prefix_active_commit_days", "prefix_author_name_count",
    "prefix_missing_author_count", "prefix_activity_span_days",
    "prefix_inactive_days_at_cutoff", "prefix_mean_commit_gap_days",
    "prefix_max_commit_gap_days", "prefix_commits_first_half",
    "prefix_commits_second_half", "prefix_commits_last_3_days",
    "prefix_commits_last_7_days",
]
EXPECTED_METADATA = [KEY, "manual_status", "first_observed_commit_at", "prediction_at",
                     "observation_end_at", "window_days", "window_observed"]
EXPECTED_HISTORY = [KEY, "commit_sha", "committed_at", "author_name"]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check(condition, description):
    if not condition:
        raise ValueError(description)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def numeric_equal(actual, expected, description):
    check(np.allclose(np.asarray(actual, dtype=float), np.asarray(expected, dtype=float),
                      rtol=1e-12, atol=1e-12, equal_nan=True), description)


def verify_csv_matches_parquet(csv_path, frame):
    """Check identifiers, labels, dates and numeric values after CSV round-trip."""
    csv = pd.read_csv(csv_path, dtype={KEY: str}, keep_default_na=True)
    check(list(csv.columns) == list(frame.columns), f"CSV columns differ: {csv_path}")
    check(len(csv) == len(frame), f"CSV row count differs: {csv_path}")
    for name in frame.columns:
        expected = frame[name]
        actual = csv[name]
        if isinstance(expected.dtype, pd.DatetimeTZDtype):
            parsed = pd.to_datetime(actual, utc=True, errors="raise", format="mixed")
            check(parsed.equals(expected), f"CSV datetime mismatch: {csv_path}/{name}")
        elif pd.api.types.is_numeric_dtype(expected.dtype):
            numeric_equal(actual, expected, f"CSV numeric mismatch: {csv_path}/{name}")
        else:
            check(actual.fillna("").astype(str).equals(expected.fillna("").astype(str)),
                  f"CSV value mismatch: {csv_path}/{name}")


def verify(output_dir):
    manifest_path = output_dir / "manifest.json"
    manifest = read_json(manifest_path)
    inputs = {name: Path(value) for name, value in manifest["input_paths"].items()}
    check(set(inputs) == set(manifest["input_sha256"]), "Input manifest keys differ")
    for name, path in inputs.items():
        check(sha256(path) == manifest["input_sha256"][name], f"Changed input: {name}")
    for relative, digest in manifest["outputs_sha256"].items():
        path = output_dir / relative
        check(path.resolve().is_relative_to(output_dir.resolve()), "Output hash path escapes directory")
        check(sha256(path) == digest, f"Changed exported artifact: {relative}")
    builder = Path(__file__).with_name("completion_stage5_cutoff.py")
    check(sha256(builder) == manifest["script_sha256"], "Builder changed after export")

    contract = read_json(output_dir / "feature_contract.json")
    check(contract["feature_columns"] == EXPECTED_FEATURES, "Unexpected model feature allowlist")
    check(contract["metadata_columns_not_predictors"] == EXPECTED_METADATA, "Metadata contract differs")
    check(contract["history_columns"] == EXPECTED_HISTORY, "Unexpected exported history schema")
    check(contract["label_column"] == "manual_status", "Unexpected label column")
    check(not set(EXPECTED_FEATURES) & set(EXPECTED_METADATA), "Metadata overlaps predictors")

    review = pd.read_csv(inputs["review_csv"], dtype=str, keep_default_na=False)
    annotated = pd.read_parquet(inputs["annotated_parquet"])
    specs = pd.read_parquet(inputs["specifications"])
    raw = pd.read_parquet(inputs["history"])
    check(review[KEY].is_unique and review[KEY].ne("").all(), "Review IDs are not unique/nonempty")
    ids = review[KEY].tolist()
    check(annotated[KEY].is_unique and set(annotated[KEY]) == set(ids), "Annotated cohort differs")
    check(specs[KEY].is_unique, "Specification identifiers are duplicated")
    specs = specs.set_index(KEY).loc[ids]
    raw = raw.loc[raw[KEY].isin(ids)].copy()
    check(set(raw[KEY]) == set(ids), "Selected specifications lack source history")
    check(not raw.duplicated([KEY, "commit_sha"]).any(), "Duplicate source ID/commit pair")
    raw["committed_at"] = pd.to_datetime(raw.committed_at, utc=True, errors="raise", format="mixed")
    check(raw.committed_at.notna().all(), "Null source commit timestamp")
    check(specs.commit_history_status.eq("done").all(), "Incomplete source history")
    fetched = pd.to_datetime(specs.commit_history_fetched_at, utc=True, errors="raise", format="mixed")
    check(raw.committed_at.le(raw[KEY].map(fetched)).all(), "Source history extends past observation")
    first = raw.groupby(KEY).committed_at.min().reindex(ids)
    total = raw.groupby(KEY).size().reindex(ids)
    indexed_review = review.set_index(KEY)
    check(annotated.set_index(KEY).loc[ids, "manual_status"].tolist() == review.manual_status.tolist(),
          "Annotated Parquet labels differ from CSV")
    summary = read_json(inputs["annotation_summary"])
    check(summary["csv_sha256"] == manifest["input_sha256"]["review_csv"], "Review summary hash differs")
    check(summary["annotated_parquet_sha256"] == manifest["input_sha256"]["annotated_parquet"],
          "Annotated summary hash differs")
    population = read_json(inputs["population_manifest"])
    for name, packet in [("specifications", "stage1/specifications.parquet"),
                         ("history", "stage1/spec_history.parquet")]:
        check(population["packet_input_sha256"][packet] == manifest["input_sha256"][name],
              f"Reviewed population provenance mismatch: {name}")

    windows = manifest["configuration"]["windows"]
    primary = manifest["configuration"]["primary_days"]
    check(primary in windows and windows == sorted(set(windows)), "Invalid window configuration")
    check(all(isinstance(day, int) and not isinstance(day, bool) and day > 0 for day in windows),
          "Cutoff windows must be positive integers")
    comparison = []
    for day in windows:
        directory = output_dir / f"day_{day:03d}"
        dataset = pd.read_parquet(directory / "cutoff_dataset.parquet")
        history = pd.read_parquet(directory / "cutoff_history.parquet")
        audit = pd.read_parquet(directory / "eligibility_audit.parquet")
        check(list(dataset.columns) == EXPECTED_METADATA + EXPECTED_FEATURES,
              f"Unexpected predictor or metadata column in day {day}")
        check(list(history.columns) == EXPECTED_HISTORY, f"History schema mismatch in day {day}")
        check(not set(EXPECTED_FEATURES) & set(audit.columns), f"Audit contains predictor columns in day {day}")
        for name, frame in [("dataset", dataset), ("audit", audit)]:
            check(frame[KEY].tolist() == ids, f"{name} IDs/order differ in day {day}")
            check(frame.manual_status.tolist() == review.manual_status.tolist(),
                  f"{name} labels differ in day {day}")
        cutoff = first + pd.to_timedelta(day, unit="D")
        observed = cutoff.le(fetched)
        check(dataset.first_observed_commit_at.tolist() == first.tolist(), f"Anchor mismatch in day {day}")
        check(dataset.prediction_at.tolist() == cutoff.tolist(), f"Cutoff mismatch in day {day}")
        check(dataset.observation_end_at.tolist() == fetched.tolist(), f"Observation boundary mismatch in day {day}")
        check(dataset.window_days.eq(day).all(), f"Window duration mismatch in day {day}")
        check(dataset.window_observed.tolist() == observed.tolist(), f"Window mask mismatch in day {day}")
        for column in EXPECTED_METADATA:
            check(dataset[column].equals(audit[column]), f"Audit metadata mismatch in day {day}/{column}")
        check(dataset.loc[~dataset.window_observed, EXPECTED_FEATURES].isna().all().all(),
              f"Incomplete windows have features in day {day}")

        expected_history = raw.loc[raw.committed_at.le(raw[KEY].map(cutoff)), EXPECTED_HISTORY]
        ordering = [KEY, "committed_at", "commit_sha"]
        pd.testing.assert_frame_equal(
            history.sort_values(ordering).reset_index(drop=True),
            expected_history.sort_values(ordering).reset_index(drop=True),
            check_dtype=False, check_exact=True,
        )
        counts = expected_history.groupby(KEY).size().reindex(ids)
        numeric_equal(audit.full_history_commit_count, total, f"Full-history audit count mismatch in day {day}")
        numeric_equal(audit.retained_history_commit_count, counts, f"Prefix audit count mismatch in day {day}")
        numeric_equal(audit.post_cutoff_commit_count, total - counts, f"Future audit count mismatch in day {day}")
        check(not audit.prospective_training_eligible.any(), f"Unverified forecast eligibility in day {day}")
        check(not audit.anchor_is_verified_creation.any(), f"Unverified birth claimed in day {day}")
        check(audit.manual_outcome_date.fillna("").tolist() == review.manual_outcome_date.tolist(),
              f"Outcome date changed in day {day}")
        check(audit.repo_name.tolist() == review.repo_name.tolist(), f"Repository grouping changed in day {day}")
        check(audit.review_group_id.tolist() == review.review_group_id.tolist(), f"Review grouping changed in day {day}")
        expected_timing = []
        before_start = []
        for ident in ids:
            label = indexed_review.at[ident, "manual_status"]
            value = indexed_review.at[ident, "manual_outcome_date"]
            if label != "completed":
                timing = "not_completed_label"
            elif not value:
                timing = "missing_date"
            else:
                date = pd.Timestamp(value).date()
                boundary = cutoff.at[ident].date()
                timing = "before_cutoff" if date < boundary else (
                    "after_cutoff" if date > boundary else "same_day_timing_uncertain")
            expected_timing.append(timing)
            before_start.append(bool(label == "completed" and value and
                                     pd.Timestamp(value).date() < first.at[ident].date()))
        check(audit.completion_timing.tolist() == expected_timing, f"Outcome timing mismatch in day {day}")
        check(audit.completion_evidence_before_observed_start.tolist() == before_start,
              f"Pre-anchor outcome audit mismatch in day {day}")

        # Independent feature calculation uses integer timestamp differences and
        # Python sets/counts rather than the builder's pandas feature function.
        indexed = dataset.set_index(KEY)
        for ident, group in expected_history.groupby(KEY):
            if not observed.at[ident]:
                continue
            timestamps = sorted(group.committed_at.tolist())
            origin = first.at[ident]
            boundary = cutoff.at[ident]
            seconds = [(time - origin).total_seconds() for time in timestamps]
            gaps = np.diff(seconds) / 86400
            authors = ["" if pd.isna(name) else str(name).strip().casefold() for name in group.author_name]
            boundary_seconds = day * 86400
            expected = [
                len(group), len({time.date() for time in timestamps}),
                len(set(authors) - {""}), authors.count(""), seconds[-1] / 86400,
                (boundary_seconds - seconds[-1]) / 86400,
                float(np.mean(gaps)) if len(gaps) else np.nan,
                float(np.max(gaps)) if len(gaps) else np.nan,
                sum(value <= boundary_seconds / 2 for value in seconds),
                sum(value > boundary_seconds / 2 for value in seconds),
                sum(value > boundary_seconds - 3 * 86400 for value in seconds),
                sum(value > boundary_seconds - 7 * 86400 for value in seconds),
            ]
            numeric_equal(indexed.loc[ident, EXPECTED_FEATURES], expected,
                          f"Recomputed feature mismatch in day {day}/{ident}")
        verify_csv_matches_parquet(directory / "cutoff_dataset.csv", dataset)
        verify_csv_matches_parquet(directory / "eligibility_audit.csv", audit)
        timings = pd.Series(expected_timing).value_counts()
        comparison.append({
            "window_days": day, "cohort_rows": len(ids),
            "observed_window_rows": int(observed.sum()), "incomplete_window_rows": int((~observed).sum()),
            "retained_history_rows": len(expected_history),
            "records_with_later_spec_commits": int((total > counts).sum()),
            "observed_rows_with_one_prefix_commit": int((counts.eq(1) & observed).sum()),
            "completed_before_cutoff": int(timings.get("before_cutoff", 0)),
            "completed_same_day_uncertain": int(timings.get("same_day_timing_uncertain", 0)),
            "completed_evidence_after_cutoff": int(timings.get("after_cutoff", 0)),
            "completed_without_evidence_date": int(timings.get("missing_date", 0)),
            "unclear_outcomes": int(review.manual_status.eq("unclear").sum()),
            "prospective_training_eligible_rows": 0,
        })
    check(comparison == manifest["comparison"], "Recomputed window comparison differs from manifest")
    pd.testing.assert_frame_equal(pd.read_csv(output_dir / "cutoff_comparison.csv"), pd.DataFrame(comparison))
    check(manifest["rows"] == len(ids), "Manifest cohort count differs")
    check(manifest["status_counts"] == review.manual_status.value_counts().sort_index().to_dict(),
          "Manifest label totals differ")
    check(manifest["distinct_repositories"] == review.repo_name.nunique(), "Manifest repository count differs")
    check(manifest["primary_dataset"] == f"day_{primary:03d}/cutoff_dataset.parquet", "Primary output differs")
    result = {
        "passed": True, "cohort_rows": len(ids), "windows_verified": windows,
        "input_hashes_verified": len(inputs), "output_hashes_verified": len(manifest["outputs_sha256"]),
        "manifest_sha256": sha256(manifest_path), "builder_sha256": sha256(builder),
        "verifier_sha256": sha256(Path(__file__)),
        "checks": ["Source/input/output/script hashes", "Exact original identifiers/order/labels",
                   "UTC anchors and observation boundaries", "Exact cutoff-bounded history records",
                   "Independently recomputed prefix features", "Unobserved-window null masks",
                   "Fixed feature allowlist and separate audit", "Outcome evidence timing",
                   "CSV/Parquet agreement", "Comparison totals", "No asserted forecast-ready eligibility"],
        "interpretation": "Integrity and temporal filtering verified; this does not validate outcome labels, "
                          "establish original specification creation, remove cohort-selection bias, "
                          "or make the cohort a complete supervised training dataset.",
    }
    destination = output_dir / "verification.json"
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results/completion_exploration/cutoff"))
    args = parser.parse_args()
    print(json.dumps(verify(args.output_dir), indent=2))


if __name__ == "__main__":
    main()
