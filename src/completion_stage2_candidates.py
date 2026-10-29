"""Screen local full-history evidence for completion candidates; never assign outcomes."""

import argparse
import hashlib
import json
import platform
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow


def value_text(value):
    return "" if value is None or pd.isna(value) else str(value)


def is_archived_path(path):
    # Include observed conventions such as design-archive and _archive without
    # treating a feature directory named archive-tools as an archive container.
    return bool(re.search(r"(?:^|/)(?:[^/]*[-_.])?(?:archive|archives|archived)(?:/|$)",
                          value_text(path).replace("\\", "/"), re.I))


def parse_checklist(markdown):
    """Count Markdown task-list items outside fenced code, comments, and quotes.

    This records the document's claims, not implementation correctness. Optional
    unchecked items still count as unchecked for this intentionally strict screen.
    """
    text = re.sub(r"<!--.*?(?:-->|\Z)", "", value_text(markdown), flags=re.S)
    fence_char, fence_length = None, 0
    checked = unchecked = 0
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(">"):
            continue
        fence = re.match(r"^(`{3,}|~{3,})(.*)$", stripped)
        if fence_char:
            if (fence and fence.group(1)[0] == fence_char
                    and len(fence.group(1)) >= fence_length
                    and not fence.group(2).strip()):
                fence_char = None
            continue
        if fence:
            fence_char, fence_length = fence.group(1)[0], len(fence.group(1))
            continue
        item = re.match(r"^(?:[-+*]|\d+[.)])\s+\[([ xX])\](?:\s|$)", stripped)
        if item:
            if item.group(1).lower() == "x":
                checked += 1
            else:
                unchecked += 1
    count = checked + unchecked
    return {"checkbox_count": count, "checked_count": checked,
            "unchecked_count": unchecked, "all_checked": count > 0 and unchecked == 0}


def validate_unique(frame, key, name):
    if key not in frame:
        raise ValueError(f"{name}: missing {key}")
    if frame[key].isna().any() or frame[key].astype(str).str.strip().eq("").any():
        raise ValueError(f"{name}: blank identifiers")
    if frame[key].duplicated().any():
        raise ValueError(f"{name}: duplicate {key}")


