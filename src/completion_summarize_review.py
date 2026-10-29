"""Export an already annotated review; never infer or convert outcome labels.

The output Parquet contains screening metadata plus reviewed fields, not a
prediction-time feature matrix. The CSV and evidence JSONs remain authoritative.
"""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from completion_apply_annotations import FIELDS, STATUSES


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-dir", type=Path,
                        default=Path("results/completion_exploration/all140"))
    args = parser.parse_args()
    directory = args.review_dir
    csv_path = directory / "completion_review.csv"
    population_path = directory / "review_population.parquet"
    review = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    population = pd.read_parquet(population_path)
    key = "file_url_sha16"
    for frame in (review, population):
        if frame.empty or frame[key].isna().any() or frame[key].duplicated().any():
            raise ValueError("Expected nonempty tables with unique non-null identifiers")
    if set(review[key]) != set(population[key]):
        raise ValueError("Review must cover the complete population")
    if not set(review.manual_status).issubset(STATUSES):
        raise ValueError("Every row needs a recognized reviewed status")
    evidence_hashes = {}
    for row in review.to_dict("records"):
        evidence_path = directory / "annotation_evidence" / f"{row[key]}.json"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
        if evidence.get(key) != row[key]:
            raise ValueError(f"Evidence identifier mismatch: {row[key]}")
        for field in FIELDS:
            if evidence.get(field) != row[field]:
                raise ValueError(f"CSV/evidence disagreement: {row[key]}/{field}")
            if field != "manual_outcome_date" and not row[field].strip():
                raise ValueError(f"Missing annotation: {row[key]}/{field}")
        if not evidence.get("sources"):
            raise ValueError(f"Missing evidence sources: {row[key]}")
        evidence_hashes[row[key]] = digest(evidence_path)
    if set(FIELDS) & set(population.columns):
        raise ValueError("Input population already contains annotations; use the screening table")
    annotated = population.merge(review[[key, *FIELDS]], on=key,
                                 how="left", validate="one_to_one", sort=False)
    output_path = directory / "completion_review_annotated.parquet"
    annotated.to_parquet(output_path, index=False)
    counts = review.manual_status.value_counts().sort_index().to_dict()
    by_repo = pd.crosstab(review.repo_name, review.manual_status).sort_index()
    by_repo.to_csv(directory / "status_by_repository.csv", encoding="utf-8-sig")

    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")

    lines = ["# Full candidate review index", "",
             "AI-assisted evidence judgments; human confirmation pending. "
             "Unclear is not an abandonment or negative label.", "",
             "Each identifier links to its evidence JSON. Packets contain the collected "
             "specification and task context. This is a review of all screened records, "
             "including shared task groups and repeated paths.", "",
             "| ID | Repository | Specification | Status | Date | Reason |",
             "| --- | --- | --- | --- | --- | --- |"]
    for row in review.to_dict("records"):
        ident = row[key]
        values = [f"[{ident}](annotation_evidence/{ident}.json)", row["repo_name"],
                  f"[{cell(row['file_path'])}](review_packets/{ident}.md)",
                  row["manual_status"], row["manual_outcome_date"], row["manual_notes"]]
        lines.append("| " + " | ".join(cell(v) for v in values) + " |")
    (directory / "ANNOTATION_INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {
        "rows": len(review), "repositories": int(review.repo_name.nunique()),
        "shared_task_groups": int(review.review_group_id.nunique()),
        "distinct_repo_paths": len(review.drop_duplicates(["repo_name", "file_path"])),
        "status_counts": {str(k): int(v) for k, v in counts.items()},
        "completed_with_recorded_event_date": int(
            ((review.manual_status == "completed") & (review.manual_outcome_date != "")).sum()),
        "completed_without_recorded_event_date": int(
            ((review.manual_status == "completed") & (review.manual_outcome_date == "")).sum()),
        "csv_sha256": digest(csv_path), "population_sha256": digest(population_path),
        "annotated_parquet_sha256": digest(output_path),
        "evidence_sha256": evidence_hashes,
        "interpretation": "Screened full-history completion review; not model accuracy, "
                          "independent human labels, binary abandonment labels, or day-90 predictors.",
    }
    (directory / "annotation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "evidence_sha256"}, indent=2))


if __name__ == "__main__":
    main()
