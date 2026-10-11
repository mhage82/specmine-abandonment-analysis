"""Build one broad-census analysis row per specification for Sprint 1."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from data_loader import load_tables, DEFAULT_TABLES

KEY = "file_url_sha16"


def require_keys(frame, name, unique=False):
    if KEY not in frame:
        raise ValueError(f"{name}: missing {KEY}")
    if frame[KEY].isna().any() or frame[KEY].astype(str).str.strip().eq("").any():
        raise ValueError(f"{name}: missing/blank specification keys")
    if unique and frame[KEY].duplicated().any():
        raise ValueError(f"{name}: duplicate specification keys; resolve before joining")


def build_analysis_table(tables):
    specs = tables["spec_files"].copy()
    features = tables["spec_content_features"].copy()
    commits = tables["spec_file_commits"].copy()
    require_keys(specs, "spec_files", True)
    require_keys(features, "spec_content_features", True)
    require_keys(commits, "spec_file_commits")
    for col in ("commit_sha", "committed_at"):
        if col not in commits:
            raise ValueError(f"spec_file_commits: missing {col}")
    audit = {"input_rows": {k: len(v) for k, v in tables.items()}}
    audit["feature_rows_without_spec"] = int((~features[KEY].isin(specs[KEY])).sum())
    audit["commit_rows_without_spec"] = int((~commits[KEY].isin(specs[KEY])).sum())
    # Prefix feature columns to preserve provenance and prevent collisions.
    features = features.rename(columns={c: f"feature_{c}" for c in features if c != KEY})
    features["pipeline_has_feature_row"] = True
    generated = set(features.columns) - {KEY}
    if generated.intersection(specs.columns) or any(c.startswith("pipeline_") for c in specs):
        raise ValueError("Source columns conflict with pipeline output names")
    result = specs.merge(features, on=KEY, how="left", validate="one_to_one")
    result["pipeline_has_feature_row"] = result["pipeline_has_feature_row"].eq(True)

    raw = commits["committed_at"]
    commits["pipeline_commit_at"] = pd.to_datetime(raw, utc=True, errors="coerce", format="mixed")
    commits["pipeline_bad_date"] = raw.notna() & commits["pipeline_commit_at"].isna()
    audit["unparseable_commit_dates"] = int(commits["pipeline_bad_date"].sum())
    audit["missing_commit_dates"] = int(raw.isna().sum())
    audit["duplicate_spec_commit_rows"] = int(commits.duplicated([KEY, "commit_sha"]).sum())
    grouped = commits.groupby(KEY, sort=False)
    history = grouped.agg(
        pipeline_history_rows=(KEY, "size"),
        pipeline_distinct_commit_count=("commit_sha", "nunique"),
        pipeline_first_observed_commit_at=("pipeline_commit_at", "min"),
        pipeline_last_observed_commit_at=("pipeline_commit_at", "max"),
        pipeline_valid_commit_date_rows=("pipeline_commit_at", "count"),
        pipeline_invalid_commit_date_rows=("pipeline_bad_date", "sum"),
    ).reset_index()
    result = result.merge(history, on=KEY, how="left", validate="one_to_one")
    counts = ["pipeline_history_rows", "pipeline_distinct_commit_count",
              "pipeline_valid_commit_date_rows", "pipeline_invalid_commit_date_rows"]
    for col in counts:
        result[col] = result[col].fillna(0).astype("Int64")
    result["pipeline_has_history_rows"] = result["pipeline_history_rows"].gt(0)
    result["pipeline_observed_history_span_days"] = (
                                                            result["pipeline_last_observed_commit_at"] - result["pipeline_first_observed_commit_at"]
                                                    ).dt.total_seconds() / 86400
    # Missing dates stay missing. Zero span can mean a single valid date.
    if len(result) != len(specs):
        raise ValueError("Join changed specification count")
    audit.update(output_rows=len(result), output_columns=len(result.columns),
                 specs_without_features=int((~result.pipeline_has_feature_row).sum()),
                 specs_without_history=int((~result.pipeline_has_history_rows).sum()))
    return result, audit


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", default=Path("results"), type=Path)
    args = parser.parse_args()
    try:
        tables = load_tables(args.data_dir)
        result, audit = build_analysis_table(tables)
        audit["source_sha256"] = {name: file_hash(args.data_dir.expanduser() / f"{name}.parquet")
                                  for name in DEFAULT_TABLES}
        out = args.output_dir.expanduser()
        out.mkdir(parents=True, exist_ok=True)
        result.to_parquet(out / "analysis_table.parquet", index=False)
        result.to_csv(out / "analysis_table.csv", index=False)
        spec_columns = set(tables["spec_files"].columns)

        feature_columns = {
            f"feature_{col}"
            for col in tables["spec_content_features"].columns
            if col != KEY
        }

        schema = [
            {
                "column": col,
                "dtype": str(dtype),
                "source": (
                    "spec_files"
                    if col in spec_columns
                    else "spec_content_features"
                    if col in feature_columns
                    else "derived/join status"
                ),
            }
            for col, dtype in result.dtypes.items()
        ]
        (out / "analysis_schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        (out / "pipeline_summary.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        print(f"Created analysis table: {len(result):,} rows, {len(result.columns)} columns")
        print(f"Specifications without feature rows: {audit['specs_without_features']:,}")
        print(f"Specifications without history rows: {audit['specs_without_history']:,}")
        print(f"Outputs saved to: {out}")
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, f"Pipeline error: {exc}\n")


if __name__ == "__main__":
    main()
