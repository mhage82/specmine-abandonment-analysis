"""Expand full-history review to archived records; preserve the prior annotations.

Retains >=2 distinct specification commits and nonempty, fully checked linked
task documents. Archive membership is eligibility, never a completion label.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

from completion_stage2_candidates import csv_safe, write_review_packets
from completion_stage3_review_all import FIELDS, SELECTION


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage1-dir", type=Path, default=Path("results/completion_exploration/stage1"))
    parser.add_argument("--stage2-dir", type=Path, default=Path("results/completion_exploration/stage2"))
    parser.add_argument("--prior-dir", type=Path, default=Path("results/completion_exploration/all140"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/completion_exploration/all564"))
    args = parser.parse_args()
    if args.output_dir.resolve() in {p.resolve() for p in (args.stage1_dir, args.stage2_dir, args.prior_dir)}:
        raise ValueError("Use a separate output directory")
    screening_path = args.stage2_dir / "screening.parquet"
    screening = pd.read_parquet(screening_path)
    eligible = (screening.all_task_content_available & screening.all_task_checklists_checked
                & screening.exp_spec_distinct_commits.ge(2))
    candidates = screening[eligible].copy().sort_values(
        ["repo_name", "file_path", "file_url_sha16"]).reset_index(drop=True)
    if candidates.empty or candidates.file_url_sha16.duplicated().any():
        raise ValueError("Expected nonempty population with unique source identifiers")
    prior_path = args.prior_dir / "completion_review.csv"
    prior = pd.read_csv(prior_path, dtype=str, keep_default_na=False).set_index("file_url_sha16")
    if not prior.index.is_unique or not set(prior.index).issubset(candidates.file_url_sha16):
        raise ValueError("Prior identifiers do not uniquely match expanded population")
    candidates["is_completion_candidate"] = True
    candidates["exclusion_reasons"] = ""
    candidates["is_new_archived_candidate"] = ~candidates.file_url_sha16.isin(prior.index)
    new = candidates[candidates.is_new_archived_candidate]
    if not (new.exp_spec_is_archived | new.any_task_document_archived).all():
        raise ValueError("Expansion unexpectedly added a non-archived record")
    candidates["review_packet"] = candidates.file_url_sha16.map(lambda key: f"review_packets/{key}.md")
    selection = [*SELECTION, "exp_spec_is_archived", "any_task_document_archived", "is_new_archived_candidate"]
    review = candidates[selection].copy()
    for column in review.columns:
        review[column] = review[column].map(csv_safe)
    for field in FIELDS:
        review[field] = ""
    decisions = {}
    for idx, row in review.iterrows():
        ident = row.file_url_sha16
        if ident in prior.index:
            if any(row[col] != prior.at[ident, col] for col in SELECTION if col != "file_url_sha16"):
                raise ValueError(f"Prior screening metadata changed: {ident}")
            source = args.prior_dir / "annotation_evidence" / f"{ident}.json"
            decision = json.loads(source.read_text(encoding="utf-8-sig"))
            if decision.get("file_url_sha16") != ident or any(decision.get(f) != prior.at[ident, f] for f in FIELDS):
                raise ValueError(f"Prior CSV/evidence mismatch: {ident}")
            decisions[ident] = source
            for field in FIELDS:
                review.at[idx, field] = prior.at[ident, field]
    packet_inputs = {
        "stage1/specifications.parquet": args.stage1_dir / "specifications.parquet",
        "stage1/spec_history.parquet": args.stage1_dir / "spec_history.parquet",
        "stage1/task_documents.parquet": args.stage1_dir / "task_documents.parquet",
        "stage1/task_links.parquet": args.stage1_dir / "task_links.parquet",
        "stage1/spec_pr_evidence.parquet": args.stage1_dir / "spec_pr_evidence.parquet",
        "stage2/task_checklist_audit.parquet": args.stage2_dir / "task_checklist_audit.parquet",
    }
    packet_input_hashes = {name: sha(path) for name, path in packet_inputs.items()}
    existing_manifest_path = args.output_dir / "population_manifest.json"
    if existing_manifest_path.exists():
        existing_manifest = json.loads(existing_manifest_path.read_text(encoding="utf-8"))
        if ("packet_input_sha256" in existing_manifest
                and existing_manifest["packet_input_sha256"] != packet_input_hashes):
            raise ValueError("Packet inputs changed; use a fresh output directory to preserve prior evidence")
    specs = pd.read_parquet(packet_inputs["stage1/specifications.parquet"])
    history = pd.read_parquet(packet_inputs["stage1/spec_history.parquet"])
    docs = pd.read_parquet(packet_inputs["stage1/task_documents.parquet"])
    links = pd.read_parquet(packet_inputs["stage1/task_links.parquet"])
    audit = pd.read_parquet(packet_inputs["stage2/task_checklist_audit.parquet"])
    task_evidence = links[links.file_url_sha16.isin(candidates.file_url_sha16)].drop_duplicates(
        ["file_url_sha16", "task_path"]).merge(audit, on="task_document_id", how="left", validate="many_to_one")
    if set(task_evidence.file_url_sha16) != set(candidates.file_url_sha16):
        raise ValueError("Task evidence does not cover every candidate identifier")
    expected_task_counts = candidates.set_index("file_url_sha16").linked_task_documents.astype("int64")
    actual_task_counts = task_evidence.groupby("file_url_sha16").size().reindex(expected_task_counts.index)
    if not expected_task_counts.gt(0).all() or not actual_task_counts.eq(expected_task_counts).all():
        raise ValueError("Task evidence document counts disagree with screening")
    if not (task_evidence.task_content_available.eq(True) & task_evidence.all_checked.eq(True)
            & task_evidence.task_document_found.eq(True)).all():
        raise ValueError("Task evidence no longer supports candidate eligibility")
    prs = pd.read_parquet(packet_inputs["stage1/spec_pr_evidence.parquet"])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "completion_review.csv"
    if csv_path.exists():
        existing = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        if not set(selection).issubset(existing.columns) or not existing[selection].equals(review[selection]):
            raise ValueError("Existing identifiers/order/metadata differ; use a fresh output directory")
        action = "preserved"
    else:
        review.to_csv(csv_path, index=False, encoding="utf-8-sig")
        action = "created"
    evidence_dir = args.output_dir / "annotation_evidence"
    evidence_dir.mkdir(exist_ok=True)
    for ident, source in decisions.items():
        dest = evidence_dir / source.name
        if dest.exists() and dest.read_bytes() != source.read_bytes():
            raise ValueError(f"Prior evidence changed in expanded directory: {ident}")
        if not dest.exists():
            shutil.copyfile(source, dest)
    write_review_packets(candidates, specs, history, task_evidence, docs, args.output_dir, prs)
    # The shared earlier packet writer describes its non-archived cohort. Replace
    # its single header sentence in these new packets; collected Markdown stays intact.
    old_header = "Selection: non-archived specification and task paths; multiple specification commits; all linked local task checklists nonempty and checked."
    new_header = "Selection: archived and non-archived paths eligible; at least two distinct specification commits; all linked local task checklists nonempty and checked. Archive status is not an outcome label."
    for ident in candidates.file_url_sha16:
        path = args.output_dir / "review_packets" / f"{ident}.md"
        content = path.read_text(encoding="utf-8")
        if old_header not in content:
            raise ValueError("Packet writer selection header changed; update the archive-aware wrapper")
        path.write_text(content.replace(old_header, new_header, 1), encoding="utf-8")
    candidates.to_parquet(args.output_dir / "review_population.parquet", index=False)
    task_evidence.to_parquet(args.output_dir / "candidate_task_evidence.parquet", index=False)
    review[review.file_url_sha16.isin(new.file_url_sha16)][selection].to_csv(
        args.output_dir / "new_archived_candidates.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "population": "All >=2-commit source records with available, nonempty, fully checked linked task lists; archived paths included",
        "rows": len(candidates), "new_records": len(new), "carried_prior_rows": len(prior),
        "repositories": int(candidates.repo_name.nunique()),
        "shared_task_groups": int(candidates.review_group_id.nunique()),
        "distinct_repo_paths": len(candidates.drop_duplicates(["repo_name", "file_path"])),
        "csv_action": action, "screening_sha256": sha(screening_path),
        "prior_review_sha256": sha(prior_path), "script_sha256": sha(Path(__file__)),
        "packet_input_sha256": packet_input_hashes,
        "prior_evidence_sha256": {ident: sha(path) for ident, path in decisions.items()},
        "annotation_policy": "Human-readable evidence review, separate from eligibility filtering; no automatic outcome assigned",
    }
    (args.output_dir / "population_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k != "prior_evidence_sha256"}, indent=2))


if __name__ == "__main__":
    main()
