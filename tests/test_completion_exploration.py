"""Focused checks for the full-history completion exploration rules."""

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from completion_stage2_candidates import (
    evaluate_specs,
    is_archived_path,
    parse_checklist,
    select_review_sample,
)


class ChecklistParsingTests(unittest.TestCase):
    def test_checked_markers_and_unfinished_task(self):
        result = parse_checklist(
            "# Tasks\n- [x] Done\n* [X] Also done\n+ [x] Done too\n"
            "1. [x] Ordered item\n  - [ ] Remaining task\n"
        )
        self.assertEqual(result["checkbox_count"], 5)
        self.assertEqual(result["checked_count"], 4)
        self.assertEqual(result["unchecked_count"], 1)
        self.assertFalse(result["all_checked"])

    def test_examples_and_comments_do_not_become_task_evidence(self):
        result = parse_checklist(
            "# Actual tasks\n- [x] Implemented\n"
            "```markdown\n- [ ] Backtick example\n```\n"
            "~~~markdown\n- [ ] Tilde example\n~~~\n"
            "<!--\n- [ ] Commented out\n-->\n"
            "> - [ ] Quoted example\n"
        )
        self.assertEqual(result["checkbox_count"], 1)
        self.assertEqual(result["checked_count"], 1)
        self.assertEqual(result["unchecked_count"], 0)
        self.assertTrue(result["all_checked"])

    def test_empty_or_missing_checklist_is_not_completed(self):
        for content in (None, "", "# Tasks\nNo checklist was supplied."):
            with self.subTest(content=content):
                result = parse_checklist(content)
                self.assertEqual(result["checkbox_count"], 0)
                self.assertFalse(result["all_checked"])

    def test_archive_is_a_path_segment_not_a_substring(self):
        for path in (
            "openspec/changes/archive/feature/tasks.md",
            "openspec/changes/ARCHIVED/feature/tasks.md",
            "archive/tasks.md",
            "openspec/design-archive/feature/spec.md",
            "openspec/_archive/feature/spec.md",
            "openspec/archives/feature/spec.md",
            "openspec/design.archive/feature/spec.md",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_archived_path(path))
        for path in (
            "openspec/changes/add-archive-tools/tasks.md",
            "openspec/archive-tools/spec.md",
            "specs/archive-support/spec.md",
            "specs/feature/archive.md",
        ):
            with self.subTest(path=path):
                self.assertFalse(is_archived_path(path))


