"""Sprint 1 descriptive quality checks and EDA of the item 6 Parquet output."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

KEY = "file_url_sha16"
COUNTS = ["feature_n_todo", "feature_n_checkboxes", "feature_n_checked",
          "feature_n_words", "pipeline_distinct_commit_count"]
FLAGS = ["feature_has_unfilled_placeholder", "pipeline_has_feature_row",
         "pipeline_has_history_rows"]
DATES = ["pipeline_first_observed_commit_at", "pipeline_last_observed_commit_at"]
REQUIRED = [KEY, "repo_name", "spec_tool", *COUNTS, *FLAGS, *DATES]


def numeric(series):
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def indicator_summary(frame):
    """Use valid observed denominators; invalid/missing values stay unknown."""
    todo = numeric(frame.feature_n_todo)
    placeholder = numeric(frame.feature_has_unfilled_placeholder)
    boxes = numeric(frame.feature_n_checkboxes)
    checked = numeric(frame.feature_n_checked)
    rules = [
        ("TODO count > 0", todo.notna() & todo.ge(0) & todo.mod(1).eq(0), todo.gt(0)),
        ("Placeholder flag = 1", placeholder.isin([0, 1]), placeholder.eq(1)),
        ("Unchecked checkboxes > 0", boxes.notna() & checked.notna() & boxes.ge(0)
         & checked.ge(0) & checked.le(boxes) & boxes.mod(1).eq(0) & checked.mod(1).eq(0), boxes.gt(checked)),
    ]
    rows = []
    for name, valid, positive in rules:
        observed = int(valid.sum())
        yes = int((valid & positive).sum())
        rows.append(dict(indicator=name, positive=yes, observed=observed,
                         unknown=len(frame)-observed,
                         percent_of_observed=100*yes/observed if observed else None))
    return pd.DataFrame(rows)


def analyze(frame, results, figures):
    missing_columns = sorted(set(REQUIRED)-set(frame))
    if missing_columns:
        raise ValueError(f"Required columns absent: {missing_columns}. Run item 6 first.")
    if frame.empty:
        raise ValueError("Analysis table is empty; no exploratory result can be calculated.")
    results.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    n = len(frame)
    missing = pd.DataFrame({"column": frame.columns,
                            "missing_rows": frame.isna().sum().values})
    missing["missing_percent"] = missing.missing_rows/n*100
    missing.sort_values(["missing_rows", "column"], ascending=[False, True]).to_csv(results/"missingness.csv", index=False)
    checks = []
    def check(name, count, meaning):
        checks.append(dict(check=name, affected_rows=int(count), meaning=meaning))
    badkey = frame[KEY].isna() | frame[KEY].astype(str).str.strip().eq("")
    check("missing_or_blank_spec_key", badkey.sum(), "Missing/blank identifiers")
    check("duplicate_spec_key_rows", frame.loc[~badkey, KEY].duplicated(keep=False).sum(), "All rows participating in duplicate keys")
    check("missing_repo_name", frame.repo_name.isna().sum(), "Null repository names")
    for col in COUNTS:
        v = numeric(frame[col])
        check(f"invalid_{col}", (frame[col].notna() & (v.isna() | v.lt(0) | v.mod(1).ne(0))).sum(), "Non-null nonnumeric/nonfinite/negative/noninteger counts")
    for col in FLAGS:
        v = numeric(frame[col])
        check(f"invalid_{col}", (frame[col].notna() & ~v.isin([0, 1])).sum(), "Non-null values outside 0/1")
    boxes, checked = numeric(frame.feature_n_checkboxes), numeric(frame.feature_n_checked)
    check("checked_exceeds_total", (checked > boxes).sum(), "Checked count exceeds total checkbox count")
    dates, coverage = {}, []
    for col in DATES:
        d = pd.to_datetime(frame[col], utc=True, errors="coerce", format="mixed")
        dates[col] = d
        invalid = frame[col].notna() & d.isna()
        check(f"invalid_{col}", invalid.sum(), "Non-null dates that could not be parsed")
        coverage.append(dict(column=col, valid_rows=int(d.notna().sum()),
                             missing_rows=int(frame[col].isna().sum()), invalid_rows=int(invalid.sum()),
                             earliest=d.min(), latest=d.max()))
    first, last = [dates[c] for c in DATES]
    check("first_commit_after_last", (first > last).sum(), "Chronological inconsistency")
    check("only_one_endpoint_present", (first.isna() ^ last.isna()).sum(), "Only one history endpoint is present")
    check("no_feature_row", numeric(frame.pipeline_has_feature_row).eq(0).sum(), "No matched feature record; not zero-valued features")
    check("no_history_rows", numeric(frame.pipeline_has_history_rows).eq(0).sum(), "No observed history records; not proof of no activity")
    pd.DataFrame(checks).to_csv(results/"quality_checks.csv", index=False)
    pd.DataFrame(coverage).to_csv(results/"date_coverage.csv", index=False)
    numeric_columns = frame.select_dtypes(include="number").columns
    frame[numeric_columns].describe().T.to_csv(results/"numeric_summary.csv", index_label="column")
    indicators = indicator_summary(frame)
    indicators.to_csv(results/"indicator_summary.csv", index=False)
    tools = frame.spec_tool.fillna("[missing]").value_counts(dropna=False).rename_axis("spec_tool").reset_index(name="specifications")
    tools.to_csv(results/"tool_distribution.csv", index=False)
    commits = numeric(frame.pipeline_distinct_commit_count)
    valid = commits.notna() & commits.ge(0) & commits.mod(1).eq(0)
    buckets = pd.cut(commits.where(valid), [-1,0,1,2,5,10,float("inf")], labels=["0","1","2","3–5","6–10","11+"])
    distribution = buckets.value_counts(sort=False).rename_axis("observed_commits").reset_index(name="specifications")
    distribution.to_csv(results/"commit_distribution.csv", index=False)
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(9, 4.5))
    rates = indicators.percent_of_observed.fillna(0)
    ax.barh(indicators.indicator, rates, color="#216a91")
    ax.set_xlim(0, max(10, float(rates.max()) * 1.65))
    ax.set_xlabel("Percent of specifications with a valid observed value")
    ax.set_title("Unfinished-work indicators in the sample\nThese indicators are not abandonment labels", loc="left")
    for i, row in indicators.iterrows():
        label = f"{row.percent_of_observed:.1f}% ({row.positive:,}/{row.observed:,})" if row.observed else "No valid observations"
        ax.text(rates.iloc[i]+max(0.1, float(rates.max())*0.02), i, label, va="center", fontsize=9)
    fig.tight_layout(); fig.savefig(figures/"unfinished_work_indicators.png", dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(distribution.observed_commits.astype(str), distribution.specifications, color="#216a91")
    ax.set_xlabel("Distinct observed commits per specification")
    ax.set_ylabel("Specifications")
    ax.set_title(f"Commit-history coverage (valid counts: {int(valid.sum()):,}/{n:,})", loc="left")
    fig.tight_layout(); fig.savefig(figures/"commit_distribution.png", dpi=180); plt.close(fig)
    summary = {"specification_rows": n, "unique_nonnull_spec_keys": int(frame[KEY].nunique()),
               "unique_nonnull_repositories": int(frame.repo_name.nunique()),
               "columns": len(frame.columns), "columns_with_nulls": int(frame.isna().any().sum()),
               "invalid_commit_count_rows": int((~valid).sum()),
               "quality_checks_with_findings": [c for c in checks if c['affected_rows'] > 0]}
    lines = ["# Sprint 1 data quality and exploratory findings", "", "## Measured findings", "",
             f"- Input: {n:,} rows, {summary['unique_nonnull_spec_keys']:,} distinct non-null specification keys, {summary['unique_nonnull_repositories']:,} distinct non-null repositories, and {len(frame.columns)} columns.",
             f"- Columns containing null values: {summary['columns_with_nulls']}. See missingness.csv for rates; null values may be legitimate or unavailable data.", ""]
    for row in indicators.itertuples():
        rate = f"{row.percent_of_observed:.2f}%" if row.observed else "undefined"
        lines.append(f"- {row.indicator}: {row.positive:,}/{row.observed:,} valid observed records ({rate}); {row.unknown:,} unknown/invalid records.")
    lines += ["", "Quality checks with findings:", ""]
    lines += [f"- {c['check']}: {c['affected_rows']:,} rows. {c['meaning']}." for c in summary['quality_checks_with_findings']] or ["- None among the implemented checks. This is not proof of complete or unbiased data."]
    lines += ["", "## Interpretation and limits", "",
              "The available features support initial exploration of unfinished-work indicators. Indicator groups overlap and must not be summed into a unique specification total.", "",
              "Commit dates describe observed records, not verified creation, intent, or complete history. No inactivity cutoff, 30/60/90/180-day eligibility classification, or censoring rule is imposed here. ", "",
              "This curated broad-census sample does not support population-rate estimates. Kiro data is outside this run. Missingness is measured as null values; semantic missingness such as blank text, sentinel values, or incorrect but parseable dates may require further inspection. An existing feature row does not guarantee successful content retrieval.", "",
              "The script reports quality issues without dropping rows, imputing values, or editing the input. Duplicate specification rows, if present, would affect row-based percentages and must be resolved before substantive interpretation."]
    (results/"findings.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/analysis_table.parquet"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/eda"))
    parser.add_argument("--figures-dir", type=Path, default=Path("figures/eda"))
    args = parser.parse_args()
    try:
        if not args.input.is_file():
            raise ValueError(f"Input not found: {args.input}. Run feature_pipeline.py first.")
        frame = pd.read_parquet(args.input)
        summary = analyze(frame, args.output_dir, args.figures_dir)
        h = hashlib.sha256()
        with args.input.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024*1024), b''): h.update(chunk)
        summary['input_sha256'] = h.hexdigest()
        summary['versions'] = {'python': sys.version.split()[0], 'pandas': pd.__version__, 'matplotlib': matplotlib.__version__}
        (args.output_dir/"eda_summary.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
        print(f"Analyzed {len(frame):,} specification rows.")
        print(f"Tables and findings: {args.output_dir}")
        print(f"Figures: {args.figures_dir}")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"EDA error: {exc}\n")


if __name__ == "__main__":
    main()
