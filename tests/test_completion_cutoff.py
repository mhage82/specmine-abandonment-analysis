"""Semantic checks for cutoff features, label preservation and temporal leakage."""

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from completion_stage5_cutoff import FEATURE_COLUMNS, KEY, build_cutoff_dataset


class CutoffDatasetTests(unittest.TestCase):
    @staticmethod
    def fixture():
        """Two specs deliberately ordered differently from their identifiers."""
        review = pd.DataFrame([
            {KEY: "b" * 16, "repo_name": "example/project",
             "file_path": "openspec/changes/b/specs/b/spec.md", "review_group_id": "b",
             "manual_status": "unclear", "manual_outcome_date": ""},
            {KEY: "a" * 16, "repo_name": "example/project",
             "file_path": "openspec/changes/a/specs/a/spec.md", "review_group_id": "a",
             "manual_status": "completed", "manual_outcome_date": "2026-01-15"},
        ])
        specifications = pd.DataFrame([
            {KEY: key, "commit_history_status": "done",
             "commit_history_fetched_at": "2026-02-01T00:00:00Z"}
            for key in review[KEY]
        ])
        anchor = pd.Timestamp("2026-01-01T12:00:00Z")
        rows = []
        for index, (day, author) in enumerate([
            (0, " Alice "), (1, "alice"), (3.5, "Bob"), (4, None), (7, " CAROL "),
        ], 1):
            rows.append({KEY: "a" * 16, "commit_sha": f"{index:040x}",
                         "committed_at": (anchor + pd.Timedelta(day, unit="D")).isoformat(),
                         "author_name": author, "message": "Immutable commit message"})
        rows.append({KEY: "b" * 16, "commit_sha": f"{100:040x}",
                     "committed_at": "2026-01-03T07:00:00-05:00",
                     "author_name": "Dana", "message": "First observed commit"})
        return review, specifications, pd.DataFrame(rows)

    def test_ids_order_labels_and_unknown_outcomes_are_preserved(self):
        review, specs, history = self.fixture()
        dataset, _, audit = build_cutoff_dataset(review, specs, history, 7)
        self.assertEqual(dataset[KEY].tolist(), review[KEY].tolist())
        self.assertEqual(dataset.manual_status.tolist(), ["unclear", "completed"])
        self.assertEqual(len(dataset), 2)
        self.assertFalse(audit.prospective_training_eligible.any())
        self.assertEqual(audit.set_index(KEY).loc["b" * 16, "completion_timing"],
                         "not_completed_label")

    def test_cutoff_and_count_boundaries_have_explicit_meaning(self):
        review, specs, history = self.fixture()
        dataset, prefix, _ = build_cutoff_dataset(review, specs, history, 7)
        row = dataset.set_index(KEY).loc["a" * 16]
        self.assertEqual(row.prediction_at, pd.Timestamp("2026-01-08T12:00:00Z"))
        self.assertEqual(row.prefix_commit_count, 5)
        self.assertEqual(row.prefix_active_commit_days, 4)
        self.assertEqual(row.prefix_author_name_count, 3)
        self.assertEqual(row.prefix_missing_author_count, 1)
        self.assertEqual(row.prefix_activity_span_days, 7)
        self.assertEqual(row.prefix_inactive_days_at_cutoff, 0)
        self.assertEqual(row.prefix_mean_commit_gap_days, 1.75)
        self.assertEqual(row.prefix_max_commit_gap_days, 3)
        self.assertEqual(row.prefix_commits_first_half, 3)
        self.assertEqual(row.prefix_commits_second_half, 2)
        self.assertEqual(row.prefix_commits_last_3_days, 1)
        self.assertEqual(row.prefix_commits_last_7_days, 4)
        self.assertEqual(set(prefix.columns), {KEY, "commit_sha", "committed_at", "author_name"})

    def test_future_commit_cannot_change_features(self):
        review, specs, history = self.fixture()
        expected, _, _ = build_cutoff_dataset(review, specs, history, 7)
        future = pd.DataFrame([{
            KEY: "a" * 16, "commit_sha": f"{200:040x}",
            "committed_at": "2026-01-08T12:00:00.000001Z",
            "author_name": "Future contributor", "message": "All work completed",
        }])
        actual, prefix, _ = build_cutoff_dataset(
            review, specs, pd.concat([history, future], ignore_index=True), 7)
        pd.testing.assert_frame_equal(expected[FEATURE_COLUMNS], actual[FEATURE_COLUMNS])
        self.assertNotIn(f"{200:040x}", prefix.commit_sha.tolist())

    def test_snapshot_fields_and_outcome_changes_cannot_change_features(self):
        review, specs, history = self.fixture()
        expected, _, _ = build_cutoff_dataset(review, specs, history, 7)
        specs["feature_n_checked"] = [200, 999]
        specs["repo_archived"] = [True, True]
        specs["exp_spec_distinct_commits"] = [500, 600]
        specs["task_content"] = "- [x] Future task completed"
        specs["repo_stars"] = [2000, 9000]
        review["manual_status"] = ["completed", "unclear"]
        review["manual_outcome_date"] = ["2026-01-05", ""]
        history["message"] = "Future annotations must not become predictors"
        history["comment_count"] = 999
        actual, prefix, _ = build_cutoff_dataset(review, specs, history, 7)
        pd.testing.assert_frame_equal(expected[FEATURE_COLUMNS], actual[FEATURE_COLUMNS])
        self.assertNotIn("comment_count", prefix.columns)
        self.assertFalse(set(FEATURE_COLUMNS) & {
            KEY, "manual_status", "manual_outcome_date", "prediction_at", "window_observed",
            "repo_name", "file_path", "review_group_id", "feature_n_checked", "repo_archived",
        })

    def test_cutoff_after_collection_has_missing_features_without_shortening_window(self):
        review, specs, history = self.fixture()
        specs.loc[specs[KEY].eq("b" * 16), "commit_history_fetched_at"] = "2026-01-05T12:00:00Z"
        dataset, _, _ = build_cutoff_dataset(review, specs, history, 7)
        row = dataset.set_index(KEY).loc["b" * 16]
        self.assertEqual(row.prediction_at, pd.Timestamp("2026-01-10T12:00:00Z"))
        self.assertEqual(row.observation_end_at, pd.Timestamp("2026-01-05T12:00:00Z"))
        self.assertFalse(row.window_observed)
        self.assertTrue(row[FEATURE_COLUMNS].isna().all())

    def test_cutoff_equal_to_collection_is_observed(self):
        review, specs, history = self.fixture()
        specs.loc[specs[KEY].eq("b" * 16), "commit_history_fetched_at"] = "2026-01-10T12:00:00Z"
        dataset, _, _ = build_cutoff_dataset(review, specs, history, 7)
        row = dataset.set_index(KEY).loc["b" * 16]
        self.assertTrue(row.window_observed)
        self.assertEqual(row.prefix_commit_count, 1)

    def test_single_commit_gap_is_unknown_and_offset_is_normalized(self):
        dataset, _, _ = build_cutoff_dataset(*self.fixture(), 7)
        row = dataset.set_index(KEY).loc["b" * 16]
        self.assertEqual(row.first_observed_commit_at, pd.Timestamp("2026-01-03T12:00:00Z"))
        self.assertEqual(row.prefix_activity_span_days, 0)
        self.assertEqual(row.prefix_inactive_days_at_cutoff, 7)
        self.assertTrue(pd.isna(row.prefix_mean_commit_gap_days))
        self.assertTrue(pd.isna(row.prefix_max_commit_gap_days))

    def test_date_only_evidence_does_not_imply_first_completion_or_binary_labels(self):
        for date, expected in [
            ("", "missing_date"), ("2026-01-07", "before_cutoff"),
            ("2026-01-08", "same_day_timing_uncertain"), ("2026-01-09", "after_cutoff"),
        ]:
            with self.subTest(date=date):
                review, specs, history = self.fixture()
                review.loc[review[KEY].eq("a" * 16), "manual_outcome_date"] = date
                _, _, audit = build_cutoff_dataset(review, specs, history, 7)
                row = audit.set_index(KEY).loc["a" * 16]
                self.assertEqual(row.completion_timing, expected)
                self.assertFalse(row.prospective_training_eligible)

    def test_duplicate_specification_identifiers_are_rejected(self):
        for table in ("review", "specifications"):
            with self.subTest(table=table):
                review, specs, history = self.fixture()
                if table == "review":
                    review = pd.concat([review, review.iloc[[0]]], ignore_index=True)
                else:
                    specs = pd.concat([specs, specs.iloc[[0]]], ignore_index=True)
                with self.assertRaises(ValueError):
                    build_cutoff_dataset(review, specs, history, 7)

    def test_duplicate_commits_are_rejected_instead_of_counted_twice(self):
        review, specs, history = self.fixture()
        history = pd.concat([history, history.iloc[[0]]], ignore_index=True)
        with self.assertRaises(ValueError):
            build_cutoff_dataset(review, specs, history, 7)

    def test_missing_selected_history_is_rejected(self):
        review, specs, history = self.fixture()
        history = history.loc[history[KEY].ne("b" * 16)]
        with self.assertRaises(ValueError):
            build_cutoff_dataset(review, specs, history, 7)

    def test_invalid_commit_and_collection_dates_are_rejected(self):
        for field in ("committed_at", "commit_history_fetched_at"):
            with self.subTest(field=field):
                review, specs, history = self.fixture()
                if field == "committed_at":
                    history.loc[0, field] = "not a date"
                else:
                    specs.loc[0, field] = "not a date"
                with self.assertRaises(ValueError):
                    build_cutoff_dataset(review, specs, history, 7)

    def test_unfinished_history_collection_is_rejected(self):
        review, specs, history = self.fixture()
        specs.loc[0, "commit_history_status"] = "partial"
        with self.assertRaises(ValueError):
            build_cutoff_dataset(review, specs, history, 7)

    def test_history_after_collection_is_rejected(self):
        review, specs, history = self.fixture()
        history.loc[0, "committed_at"] = "2026-02-02T00:00:00Z"
        with self.assertRaises(ValueError):
            build_cutoff_dataset(review, specs, history, 7)

    def test_window_must_be_a_positive_integer(self):
        for window in (0, -1, 1.5, True, "7"):
            with self.subTest(window=window), self.assertRaises(ValueError):
                build_cutoff_dataset(*self.fixture(), window)


if __name__ == "__main__":
    unittest.main()
