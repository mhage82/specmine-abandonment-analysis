"""Checks for joins and provenance that affect manual-review selection."""

import gzip
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.completion_stage1_prepare import (
    build_task_tables,
    parse_pr_target,
    read_spec_markdown,
    require_unique,
    summarize_history,
    task_urls,
)


class CompletionStageOneTests(unittest.TestCase):
    def test_mixed_valid_date_formats_remain_observed(self):
        history = pd.DataFrame({
            "file_url_sha16": ["a", "a"], "commit_sha": ["first", "second"],
            "committed_at": ["2026-01-01", "2026-01-03T04:00:00Z"],
        })
        row = summarize_history(history).iloc[0]
        self.assertEqual(row.exp_invalid_commit_dates, 0)
        self.assertEqual(row.exp_last_commit_at, pd.Timestamp("2026-01-03T04:00:00Z"))

    def test_count_distinct_nonblank_commit_sha_not_history_rows(self):
        history = pd.DataFrame({
            "file_url_sha16": ["a"] * 5,
            "commit_sha": ["same", "same", "different", "", None],
            "committed_at": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "2026-01-03T00:00:00Z", "bad", None],
        })
        row = summarize_history(history).iloc[0]
        self.assertEqual(row.exp_spec_distinct_commits, 2)
        self.assertEqual(row.exp_history_rows, 5)
        self.assertEqual(row.exp_invalid_commit_dates, 2)
        self.assertEqual(row.exp_last_commit_at, pd.Timestamp("2026-01-03", tz="UTC"))

    def test_duplicate_keys_fail_instead_of_multiplying_join_rows(self):
        frame = pd.DataFrame({"key": ["same", "same"], "value": [1, 2]})
        with self.assertRaisesRegex(ValueError, "duplicate identifiers"):
            require_unique(frame, ["key"], "test")

    def test_conflicting_raw_markdown_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "specs.jsonl.gz"
            with gzip.open(path, "wt", encoding="utf-8") as target:
                for text in ["original", "different"]:
                    target.write(json.dumps({"file_url_sha16": "a", "content": text}) + "\n")
            with self.assertRaisesRegex(ValueError, "conflicting Markdown"):
                read_spec_markdown(path)

    def test_original_url_reference_is_retained_and_marked_unverified(self):
        row = pd.Series({
            "repo_name": "owner/repo", "spec_file_path": "specs/my feature/spec.md",
            "task_path": "specs/my feature/tasks.md", "repo_default_branch": "main",
            "file_url": "https://github.com/owner/repo/blob/feature/a/specs/my%20feature/spec.md",
        })
        urls = task_urls(row)
        self.assertEqual(urls["task_url_revision"], "feature/a")
        self.assertEqual(urls["task_url_at_spec_revision"], "https://github.com/owner/repo/blob/feature/a/specs/my%20feature/tasks.md")
        self.assertEqual(urls["task_history_url"], "https://github.com/owner/repo/commits/feature/a/specs/my%20feature/tasks.md")
        self.assertIn("not_verified", urls["task_url_revision_status"])

    def test_missing_task_content_is_kept_as_missing_not_fabricated(self):
        specs = pd.DataFrame({
            "file_url_sha16": ["a", "b"], "repo_name": ["owner/repo"] * 2,
            "file_path": ["feature-a/spec.md", "feature-b/spec.md"],
            "file_url": ["https://github.com/owner/repo/blob/abc/feature-a/spec.md", "https://github.com/owner/repo/blob/abc/feature-b/spec.md"],
            "repo_default_branch": ["main"] * 2,
        })
        refs = pd.DataFrame({
            "file_url_sha16": ["a", "b"], "rel": ["sibling", "sibling"],
            "target": ["feature-a/tasks.md", "feature-b/TASKS.md"],
        })
        docs = pd.DataFrame({
            "repo_name": ["owner/repo"], "file_path": ["feature-a/tasks.md"],
            "content": ["- [x] Implement the feature"], "fetch_status": ["done"],
            "content_sha": ["content-hash"], "n_tasks": [1], "n_tasks_done": [1],
            "fetched_at": ["2026-01-01T00:00:00Z"],
        })
        links, documents, stats = build_task_tables(specs, refs, docs)
        self.assertEqual(len(links), 2)
        self.assertEqual(len(documents), 1)
        self.assertEqual(links.set_index("file_url_sha16").task_document_found.to_dict(), {"a": True, "b": False})
        self.assertEqual(stats["task_links_without_local_document"], 1)

    def test_pr_links_respect_explicit_repository(self):
        self.assertEqual(parse_pr_target("#42", "local/repo"), ("local/repo", 42))
        self.assertEqual(parse_pr_target("remote/repo#42", "local/repo"), ("remote/repo", 42))
        self.assertEqual(parse_pr_target("https://github.com/remote/repo/pull/42#discussion", "local/repo"), ("remote/repo", 42))
        self.assertIsNone(parse_pr_target("https://example.com/pull/42", "local/repo"))


if __name__ == "__main__":
    unittest.main()
