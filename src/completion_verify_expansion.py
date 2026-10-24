"""Verify an annotated archive expansion against screening and prior judgments.

This checks artifact integrity, not the correctness of research judgments.
Run after completion_apply_annotations.py and completion_summarize_review.py.
"""

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

import pandas as pd

from completion_apply_annotations import FIELDS, STATUSES
from completion_stage3_review_all import SELECTION


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-dir", type=Path,
                        default=Path("results/completion_exploration/all564"))
    parser.add_argument("--prior-dir", type=Path,
                        default=Path("results/completion_exploration/all140"))
    parser.add_argument("--stage1-dir", type=Path,
                        default=Path("results/completion_exploration/stage1"))
    parser.add_argument("--stage2-dir", type=Path,
                        default=Path("results/completion_exploration/stage2"))
    args = parser.parse_args()
    directory = args.review_dir
    key = "file_url_sha16"
    manifest = json.loads((directory / "population_manifest.json").read_text(encoding="utf-8"))
    review_path = directory / "completion_review.csv"
    prior_path = args.prior_dir / "completion_review.csv"
    rows, prior = read_csv(review_path), read_csv(prior_path)
    require(rows and len({r[key] for r in rows}) == len(rows), "Empty or duplicate review identifiers")
    by_id = {r[key]: r for r in rows}
    require(len(rows) == manifest["rows"] and len(prior) == manifest["carried_prior_rows"],
            "Population counts disagree with manifest")
    require(digest(prior_path) == manifest["prior_review_sha256"], "Prior CSV changed")
    screening_path = args.stage2_dir / "screening.parquet"
    require(digest(screening_path) == manifest["screening_sha256"], "Screening input changed")
    packet_inputs = {
        "stage1/specifications.parquet": args.stage1_dir / "specifications.parquet",
        "stage1/spec_history.parquet": args.stage1_dir / "spec_history.parquet",
        "stage1/task_documents.parquet": args.stage1_dir / "task_documents.parquet",
        "stage1/task_links.parquet": args.stage1_dir / "task_links.parquet",
        "stage1/spec_pr_evidence.parquet": args.stage1_dir / "spec_pr_evidence.parquet",
        "stage2/task_checklist_audit.parquet": args.stage2_dir / "task_checklist_audit.parquet",
    }
    require(set(manifest.get("packet_input_sha256", {})) == set(packet_inputs),
            "Packet input hashes are missing or incomplete; rerun stage 4")
    for name, path in packet_inputs.items():
        require(digest(path) == manifest["packet_input_sha256"][name], f"Packet input changed: {name}")
    screening = pd.read_parquet(screening_path)
    eligible = screening[
        screening.all_task_content_available & screening.all_task_checklists_checked
        & screening.exp_spec_distinct_commits.ge(2)
    ].sort_values(["repo_name", "file_path", key])
    require(list(eligible[key]) == [r[key] for r in rows], "Eligible set or row order changed")
    require(eligible.total_task_checkboxes.gt(0).all(), "Empty task lists entered the cohort")
    population = pd.read_parquet(directory / "review_population.parquet").set_index(key)
    annotated = pd.read_parquet(directory / "completion_review_annotated.parquet").set_index(key)
    require(population.index.is_unique and annotated.index.is_unique, "Duplicate Parquet identifiers")
    require(set(population.index) == set(by_id) == set(annotated.index), "Parquet identifier mismatch")
    prior_ids = {r[key] for r in prior}
    new_ids = set(by_id) - prior_ids
    expected_population = eligible.set_index(key).copy()
    expected_population["is_completion_candidate"] = True
    expected_population["exclusion_reasons"] = ""
    expected_population["is_new_archived_candidate"] = ~expected_population.index.isin(prior_ids)
    expected_population["review_packet"] = expected_population.index.map(
        lambda ident: f"review_packets/{ident}.md")
    require(set(population.columns) == set(expected_population.columns),
            "Population screening columns differ")
    pd.testing.assert_frame_equal(population, expected_population[population.columns])
    pd.testing.assert_frame_equal(annotated[population.columns], population)
    require(len(new_ids) == manifest["new_records"], "New-record count mismatch")
    require(set(population.index[population.is_new_archived_candidate]) == new_ids,
            "New-record marker mismatch")
    new = population.loc[sorted(new_ids)]
    require((new.exp_spec_is_archived | new.any_task_document_archived).all(),
            "Unexpected non-archived addition")
    for row in prior:
        ident = row[key]
        require(ident in by_id, f"Prior identifier missing: {ident}")
        require(all(by_id[ident][f] == row[f] for f in [*SELECTION, *FIELDS]),
                f"Prior record changed: {ident}")
        old = args.prior_dir / "annotation_evidence" / f"{ident}.json"
        carried = directory / "annotation_evidence" / old.name
        require(old.read_bytes() == carried.read_bytes(), f"Prior evidence changed: {ident}")
        require(digest(old) == manifest["prior_evidence_sha256"][ident],
                f"Prior evidence hash changed: {ident}")
    backups = sorted((directory / "annotation_evidence" / "backups").glob(
        "completion_review.before_codex_*.csv"))
    require(bool(backups), "Missing pre-application backup")
    initial = read_csv(backups[0])
    require([r[key] for r in initial] == [r[key] for r in rows], "Row order differs from backup")
    for before, row in zip(initial, rows):
        require(all(row[c] == before[c] for c in row if c not in FIELDS),
                f"Screening metadata changed: {row[key]}")
    for row in rows:
        ident = row[key]
        decision = json.loads((directory / "annotation_evidence" / f"{ident}.json")
                              .read_text(encoding="utf-8-sig"))
        require(decision.get(key) == ident and bool(decision.get("sources")),
                f"Invalid evidence record: {ident}")
        require(row["manual_status"] in STATUSES, f"Unknown review status: {ident}")
        require(row["manual_scope_match"] in {"yes", "partial", "unclear"},
                f"Unknown scope status: {ident}")
        for field in FIELDS:
            value = row[field]
            require(isinstance(value, str) and "\n" not in value and "\r" not in value,
                    f"Multiline or invalid annotation: {ident}/{field}")
            require(field == "manual_outcome_date" or bool(value.strip()),
                    f"Missing annotation: {ident}/{field}")
            require(decision.get(field) == value == annotated.at[ident, field],
                    f"CSV/JSON/Parquet disagreement: {ident}/{field}")
        for field in ("manual_outcome_date", "reviewed_at"):
            if row[field]:
                date.fromisoformat(row[field])
        if row["manual_status"] == "unclear":
            require(row["manual_outcome_date"] == "", f"Unclear record asserts an outcome date: {ident}")
    require(review_path.read_bytes().startswith(b"\xef\xbb\xbf"), "Missing UTF-8 BOM")
    require(len(review_path.read_text(encoding="utf-8-sig").splitlines()) == len(rows) + 1,
            "Unexpected CSV physical row count")
    require(population.repo_name.nunique() == manifest["repositories"], "Repository count mismatch")
    require(population.review_group_id.nunique() == manifest["shared_task_groups"], "Group count mismatch")
    require(len(population.drop_duplicates(["repo_name", "file_path"])) == manifest["distinct_repo_paths"],
            "Repository/path count mismatch")
    result = {
        "passed": True, "review_rows": len(rows), "new_archived_rows": len(new_ids),
        "prior_rows_preserved": len(prior), "prior_csv_sha256": digest(prior_path),
        "annotated_csv_sha256": digest(review_path),
        "checks": ["Exact eligibility set and deterministic row order",
                   "Specification/history/task/link/PR packet input hashes unchanged",
                   "Nonempty fully checked tasks and at least two distinct specification commits",
                   "Only archived records added; all prior rows and evidence bytes preserved",
                   "Both Parquets retain the expected screening values and row order",
                   "Pre-application metadata preserved", "Every CSV/JSON/Parquet annotation agrees",
                   "Complete valid statuses and ISO dates; unclear dates blank",
                   "UTF-8 BOM and one physical CSV line per record", "Population counts match manifest"],
        "limitation": "Integrity verification does not validate research-label correctness.",
    }
    (directory / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