class CompletionScreeningTests(unittest.TestCase):
    @staticmethod
    def fixture():
        specs = pd.DataFrame(
            [
                {
                    "file_url_sha16": key,
                    "repo_name": "example/project",
                    "file_path": f"openspec/changes/{key}/specs/auth/spec.md",
                    "spec_tool": "openspec",
                    "spec_role": "change_proposal",
                    "exp_spec_distinct_commits": 2,
                }
                for key in ("a", "b", "c")
            ]
        )
        docs = pd.DataFrame(
            [
                {
                    "task_document_id": key,
                    "repo_name": "example/project",
                    "task_path": f"openspec/changes/{key}/tasks.md",
                    "task_content": "- [x] Implement the behavior\n- [x] Add tests\n",
                    "task_fetch_status": "done",
                    "source_n_tasks": 2,
                    "source_n_tasks_done": 2,
                }
                for key in ("tasks-a", "tasks-b", "tasks-extra")
            ]
        )
        links = pd.DataFrame(
            [
                {
                    "file_url_sha16": spec,
                    "repo_name": "example/project",
                    "spec_file_path": specs.set_index("file_url_sha16").loc[spec, "file_path"],
                    "task_path": docs.set_index("task_document_id").loc[doc, "task_path"],
                    "task_document_id": doc,
                    "task_document_found": True,
                }
                for spec, doc in (("a", "tasks-a"), ("b", "tasks-b"))
            ]
        )
        return specs, links, docs

    def screen(self, specs, links, docs, **kwargs):
        screening, evidence, audit = evaluate_specs(specs, links, docs, **kwargs)
        self.assertIsInstance(evidence, pd.DataFrame)
        self.assertIsInstance(audit, pd.DataFrame)
        self.assertEqual(len(screening), len(specs))
        self.assertTrue(screening["file_url_sha16"].is_unique)
        self.assertEqual(set(screening["file_url_sha16"]), set(specs["file_url_sha16"]))
        return screening.set_index("file_url_sha16")

    def test_specs_without_task_links_are_preserved_and_rejected(self):
        result = self.screen(*self.fixture())
        self.assertTrue(result.loc["a", "is_completion_candidate"])
        self.assertTrue(result.loc["b", "is_completion_candidate"])
        self.assertFalse(result.loc["c", "is_completion_candidate"])
        self.assertTrue(result.loc["c", "exclusion_reasons"])

    def test_shared_task_and_repeated_links_do_not_duplicate_specs(self):
        specs, links, docs = self.fixture()
        shared = links.iloc[[0]].copy()
        shared["file_url_sha16"] = "b"
        shared["spec_file_path"] = specs.loc[1, "file_path"]
        links = pd.concat([links.iloc[[0]], links.iloc[[0]], shared], ignore_index=True)
        result = self.screen(specs, links, docs)
        self.assertTrue(result.loc["a", "is_completion_candidate"])
        self.assertTrue(result.loc["b", "is_completion_candidate"])
        self.assertEqual(result.loc["a", "exp_spec_distinct_commits"], 2)

    def test_every_linked_task_document_must_have_a_complete_nonempty_checklist(self):
        specs, links, docs = self.fixture()
        extra = links.iloc[[0]].copy()
        extra["task_document_id"] = "tasks-extra"
        extra["task_path"] = docs.loc[2, "task_path"]
        links = pd.concat([links, extra], ignore_index=True)
        for content in ("- [x] Done\n- [ ] Remaining\n", "# Tasks\nNo checklist"):
            with self.subTest(content=content):
                docs.loc[2, "task_content"] = content
                result = self.screen(specs, links, docs)
                self.assertFalse(result.loc["a", "is_completion_candidate"])
                self.assertTrue(result.loc["b", "is_completion_candidate"])

    def test_missing_linked_document_cannot_count_as_completed(self):
        specs, links, docs = self.fixture()
        links.loc[0, "task_document_found"] = False
        docs = docs.loc[docs["task_document_id"] != "tasks-a"]
        result = self.screen(specs, links, docs)
        self.assertFalse(result.loc["a", "is_completion_candidate"])
        self.assertTrue(result.loc["a", "exclusion_reasons"])

    def test_source_counts_do_not_override_the_actual_markdown(self):
        specs, links, docs = self.fixture()
        docs.loc[0, "task_content"] = "- [x] Done\n- [ ] Still unfinished\n"
        # Source counts still claim 2/2; the document itself must win.
        result = self.screen(specs, links, docs)
        self.assertFalse(result.loc["a", "is_completion_candidate"])
        # A source parser may also miss numbered checklist items entirely.
        docs.loc[0, "task_content"] = "1. [x] Implemented\n2. [x] Tested\n"
        docs.loc[0, ["source_n_tasks", "source_n_tasks_done"]] = 0
        result = self.screen(specs, links, docs)
        self.assertTrue(result.loc["a", "is_completion_candidate"])

    def test_spec_archive_path_or_role_excludes_from_this_exploration(self):
        specs, links, docs = self.fixture()
        specs.loc[0, "file_path"] = "openspec/changes/archive/a/specs/auth/spec.md"
        specs.loc[1, "spec_role"] = "archived"
        result = self.screen(specs, links, docs)
        self.assertFalse(result.loc["a", "is_completion_candidate"])
        self.assertFalse(result.loc["b", "is_completion_candidate"])

    def test_archived_linked_task_excludes_nonarchived_spec(self):
        specs, links, docs = self.fixture()
        archived_path = "openspec/changes/archive/a/tasks.md"
        docs.loc[0, "task_path"] = archived_path
        links.loc[0, "task_path"] = archived_path
        result = self.screen(specs, links, docs)
        self.assertFalse(result.loc["a", "is_completion_candidate"])

    def test_minimum_is_specification_distinct_commits_not_link_count(self):
        specs, links, docs = self.fixture()
        specs.loc[0, "exp_spec_distinct_commits"] = 1
        links = pd.concat([links, links.iloc[[0]], links.iloc[[0]]], ignore_index=True)
        result = self.screen(specs, links, docs, min_commits=2)
        self.assertFalse(result.loc["a", "is_completion_candidate"])
        self.assertTrue(result.loc["b", "is_completion_candidate"])
        stricter = self.screen(specs, links, docs, min_commits=3)
        self.assertFalse(stricter["is_completion_candidate"].any())


class ReviewSelectionTests(unittest.TestCase):
    @staticmethod
    def candidates():
        return pd.DataFrame(
            [
                {
                    "file_url_sha16": key,
                    "repo_name": repo,
                    "file_path": f"specs/{key}/spec.md",
                    "review_group_id": group,
                    "exp_spec_distinct_commits": 3,
                    "is_completion_candidate": True,
                }
                for key, repo, group in (
                    ("a", "owner/one", "group-a"),
                    ("b", "owner/one", "group-a"),
                    ("c", "owner/one", "group-c"),
                    ("d", "owner/two", "group-d"),
                    ("e", "owner/three", "group-e"),
                )
            ]
        )

    def test_selection_is_reproducible_and_prefers_repository_variety(self):
        candidates = self.candidates()
        first = select_review_sample(candidates, size=3, seed=42)
        second = select_review_sample(candidates, size=3, seed=42)
        self.assertEqual(list(first["file_url_sha16"]), list(second["file_url_sha16"]))
        self.assertEqual(len(first), 3)
        self.assertEqual(first["repo_name"].nunique(), 3)
        self.assertTrue(first["review_group_id"].is_unique)

    def test_shared_task_groups_are_not_repeated_even_when_sample_is_large(self):
        result = select_review_sample(self.candidates(), size=10, seed=42)
        self.assertEqual(len(result), 4)
        self.assertTrue(result["review_group_id"].is_unique)


if __name__ == "__main__":
    unittest.main()