def evaluate_specs(specs, links, docs, min_commits=2):
    """Return every spec's screening decision, task evidence, and document audit."""
    if min_commits < 2:
        raise ValueError("min_commits must be at least 2 for this experiment")
    validate_unique(specs, "file_url_sha16", "specifications")
    validate_unique(docs, "task_document_id", "task_documents")
    audit_records = []
    for doc in docs.to_dict("records"):
        content = value_text(doc.get("task_content"))
        counts = parse_checklist(content)
        available = bool(content.strip()) and value_text(doc.get("task_fetch_status")).lower() == "done"
        source_total, source_done = doc.get("source_n_tasks"), doc.get("source_n_tasks_done")
        match = None
        if pd.notna(source_total) and pd.notna(source_done):
            match = (int(source_total) == counts["checkbox_count"]
                     and int(source_done) == counts["checked_count"])
        audit_records.append({
            "task_document_id": doc["task_document_id"],
            "task_content_available": available,
            "task_is_archived": is_archived_path(doc.get("task_path")),
            "source_count_matches": match,
            **counts,
        })
    audit_columns = ["task_document_id", "task_content_available", "task_is_archived",
                     "source_count_matches", "checkbox_count", "checked_count",
                     "unchecked_count", "all_checked"]
    audit = pd.DataFrame(audit_records, columns=audit_columns)
    evidence = links.drop_duplicates(["file_url_sha16", "task_path"]).copy()
    if not evidence.file_url_sha16.isin(specs.file_url_sha16).all():
        raise ValueError("task_links contains unknown specification identifiers")
    evidence = evidence.merge(audit, on="task_document_id", how="left", validate="many_to_one")
    evidence["task_content_available"] = (evidence.task_content_available.eq(True)
                                           & evidence.task_document_found.eq(True))
    evidence["task_is_archived"] = evidence.task_path.map(is_archived_path)
    evidence["all_checked"] = evidence.all_checked.eq(True) & evidence.task_content_available
    for col in ["checkbox_count", "checked_count", "unchecked_count"]:
        evidence[col] = pd.to_numeric(evidence[col], errors="coerce").astype("Int64")
    by_spec = {key: frame for key, frame in evidence.groupby("file_url_sha16", sort=False)}
    identity = ["file_url_sha16", "repo_name", "file_path", "file_url", "spec_tool", "spec_role",
                "repo_archived", "has_tasks", "commit_history_status", "commit_history_fetched_at",
                "exp_spec_distinct_commits", "exp_first_commit_at", "exp_last_commit_at",
                "exp_history_rows", "exp_invalid_commit_dates"]
    screening = specs[[col for col in identity if col in specs]].copy()
    records = []
    for spec in specs.to_dict("records"):
        group = by_spec.get(spec["file_url_sha16"])
        linked = group is not None and len(group) > 0
        count = len(group) if linked else 0
        available = linked and bool(group.task_content_available.all())
        archived = (is_archived_path(spec.get("file_path"))
                    or value_text(spec.get("spec_role")).lower() == "archived")
        tasks_archived = linked and bool(group.task_is_archived.any())
        all_checked = available and bool(group.all_checked.all())
        commits = spec.get("exp_spec_distinct_commits", 0)
        enough_commits = pd.notna(commits) and int(commits) >= min_commits
        reasons = []
        if archived:
            reasons.append("archived_specification")
        if not enough_commits:
            reasons.append("fewer_than_minimum_specification_commits")
        if not linked:
            reasons.append("no_recorded_task_link")
        elif not available:
            reasons.append("task_content_missing_or_fetch_not_done")
        if tasks_archived:
            reasons.append("archived_task_document")
        if available and not all_checked:
            reasons.append("empty_or_unchecked_task_list")
        paths = sorted(set(group.task_path)) if linked else []
        task_ids = sorted(set(group.task_document_id.dropna().astype(str))) if linked else []
        group_id = hashlib.sha256((spec["repo_name"] + "\n" + "\n".join(paths)).encode()).hexdigest()[:20]
        records.append({
            "exp_spec_is_archived": archived,
            "exp_meets_minimum_commits": bool(enough_commits),
            "linked_task_documents": count,
            "all_task_content_available": bool(available),
            "any_task_document_archived": bool(tasks_archived),
            "all_task_checklists_checked": bool(all_checked),
            "total_task_checkboxes": int(group.checkbox_count.sum()) if available else None,
            "total_checked_tasks": int(group.checked_count.sum()) if available else None,
            "total_unchecked_tasks": int(group.unchecked_count.sum()) if available else None,
            "task_count_disagreement": bool(group.source_count_matches.eq(False).any()) if linked else False,
            "task_paths_json": json.dumps(paths, ensure_ascii=False),
            "task_document_ids_json": json.dumps(task_ids),
            "review_group_id": group_id if linked else "",
            "is_completion_candidate": not reasons,
            "exclusion_reasons": ";".join(reasons),
        })
    screening = pd.concat([screening.reset_index(drop=True), pd.DataFrame(records)], axis=1)
    for col in ["total_task_checkboxes", "total_checked_tasks", "total_unchecked_tasks"]:
        screening[col] = screening[col].astype("Int64")
    return screening, evidence, audit


def select_review_sample(candidates, size=10, seed=42):
    """Deterministic purposive sample: distinct task groups, repositories first."""
    if size < 0:
        raise ValueError("sample size must be nonnegative")
    if candidates.empty or size == 0:
        return candidates.iloc[:0].copy()
    sample = candidates.sort_values(
        ["exp_spec_distinct_commits", "file_url_sha16"], ascending=[False, True]
    ).drop_duplicates("review_group_id").copy()
    sample["_order"] = sample.review_group_id.map(
        lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest())
    sample = sample.sort_values(["_order", "file_url_sha16"])
    sample["_repo_round"] = sample.groupby("repo_name").cumcount()
    return sample.sort_values(["_repo_round", "_order", "file_url_sha16"]).head(size).drop(
        columns=["_order", "_repo_round"]).reset_index(drop=True)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_safe(value):
    text = re.sub(r"[\r\n\t]+", " ", value_text(value))
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


def markdown_code(content):
    text = value_text(content)
    fence = "`" * max(3, 1 + max((len(s) for s in re.findall(r"`+", text)), default=0))
    return f"{fence}text\n{text}\n{fence}\n"


def md_cell(value):
    return re.sub(r"[\r\n]+", " ", value_text(value)).replace("|", "\\|")


