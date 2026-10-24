"""Expand the review to every screened candidate without task-group subsampling.

Reuses the fresh completion experiment's packet writer, not feature_pipeline.py.
Preserves the earlier sample and carries its annotations into a separate output.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

from completion_stage2_candidates import csv_safe, write_review_packets

FIELDS = ["manual_status", "manual_scope_match", "manual_evidence_url",
          "manual_outcome_date", "manual_notes", "reviewer", "reviewed_at"]
SELECTION = ["file_url_sha16", "repo_name", "spec_tool", "file_path", "file_url",
             "exp_spec_distinct_commits", "linked_task_documents", "total_task_checkboxes",
             "task_paths_json", "task_count_disagreement", "review_group_id", "review_packet"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage1-dir", type=Path, default=Path("results/completion_exploration/stage1"))
    parser.add_argument("--stage2-dir", type=Path, default=Path("results/completion_exploration/stage2"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/completion_exploration/all140"))
    args = parser.parse_args()
    if args.output_dir.resolve() in {args.stage1_dir.resolve(), args.stage2_dir.resolve()}:
        raise ValueError("Use a separate output directory to preserve previous stages")
    candidates = pd.read_parquet(args.stage2_dir / "completion_candidates.parquet")
    candidates = candidates.sort_values(["repo_name", "file_path", "file_url_sha16"]).reset_index(drop=True)
    if candidates.file_url_sha16.duplicated().any():
        raise ValueError("Candidate identifiers must be unique")
    candidates["review_packet"] = candidates.file_url_sha16.map(lambda key: f"review_packets/{key}.md")
    review = candidates[SELECTION].copy()
    for col in review.columns:
        review[col] = review[col].map(csv_safe)
    for field in FIELDS:
        review[field] = ""
    previous_path = args.stage2_dir / "completion_review.csv"
    previous = pd.read_csv(previous_path, dtype=str, keep_default_na=False).set_index("file_url_sha16")
    if not previous.index.is_unique or not set(previous.index).issubset(set(review.file_url_sha16)):
        raise ValueError("Previous sample identifiers do not uniquely match candidates")
    for idx, row in review.iterrows():
        ident = row.file_url_sha16
        if ident in previous.index:
            for field in FIELDS:
                review.at[idx, field] = previous.at[ident, field]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / "completion_review.csv"
    if target.exists():
        existing = pd.read_csv(target, dtype=str, keep_default_na=False)
        if existing.file_url_sha16.tolist() != review.file_url_sha16.tolist():
            raise ValueError("Existing review has different identifiers/order; use a fresh directory")
        if not set(SELECTION).issubset(existing.columns) or not existing[SELECTION].equals(review[SELECTION]):
            raise ValueError("Existing review metadata differs from candidates; use a fresh directory")
        action = "preserved"
    else:
        review.to_csv(target, index=False, encoding="utf-8-sig")
        action = "created"
    evidence_dir = args.output_dir / "annotation_evidence"
    evidence_dir.mkdir(exist_ok=True)
    for ident in previous.index:
        source = args.stage2_dir / "annotation_evidence" / f"{ident}.json"
        if source.is_file():
            decision = json.loads(source.read_text(encoding="utf-8-sig"))
            if any(decision.get(field) != previous.at[ident, field] for field in FIELDS):
                raise ValueError(f"Prior CSV/decision mismatch: {ident}; preserve and reconcile before copying")
            destination = evidence_dir / source.name
            if not destination.exists():
                shutil.copyfile(source, destination)
    specs = pd.read_parquet(args.stage1_dir / "specifications.parquet")
    history = pd.read_parquet(args.stage1_dir / "spec_history.parquet")
    tasks = pd.read_parquet(args.stage2_dir / "candidate_task_evidence.parquet")
    docs = pd.read_parquet(args.stage1_dir / "task_documents.parquet")
    prs = pd.read_parquet(args.stage1_dir / "spec_pr_evidence.parquet")
    write_review_packets(candidates, specs, history, tasks, docs, args.output_dir, prs)
    candidates.to_parquet(args.output_dir / "review_population.parquet", index=False)
    manifest = {
        "population": "All stage-2 passing source records; no additional selection or deduplication",
        "rows": len(candidates), "repositories": int(candidates.repo_name.nunique()),
        "shared_task_groups": int(candidates.review_group_id.nunique()),
        "distinct_repo_paths": len(candidates.drop_duplicates(["repo_name", "file_path"])),
        "carried_prior_rows": len(previous), "csv_action": action,
        "source_candidates_sha256": hashlib.sha256((args.stage2_dir / "completion_candidates.parquet").read_bytes()).hexdigest(),
        "prior_review_sha256": hashlib.sha256(previous_path.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "reviewer_note": "AI-assisted evidence review remains distinct from automatic candidate filtering",
    }
    (args.output_dir / "population_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
