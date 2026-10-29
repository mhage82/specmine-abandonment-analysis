"""Evidence-aware baseline status must not confuse inactivity with completion."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from completion_stage6_status import add_cutoff_status


KEY = "file_url_sha16"
ADDED_FIELDS = [
    "status_at_cutoff", "completed_by_cutoff", "has_recent_spec_commit",
    "cutoff_status_reason", "cutoff_status_evidence_url",
    "cutoff_status_evidence_date", "training_row_action",
]


class CutoffStatusTests(unittest.TestCase):
    @staticmethod
    def fixture():
        # Input rows intentionally have different ordering across tables.
        dataset = pd.DataFrame([
            {KEY: "b" * 16, "manual_status": "unclear",
             "prediction_at": pd.Timestamp("2026-01-08T12:00:00Z"),
             "window_observed": True, "prefix_commits_last_7_days": 0.0,
             "example_original_feature": 17},
            {KEY: "a" * 16, "manual_status": "completed",
             "prediction_at": pd.Timestamp("2026-01-08T12:00:00Z"),
             "window_observed": True, "prefix_commits_last_7_days": 3.0,
             "example_original_feature": 29},
        ])
        audit = pd.DataFrame([
            {KEY: "a" * 16, "full_history_commit_count": 100},
            {KEY: "b" * 16, "full_history_commit_count": 999},
        ])
        review = pd.DataFrame([
            {KEY: "a" * 16, "manual_status": "completed",
             "manual_outcome_date": "2026-01-07",
             "manual_evidence_url": "https://example.org/a", "manual_notes": "Evidence"},
            {KEY: "b" * 16, "manual_status": "unclear",
             "manual_outcome_date": "", "manual_evidence_url": "https://example.org/b"},
        ])
        return dataset, audit, review

    def test_original_rows_values_labels_and_order_are_preserved(self):
        dataset, audit, review = self.fixture()
        original = dataset.copy(deep=True)
        result = add_cutoff_status(dataset, audit, review)
        self.assertEqual(result[KEY].tolist(), dataset[KEY].tolist())
        self.assertEqual(len(result), len(dataset))
        pd.testing.assert_frame_equal(result[dataset.columns].reset_index(drop=True), original)
        pd.testing.assert_frame_equal(dataset, original)
        self.assertTrue(set(ADDED_FIELDS).issubset(result.columns))
        self.assertNotIn("active_at_cutoff", result.columns)
        self.assertEqual(str(result.completed_by_cutoff.dtype), "boolean")
        self.assertEqual(str(result.has_recent_spec_commit.dtype), "boolean")
        self.assertFalse(result.completed_by_cutoff.eq(False).fillna(False).any())

    def test_unclear_is_unknown_not_inactive_despite_no_recent_commit(self):
        result = add_cutoff_status(*self.fixture()).set_index(KEY)
        row = result.loc["b" * 16]
        self.assertEqual(row.status_at_cutoff, "unknown")
        self.assertTrue(pd.isna(row.completed_by_cutoff))
        self.assertFalse(row.has_recent_spec_commit)
        self.assertEqual(row.training_row_action, "needs_baseline_review")
        self.assertTrue(pd.isna(row.cutoff_status_evidence_date) or row.cutoff_status_evidence_date == "")
        self.assertTrue(pd.isna(row.cutoff_status_evidence_url) or row.cutoff_status_evidence_url == "")
        self.assertTrue(str(row.cutoff_status_reason).strip())

    def test_documented_completion_precedes_cutoff_even_with_recent_edits(self):
        result = add_cutoff_status(*self.fixture()).set_index(KEY)
        row = result.loc["a" * 16]
        self.assertEqual(row.status_at_cutoff, "completed")
        self.assertTrue(row.completed_by_cutoff)
        self.assertTrue(row.has_recent_spec_commit)
        self.assertEqual(row.training_row_action, "exclude_already_completed")
        self.assertEqual(row.cutoff_status_evidence_date, "2026-01-07")
        self.assertEqual(row.cutoff_status_evidence_url, "https://example.org/a")

    def test_missing_later_or_same_day_completion_date_leaves_baseline_unknown(self):
        for date in ["", None, "2026-01-08", "2026-01-09"]:
            with self.subTest(date=date):
                dataset, audit, review = self.fixture()
                review.loc[review[KEY].eq("a" * 16), "manual_outcome_date"] = date
                row = add_cutoff_status(dataset, audit, review).set_index(KEY).loc["a" * 16]
                self.assertEqual(row.status_at_cutoff, "unknown")
                self.assertTrue(pd.isna(row.completed_by_cutoff))
                self.assertTrue(row.has_recent_spec_commit)
                self.assertEqual(row.training_row_action, "needs_baseline_review")

    def test_recent_activity_alone_cannot_establish_active_scope(self):
        for count in [0, 1, 10]:
            with self.subTest(count=count):
                dataset, audit, review = self.fixture()
                dataset.loc[dataset[KEY].eq("b" * 16), "prefix_commits_last_7_days"] = count
                row = add_cutoff_status(dataset, audit, review).set_index(KEY).loc["b" * 16]
                self.assertEqual(row.status_at_cutoff, "unknown")
                self.assertTrue(pd.isna(row.completed_by_cutoff))
                self.assertEqual(bool(row.has_recent_spec_commit), count > 0)

    def test_last_commit_before_or_after_cutoff_does_not_determine_status(self):
        dataset, audit, review = self.fixture()
        expected = add_cutoff_status(dataset, audit, review)[ADDED_FIELDS]
        for last_date in ["2025-12-31T00:00:00Z", "2026-12-31T00:00:00Z"]:
            with self.subTest(last_date=last_date):
                modified = dataset.copy()
                modified["file_last_commit_at"] = last_date
                changed_audit = audit.copy()
                changed_audit["full_history_commit_count"] = 999999
                changed_audit["post_cutoff_commit_count"] = 100000
                changed_audit["completion_timing"] = "untrusted_future_flag"
                changed_audit["collected_path_has_archive_segment"] = True
                changed_audit["prospective_training_eligible"] = True
                actual = add_cutoff_status(modified, changed_audit, review)
                pd.testing.assert_frame_equal(actual[ADDED_FIELDS], expected)
                self.assertTrue(actual.file_last_commit_at.eq(last_date).all())

    def test_incomplete_window_recent_activity_is_unknown_and_evidence_still_applies(self):
        dataset, audit, review = self.fixture()
        dataset["window_observed"] = False
        dataset["prefix_commits_last_7_days"] = np.nan
        result = add_cutoff_status(dataset, audit, review).set_index(KEY)
        self.assertTrue(result.has_recent_spec_commit.isna().all())
        completed = result.loc["a" * 16]
        self.assertEqual(completed.status_at_cutoff, "completed")
        self.assertTrue(completed.completed_by_cutoff)
        self.assertEqual(completed.training_row_action, "exclude_already_completed")
        unknown = result.loc["b" * 16]
        self.assertEqual(unknown.status_at_cutoff, "unknown")
        self.assertTrue(pd.isna(unknown.completed_by_cutoff))
        self.assertEqual(unknown.training_row_action, "exclude_incomplete_window")

    def test_cutoff_date_is_compared_after_utc_normalization(self):
        dataset, audit, review = self.fixture()
        dataset["prediction_at"] = "2026-01-08T23:00:00-05:00"
        review.loc[review[KEY].eq("a" * 16), "manual_outcome_date"] = "2026-01-08"
        row = add_cutoff_status(dataset, audit, review).set_index(KEY).loc["a" * 16]
        self.assertEqual(row.status_at_cutoff, "completed")

    def test_unobserved_window_does_not_expose_recent_activity_from_partial_history(self):
        for count in [0.0, 4.0, np.nan]:
            with self.subTest(count=count):
                dataset, audit, review = self.fixture()
                dataset["window_observed"] = False
                dataset["prefix_commits_last_7_days"] = count
                result = add_cutoff_status(dataset, audit, review)
                self.assertTrue(result.has_recent_spec_commit.isna().all())

    def test_noncompletion_labels_never_become_active_or_completed_automatically(self):
        for label in ["abandoned", "deferred", "in_progress", "unclear"]:
            with self.subTest(label=label):
                dataset, audit, review = self.fixture()
                dataset.loc[dataset[KEY].eq("a" * 16), "manual_status"] = label
                review.loc[review[KEY].eq("a" * 16), "manual_status"] = label
                row = add_cutoff_status(dataset, audit, review).set_index(KEY).loc["a" * 16]
                self.assertEqual(row.status_at_cutoff, "unknown")
                self.assertTrue(pd.isna(row.completed_by_cutoff))

    def test_mismatched_labels_are_rejected(self):
        dataset, audit, review = self.fixture()
        review.loc[review[KEY].eq("a" * 16), "manual_status"] = "unclear"
        with self.assertRaises(ValueError):
            add_cutoff_status(dataset, audit, review)

    def test_prior_completion_requires_a_recorded_evidence_source(self):
        dataset, audit, review = self.fixture()
        review.loc[review[KEY].eq("a" * 16), "manual_evidence_url"] = ""
        with self.assertRaises(ValueError):
            add_cutoff_status(dataset, audit, review)

    def test_prior_completion_requires_scope_confirmation_when_available(self):
        dataset, audit, review = self.fixture()
        review["manual_scope_match"] = "unclear"
        with self.assertRaises(ValueError):
            add_cutoff_status(dataset, audit, review)

    def test_duplicate_missing_or_extra_ids_are_rejected(self):
        for table in range(3):
            for mode in ["duplicate", "missing", "extra"]:
                with self.subTest(table=table, mode=mode):
                    tables = list(self.fixture())
                    frame = tables[table]
                    if mode == "duplicate":
                        tables[table] = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
                    elif mode == "missing":
                        tables[table] = frame.iloc[:1].copy()
                    else:
                        extra = frame.iloc[[0]].copy()
                        extra[KEY] = "c" * 16
                        tables[table] = pd.concat([frame, extra], ignore_index=True)
                    with self.assertRaises(ValueError):
                        add_cutoff_status(*tables)

    def test_invalid_outcome_dates_are_rejected(self):
        for date in ["not a date", "2026-02-30", "2026-01-07T12:00:00Z"]:
            with self.subTest(date=date):
                dataset, audit, review = self.fixture()
                review.loc[review[KEY].eq("a" * 16), "manual_outcome_date"] = date
                with self.assertRaises(ValueError):
                    add_cutoff_status(dataset, audit, review)

    def test_invalid_labels_are_rejected_even_when_they_agree(self):
        dataset, audit, review = self.fixture()
        dataset["manual_status"] = "invented_label"
        review["manual_status"] = "invented_label"
        with self.assertRaises(ValueError):
            add_cutoff_status(dataset, audit, review)

    def test_observed_recent_counts_must_be_finite_nonnegative_integers(self):
        for count in [np.nan, np.inf, -1, 1.5]:
            with self.subTest(count=count):
                dataset, audit, review = self.fixture()
                dataset.loc[dataset[KEY].eq("b" * 16), "prefix_commits_last_7_days"] = count
                with self.assertRaises(ValueError):
                    add_cutoff_status(dataset, audit, review)

    def test_invalid_window_flags_and_cutoff_dates_are_rejected(self):
        for field, value in [("window_observed", "false"), ("window_observed", None),
                             ("prediction_at", "not a date")]:
            with self.subTest(field=field, value=value):
                dataset, audit, review = self.fixture()
                dataset[field] = dataset[field].astype(object)
                dataset.loc[0, field] = value
                with self.assertRaises(ValueError):
                    add_cutoff_status(dataset, audit, review)


if __name__ == "__main__":
    unittest.main()
