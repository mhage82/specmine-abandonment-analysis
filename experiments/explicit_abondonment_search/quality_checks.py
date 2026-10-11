from pathlib import Path
import json
import pandas as pd

experiment = Path(__file__).resolve().parent
source = experiment.parents[1] / "data/raw/specmine-full-inspection/spec_files.parquet"
output = experiment / "results"
output.mkdir(exist_ok=True)
columns = ["file_url_sha16", "repo_name", "file_path", "file_url",
           "file_last_commit_html_url", "file_last_commit_message"]
df = pd.read_parquet(source, columns=columns)
quality = []
for name in columns:
    values = df[name]
    blank = values.fillna("").astype(str).str.strip().eq("")
    quality.append({"field": name, "null_count": int(values.isna().sum()),
                    "null_or_blank_count": int(blank.sum()),
                    "null_or_blank_percent": round(float(blank.mean() * 100), 4)})
pd.DataFrame(quality).to_csv(output / "metadata_missingness.csv", index=False)
keywords = r"\babandon(?:ed|ing)?\b|\bcancel(?:led|ed)\b|\bshelved\b"
matched = df[df.file_last_commit_message.str.contains(keywords, case=False, na=False)]
selected = matched.head(20)
summary = {
    "total_metadata_records": len(df),
    "distinct_repositories": int(df.repo_name.nunique()),
    "duplicate_identifier_rows_beyond_first": int(df.file_url_sha16.duplicated().sum()),
    "duplicate_repository_path_rows_beyond_first": int(df.duplicated(["repo_name", "file_path"]).sum()),
    "keyword_matched_records": len(matched),
    "keyword_match_percent": round(len(matched) / len(df) * 100, 4),
    "selected_records": len(selected),
    "selected_distinct_repositories": int(selected.repo_name.nunique()),
    "selected_distinct_commit_urls": int(selected.file_last_commit_html_url.nunique()),
}
(output / "metadata_quality_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
pd.DataFrame([{"metric": k, "value": v} for k, v in summary.items()]).to_csv(
    output / "metadata_quality_summary.csv", index=False)
print(json.dumps(summary, indent=2))
print(pd.DataFrame(quality).to_string(index=False))
