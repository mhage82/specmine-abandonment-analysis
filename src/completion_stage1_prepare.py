"""Prepare local, full-history evidence for exploratory completion review.

This standalone stage does not import the existing feature pipeline. It keeps
one row per broad-census specification and separate one-to-many evidence tables.
It assigns no outcome labels, does not download GitHub data, and applies no
90-day window. Kiro tables have a different grain and are outside this stage.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import pandas as pd
import pyarrow


KEY = "file_url_sha16"
REPO_ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    absent = sorted(set(columns) - set(frame.columns))
    if absent:
        raise ValueError(f"{name}: missing required columns: {absent}")


def require_unique(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    require_columns(frame, columns, name)
    if frame[columns].isna().any().any():
        raise ValueError(f"{name}: null identifier in {columns}")
    for column in columns:
        if frame[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"{name}: blank identifier in {column}")
    if frame.duplicated(columns).any():
        raise ValueError(f"{name}: duplicate identifiers in {columns}; refusing silent deduplication")


def stable_task_id(repo: str, path: str) -> str:
    """ID identifies a repository/path document, not a document version."""
    payload = json.dumps([repo, path], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_task_path(value: object) -> bool:
    return isinstance(value, str) and value.rsplit("/", 1)[-1].casefold() == "tasks.md"


def read_spec_markdown(path: Path) -> tuple[dict[str, str | None], dict[str, int]]:
    """Permit identical repeated JSON records, fail on conflicting contents."""
    contents: dict[str, str | None] = {}
    stats = {"rows": 0, "identical_duplicate_keys": 0}
    with gzip.open(path, "rt", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            item = json.loads(line)
            key = item.get(KEY)
            if not isinstance(key, str) or not key.strip():
                raise ValueError(f"{path.name}:{line_number}: missing specification identifier")
            content = item.get("content")
            if content is not None and not isinstance(content, str):
                raise ValueError(f"{path.name}:{line_number}: content must be text or null")
            if key in contents:
                if contents[key] != content:
                    raise ValueError(f"{path.name}: conflicting Markdown for {key}")
                stats["identical_duplicate_keys"] += 1
            contents[key] = content
            stats["rows"] += 1
    return contents, stats


def summarize_history(history: pd.DataFrame) -> pd.DataFrame:
    require_columns(history, [KEY, "commit_sha", "committed_at"], "spec_file_commits")
    work = history[[KEY, "commit_sha", "committed_at"]].copy()
    work["valid_sha"] = work["commit_sha"].astype("string").str.strip().replace("", pd.NA)
    work["parsed_date"] = pd.to_datetime(work["committed_at"], errors="coerce", utc=True, format="mixed")
    work["invalid_date"] = work["parsed_date"].isna().astype("int64")
    return work.groupby(KEY, dropna=False).agg(
        exp_history_rows=("commit_sha", "size"),
        exp_spec_distinct_commits=("valid_sha", "nunique"),
        exp_first_commit_at=("parsed_date", "min"),
        exp_last_commit_at=("parsed_date", "max"),
        exp_invalid_commit_dates=("invalid_date", "sum"),
    ).reset_index()


def task_urls(row: pd.Series) -> dict[str, str | None]:
    """Use the spec's URL ref; task snapshot correspondence is NOT verified."""
    repo, spec_path, task_path = row["repo_name"], row["spec_file_path"], row["task_path"]
    original = row.get("file_url")
    result: dict[str, str | None] = {
        "task_url_at_spec_revision": None,
        "task_history_url": None,
        "task_url_current_branch": None,
        "task_url_revision": None,
        "task_url_revision_status": "unavailable",
    }
    if isinstance(original, str):
        parsed = urlsplit(original)
        decoded = unquote(parsed.path)
        prefix = f"/{repo}/blob/"
        suffix = "/" + spec_path
        if parsed.hostname == "github.com" and decoded.startswith(prefix) and decoded.endswith(suffix):
            ref = decoded[len(prefix):-len(suffix)]
            if ref:
                base = f"https://github.com/{repo}"
                result.update(
                    task_url_at_spec_revision=f"{base}/blob/{quote(ref, safe='/')}/{quote(task_path, safe='/')}",
                    task_history_url=f"{base}/commits/{quote(ref, safe='/')}/{quote(task_path, safe='/')}",
                    task_url_revision=ref,
                    task_url_revision_status="derived_from_spec_url_not_verified_against_task_snapshot",
                )
    branch = row.get("repo_default_branch")
    if isinstance(branch, str) and branch.strip():
        result["task_url_current_branch"] = (
            f"https://github.com/{repo}/blob/{quote(branch, safe='/')}/{quote(task_path, safe='/')}"
        )
    return result