def write_review_packets(sample, specs, history, evidence, docs, out, pr_evidence=None):
    packet_dir = out / "review_packets"
    packet_dir.mkdir(parents=True, exist_ok=True)
    spec_index = specs.set_index("file_url_sha16")
    doc_index = docs.set_index("task_document_id")
    index_lines = ["# Completion review examples", "",
                   "These are filtered candidates, not confirmed completion labels.", "",
                   "Use completion_review.csv to record the review. Packets are regenerated on rerun; do not annotate them in place.", ""]
    for record in sample.to_dict("records"):
        key = record["file_url_sha16"]
        spec = spec_index.loc[key]
        spec_tasks = evidence[evidence.file_url_sha16.eq(key)]
        lines = [f"# Review {key}", "", f"Repository: {record['repo_name']}", "",
                 f"Specification path: `{record['file_path']}`", "",
                 f"Specification URL: {value_text(record.get('file_url'))}", "",
                 f"Recorded distinct specification commits: {record['exp_spec_distinct_commits']}", "",
                 "Selection: non-archived specification and task paths; multiple specification commits; all linked local task checklists nonempty and checked.", "",
                 "This is a full available-history exploration, not a prediction experiment. Check whether the task scope matches this specification and seek implementation evidence.", "",
                 "## Specification snapshot", "", markdown_code(spec.get("exp_spec_markdown")), "",
                 "## Related task snapshots", ""]
        for task in spec_tasks.to_dict("records"):
            doc = doc_index.loc[task["task_document_id"]]
            lines.extend([f"### {task['task_path']}", "",
                          f"Checked / total recognized items: {task['checked_count']} / {task['checkbox_count']}", "",
                          f"Source count agrees with parser: {task.get('source_count_matches')}", "",
                          f"Content hash recorded by source: {value_text(doc.get('task_content_sha'))}", "",
                          f"Content fetched at: {value_text(doc.get('task_fetched_at'))}", "",
                          f"Task URL at the specification revision: {value_text(task.get('task_url_at_spec_revision'))}", "",
                          "This constructed URL is a navigation aid; equivalence to the separately collected task snapshot has not been verified.", "",
                          f"Task history: {value_text(task.get('task_history_url'))}", "",
                          markdown_code(doc.get("task_content")), ""])
        lines.extend(["## Recorded specification-file commits", "",
                      "This is file history, not the repository's complete implementation history. Follow moves/renames and linked PRs when necessary.", "",
                      "| Date (source) | Commit | Message (first 200 characters) |",
                      "| --- | --- | --- |"])
        rows = history[history.file_url_sha16.eq(key)].drop_duplicates("commit_sha")
        if "committed_at" in rows:
            rows = rows.sort_values("committed_at", kind="stable")
        for commit in rows.to_dict("records"):
            sha = value_text(commit.get("commit_sha"))
            url = value_text(commit.get("html_url")) or f"https://github.com/{record['repo_name']}/commit/{sha}"
            lines.append(f"| {md_cell(commit.get('committed_at'))} | [{sha[:12]}]({url}) | {md_cell(commit.get('message'))[:200]} |")
        if pr_evidence is not None and "file_url_sha16" in pr_evidence:
            prs = pr_evidence[pr_evidence.file_url_sha16.eq(key)].drop_duplicates(
                ["repo_name", "pr_number"])
            lines.extend(["", "## Collected PR leads", "",
                          "PR association or merge alone does not prove completion. Inspect the relevant requirements and diff.", ""])
            for pr in prs.to_dict("records"):
                number = pr.get("pr_number")
                if pd.notna(number):
                    url = value_text(pr.get("pr_url")) or f"https://github.com/{pr['repo_name']}/pull/{int(number)}"
                    merged = value_text(pr.get("pr_is_merged")) or "unknown"
                    lines.append(f"- {url}: {md_cell(pr.get('pr_title'))}; merged={merged}")
            if prs.empty:
                lines.append("No PR lead was recorded in the collected evidence; this is not proof that no PR exists.")
        lines.extend(["", "## Manual review", "",
                      "Record status as completed, abandoned, in_progress, deferred, or unclear in the CSV. Leave an outcome unknown when evidence is insufficient.", "",
                      "Save the evidence URL, supported date, scope match, and explanation. A completion checklist is a claim; a later archive move or a keyword alone is insufficient.", ""])
        (packet_dir / f"{key}.md").write_text("\n".join(lines), encoding="utf-8")
        index_lines.append(f"- [{record['repo_name']} — {record['file_path']}](review_packets/{key}.md)")
    (out / "REVIEW_GUIDE.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("results/completion_exploration/stage1"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/completion_exploration/stage2"))
    parser.add_argument("--min-spec-commits", type=int, default=2)
    parser.add_argument("--sample-size", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        names = ["specifications", "task_links", "task_documents", "spec_history"]
        paths = {name: args.input_dir / f"{name}.parquet" for name in names}
        tables = {name: pd.read_parquet(path) for name, path in paths.items()}
        screening, evidence, audit = evaluate_specs(
            tables["specifications"], tables["task_links"], tables["task_documents"], args.min_spec_commits)
        candidates = screening[screening.is_completion_candidate].sort_values("file_url_sha16").reset_index(drop=True)
        sample = select_review_sample(candidates, args.sample_size, args.seed)
        sample["review_packet"] = sample.file_url_sha16.map(lambda key: f"review_packets/{key}.md")
        review_columns = ["file_url_sha16", "repo_name", "spec_tool", "file_path", "file_url",
                          "exp_spec_distinct_commits", "linked_task_documents", "total_task_checkboxes",
                          "task_paths_json", "task_count_disagreement", "review_group_id", "review_packet"]
        review = sample[[col for col in review_columns if col in sample]].copy()
        for col in ["manual_status", "manual_scope_match", "manual_evidence_url", "manual_outcome_date",
                    "manual_notes", "reviewer", "reviewed_at"]:
            review[col] = ""
        review_path = args.output_dir / "completion_review.csv"
        review_action = "created"
        if review_path.exists():
            previous = pd.read_csv(review_path, dtype=str, keep_default_na=False)
            if ("file_url_sha16" not in previous
                    or previous.file_url_sha16.tolist() != review.file_url_sha16.astype(str).tolist()):
                raise ValueError("Existing completion_review.csv has a different sample. Use a new output directory to preserve manual work.")
            review_action = "preserved"
        args.output_dir.mkdir(parents=True, exist_ok=True)
        screening.to_parquet(args.output_dir / "screening.parquet", index=False)
        candidates.to_parquet(args.output_dir / "completion_candidates.parquet", index=False)
        sample.to_parquet(args.output_dir / "review_sample.parquet", index=False)
        audit.to_parquet(args.output_dir / "task_checklist_audit.parquet", index=False)
        selected_evidence = evidence[evidence.file_url_sha16.isin(candidates.file_url_sha16)]
        selected_evidence.to_parquet(args.output_dir / "candidate_task_evidence.parquet", index=False)
        tables["spec_history"][tables["spec_history"].file_url_sha16.isin(candidates.file_url_sha16)].to_parquet(
            args.output_dir / "candidate_history.parquet", index=False)
        if review_action == "created":
            for col in review.select_dtypes(include=["object", "string"]).columns:
                review[col] = review[col].map(csv_safe)
            review.to_csv(review_path, index=False, encoding="utf-8-sig")
        pr_path = args.input_dir / "spec_pr_evidence.parquet"
        prs = pd.read_parquet(pr_path) if pr_path.is_file() else None
        if pr_path.is_file():
            paths["spec_pr_evidence"] = pr_path
        write_review_packets(sample, tables["specifications"], tables["spec_history"],
                             evidence, tables["task_documents"], args.output_dir, prs)
        cumulative = [
            ("all_source_specs", pd.Series(True, index=screening.index)),
            ("non_archived_specs", ~screening.exp_spec_is_archived),
            ("multiple_spec_commits", screening.exp_meets_minimum_commits),
            ("task_content_available", screening.all_task_content_available),
            ("non_archived_task_documents", ~screening.any_task_document_archived),
            ("all_nonempty_checklists_checked", screening.all_task_checklists_checked),
        ]
        mask = pd.Series(True, index=screening.index)
        funnel = {}
        for label, condition in cumulative:
            mask &= condition
            funnel[label] = int(mask.sum())
        exclusions = screening.exclusion_reasons.str.split(";").explode()
        manifest = {
            "experiment": "completion_full_history_v1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "Broad-census local task evidence; full available history; no temporal prediction window",
            "candidate_is_not_outcome_label": True,
            "filters": {"exclude_archived_spec_and_task_paths": True,
                        "min_distinct_specification_commits": args.min_spec_commits,
                        "all_linked_task_documents_known_nonempty_and_checked": True},
            "input_hashes": {name: sha256_file(path) for name, path in paths.items()},
            "script_sha256": sha256_file(Path(__file__)),
            "python": platform.python_version(), "pandas": pd.__version__, "pyarrow": pyarrow.__version__,
            "filter_funnel": funnel,
            "exclusion_reason_counts_overlapping": {k: int(v) for k, v in exclusions[exclusions.ne("")].value_counts().items()},
            "candidate_rows": len(candidates), "candidate_repositories": int(candidates.repo_name.nunique()),
            "candidate_review_groups": int(candidates.review_group_id.nunique()),
            "candidate_tools": {str(k): int(v) for k, v in candidates.spec_tool.value_counts().items()},
            "candidate_count_disagreements": int(candidates.task_count_disagreement.sum()),
            "review_rows": len(sample), "review_repositories": int(sample.repo_name.nunique()),
            "sample_size_requested": args.sample_size, "seed": args.seed,
            "sampling": "Purposive: one representative per shared task-path set; repositories round-robin; seeded hash order",
            "review_csv_action": review_action,
        }
        (args.output_dir / "summary.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"filter_funnel": funnel, "candidate_repositories": manifest["candidate_repositories"],
                          "review_rows": len(sample), "review_csv": str(review_path),
                          "review_csv_action": review_action}, indent=2))
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f"Completion screening error: {exc}\n")


if __name__ == "__main__":
    main()