def build_task_tables(
    specifications: pd.DataFrame, references: pd.DataFrame, artifacts: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    require_unique(artifacts, ["repo_name", "file_path"], "openspec_artifact_files")
    tasks = artifacts.loc[artifacts["file_path"].map(is_task_path)].copy()
    tasks = tasks.rename(columns={
        "file_path": "task_path", "content": "task_content", "fetch_status": "task_fetch_status",
        "content_sha": "task_content_sha", "n_tasks": "source_n_tasks",
        "n_tasks_done": "source_n_tasks_done", "fetched_at": "task_fetched_at",
    })
    tasks["task_document_id"] = [stable_task_id(r, p) for r, p in zip(tasks.repo_name, tasks.task_path)]
    task_columns = ["task_document_id", "repo_name", "task_path", "task_content", "task_fetch_status",
                    "task_content_sha", "source_n_tasks", "source_n_tasks_done", "task_fetched_at"]
    tasks = tasks[task_columns].sort_values(["repo_name", "task_path"], kind="stable").reset_index(drop=True)
    require_unique(tasks, ["task_document_id"], "task_documents")

    matching = references.loc[references["rel"].eq("sibling") & references["target"].map(is_task_path)]
    relations = matching[[KEY, "target"]].rename(columns={"target": "task_path"})
    source_relations = len(relations)
    relations = relations.drop_duplicates([KEY, "task_path"])
    spec_meta = specifications[[KEY, "repo_name", "file_path", "file_url", "repo_default_branch"]]
    relations = relations.merge(spec_meta, on=KEY, how="inner", validate="many_to_one")
    relations = relations.rename(columns={"file_path": "spec_file_path"})
    relations["task_document_id"] = [stable_task_id(r, p) for r, p in zip(relations.repo_name, relations.task_path)]
    relations["task_document_found"] = relations["task_document_id"].isin(tasks["task_document_id"])
    url_columns = list(task_urls(pd.Series({"repo_name": "r", "spec_file_path": "s", "task_path": "t"})))
    urls = pd.DataFrame([task_urls(row) for _, row in relations.iterrows()], columns=url_columns, index=relations.index)
    relations = pd.concat([relations.drop(columns=["file_url", "repo_default_branch"]), urls], axis=1)
    relations = relations.sort_values([KEY, "task_path"], kind="stable").reset_index(drop=True)
    stats = {
        "task_link_source_rows": source_relations,
        "task_link_duplicate_relations_removed": source_relations - len(matching[[KEY, "target"]].drop_duplicates()),
        "task_links_without_local_document": int((~relations.task_document_found).sum()),
        "specifications_with_task_link": int(relations[KEY].nunique()),
        "specifications_with_local_task_document": int(relations.loc[relations.task_document_found, KEY].nunique()),
        "task_documents_with_null_content": int(tasks.task_content.isna().sum()),
    }
    return relations, tasks, stats


def parse_pr_target(target: object, default_repo: str) -> tuple[str, int] | None:
    if not isinstance(target, str):
        return None
    local = re.fullmatch(r"#(\d+)", target.strip())
    if local:
        return default_repo, int(local.group(1))
    qualified = re.fullmatch(r"([^/\s]+/[^#\s]+)#(\d+)", target.strip())
    if qualified:
        return qualified.group(1), int(qualified.group(2))
    remote = re.fullmatch(r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)(?:[/?#].*)?", target.strip())
    if remote:
        return remote.group(1), int(remote.group(2))
    return None


def build_pr_evidence(
    specifications: pd.DataFrame, references: pd.DataFrame, prs: pd.DataFrame, pr_files: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Links are review leads, never proof that the specification was completed."""
    require_unique(prs, ["tool", "repo_name", "pr_number"], "pull_requests")
    spec_paths = specifications[[KEY, "repo_name", "file_path"]]
    paths = pr_files[["repo_name", "file_path", "pr_number"]].drop_duplicates()
    matched = spec_paths.merge(paths, on=["repo_name", "file_path"], how="inner")
    matched = matched[[KEY, "repo_name", "pr_number"]].drop_duplicates()
    matched["relation"] = "pr_changes_spec_path"
    repo_lookup = specifications.set_index(KEY)["repo_name"].to_dict()
    explicit = []
    unparsed = 0
    for row in references.loc[references.rel.eq("pr")].itertuples(index=False):
        spec_id = getattr(row, KEY)
        if spec_id not in repo_lookup:
            continue
        parsed = parse_pr_target(row.target, repo_lookup[spec_id])
        if parsed is None:
            unparsed += 1
        else:
            explicit.append({KEY: spec_id, "repo_name": parsed[0], "pr_number": parsed[1], "relation": "explicit_pr_reference"})
    explicit_frame = pd.DataFrame(explicit, columns=[KEY, "repo_name", "pr_number", "relation"])
    edges = pd.concat([matched, explicit_frame], ignore_index=True).drop_duplicates()
    metadata = prs.rename(columns={c: "pr_" + c for c in prs if c not in {"repo_name", "pr_number"}})
    # Source PRs are collected per tool, so multiple metadata records can exist
    # for one physical PR. Preserve that provenance instead of silently picking.
    evidence = edges.merge(metadata, on=["repo_name", "pr_number"], how="left", indicator=True)
    evidence["pr_metadata_found"] = evidence.pop("_merge").eq("both")
    evidence["pr_url"] = [f"https://github.com/{r}/pull/{int(n)}" for r, n in zip(evidence.repo_name, evidence.pr_number)]
    evidence = evidence.sort_values([KEY, "repo_name", "pr_number", "relation", "pr_tool"], kind="stable").reset_index(drop=True)
    return evidence, {
        "unparsed_explicit_pr_reference_rows": unparsed,
        "spec_pr_relations": len(edges),
        "spec_pr_evidence_rows_without_metadata": int((~evidence.pr_metadata_found).sum()),
        "source_pr_records_duplicating_physical_pr": int(prs.duplicated(["repo_name", "pr_number"]).sum()),
    }


def prepare(data_dir: Path, output_dir: Path) -> dict:
    names = ["spec_files", "spec_content_features", "spec_file_commits", "spec_links", "openspec_artifact_files"]
    optional_names = ["pull_requests", "pr_files", "openspec_code_refs"]
    paths = {name: data_dir / (name + ".parquet") for name in names}
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Required input {name}: {path}")
    for name in optional_names:
        if (data_dir / (name + ".parquet")).is_file():
            paths[name] = data_dir / (name + ".parquet")
    tables = {name: pd.read_parquet(path) for name, path in paths.items()}
    specs, features, history = (tables[n] for n in names[:3])
    require_unique(specs, [KEY], "spec_files")
    require_unique(features, [KEY], "spec_content_features")
    require_columns(specs, ["repo_name", "file_path", "file_url", "repo_default_branch"], "spec_files")
    if any(c.startswith("exp_") for c in specs.columns):
        raise ValueError("spec_files: exp_ namespace already used")
    feature_names = {c: "feature_" + c for c in features if c != KEY}
    if set(feature_names.values()) & set(specs.columns):
        raise ValueError("Prefixed feature columns collide with original specification columns")
    base = specs.merge(features.rename(columns=feature_names), on=KEY, how="left", validate="one_to_one")
    base = base.merge(summarize_history(history), on=KEY, how="left", validate="one_to_one")
    for column in ["exp_history_rows", "exp_spec_distinct_commits", "exp_invalid_commit_dates"]:
        base[column] = base[column].fillna(0).astype("int64")
    markdown_path = data_dir.parent / "specs.jsonl.gz"
    markdown_stats: dict = {"available": markdown_path.is_file()}
    if markdown_path.is_file():
        contents, stats = read_spec_markdown(markdown_path)
        markdown_stats.update(stats)
        markdown_stats["unknown_specification_keys"] = len(set(contents) - set(specs[KEY]))
        base["exp_spec_markdown"] = base[KEY].map(contents).astype("string")
        paths["specs_jsonl_gz"] = markdown_path
    else:
        base["exp_spec_markdown"] = pd.Series(pd.NA, index=base.index, dtype="string")
    base = base.sort_values(KEY, kind="stable").reset_index(drop=True)
    references = tables["spec_links"].rename(columns={"spec_url_sha16": KEY})
    require_columns(references, [KEY, "rel", "target"], "spec_links")
    task_links, task_documents, task_stats = build_task_tables(base, references, tables["openspec_artifact_files"])
    outputs = {
        "specifications": base,
        "spec_history": history.sort_values([KEY, "seq_from_oldest", "commit_sha"], kind="stable").reset_index(drop=True),
        "spec_references": references.sort_values([KEY, "rel", "target"], kind="stable").reset_index(drop=True),
        "task_links": task_links,
        "task_documents": task_documents,
    }
    optional_stats = {}
    if {"pull_requests", "pr_files"}.issubset(tables):
        outputs["spec_pr_evidence"], optional_stats = build_pr_evidence(base, references, tables["pull_requests"], tables["pr_files"])
    if "openspec_code_refs" in tables:
        outputs["artifact_code_refs"] = tables["openspec_code_refs"].sort_values(["repo_name", "artifact_path", "code_path", "id"], kind="stable").reset_index(drop=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_details = {}
    for name, frame in outputs.items():
        output = output_dir / (name + ".parquet")
        frame.to_parquet(output, index=False)
        output_details[name] = {"path": str(output.resolve()), "rows": len(frame), "columns": len(frame.columns), "sha256": sha256_file(output)}
    spec_keys = set(specs[KEY])
    summary = {
        "stage": "completion_stage1_prepare", "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "all broad-census spec_files records; Kiro tables excluded because their document grain and join keys differ",
        "history_scope": "all locally recorded specification-file history; no temporal cutoff; no additional GitHub fetches or rename-history reconstruction",
        "outcome_labels_assigned": False,
        "task_url_caveat": "URLs use the specification URL revision; downloaded task content has no verified matching commit revision",
        "task_snapshot_caveat": "Task content and specification history may have been fetched at different dates; neither source task counts nor task content establishes an outcome date",
        "pr_evidence_caveat": "PR links, cochanged files, and merged state are review leads, not automatic completion evidence",
        "versions": {"python": platform.python_version(), "pandas": pd.__version__, "pyarrow": pyarrow.__version__},
        "script": {"path": str(Path(__file__).resolve()), "sha256": sha256_file(Path(__file__))},
        "inputs": {name: {"path": str(path.resolve()), "sha256": sha256_file(path), "rows": len(tables[name]) if name in tables else markdown_stats.get("rows")} for name, path in paths.items()},
        "outputs": output_details,
        "coverage": {
            "specifications": len(base), "repositories": int(base.repo_name.nunique()),
            "duplicate_repo_path_records_preserved": int(base.duplicated(["repo_name", "file_path"]).sum()),
            "feature_keys_without_specification": len(set(features[KEY]) - spec_keys),
            "specifications_without_features": len(spec_keys - set(features[KEY])),
            "history_rows_without_specification": int((~history[KEY].isin(spec_keys)).sum()),
            "reference_rows_without_specification": int((~references[KEY].isin(spec_keys)).sum()),
            "specifications_without_markdown": int(base.exp_spec_markdown.isna().sum()),
            "specifications_with_at_least_two_distinct_commits": int(base.exp_spec_distinct_commits.ge(2).sum()),
            **task_stats, **optional_stats,
        },
        "markdown": markdown_stats,
        "optional_inputs_not_present": sorted(set(optional_names) - set(tables)),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data/raw/specmine-official/data")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "results/completion_exploration/stage1")
    args = parser.parse_args()
    summary = prepare(args.data_dir.resolve(), args.output_dir.resolve())
    print(json.dumps({"output_dir": str(args.output_dir.resolve()), "coverage": summary["coverage"], "output_rows": {n: v["rows"] for n, v in summary["outputs"].items()}}, indent=2))


if __name__ == "__main__":
    main()
