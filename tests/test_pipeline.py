import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feature_pipeline import build_analysis_table


class PipelineTests(unittest.TestCase):
    def fixture(self):
        return {
            "spec_files": pd.DataFrame({"file_url_sha16": ["a", "b", "c"]}),
            "spec_content_features": pd.DataFrame({"file_url_sha16": ["a"], "n_todo": [2]}),
            "spec_file_commits": pd.DataFrame({
                "file_url_sha16": ["a", "a", "a", "c"],
                "commit_sha": ["x", "y", "y", "z"],
                "committed_at": ["2026-01-01T00:00:00Z", "2026-01-03T00:00:00Z",
                                 "2026-01-03T00:00:00Z", "bad-date"]}),
        }

    def test_grain_missingness_dates_and_duplicate_commits(self):
        result, audit = build_analysis_table(self.fixture())
        result = result.set_index("file_url_sha16")
        self.assertEqual(len(result), 3)
        self.assertEqual(result.loc["a", "pipeline_distinct_commit_count"], 2)
        self.assertEqual(result.loc["a", "pipeline_history_rows"], 3)
        self.assertEqual(result.loc["a", "pipeline_observed_history_span_days"], 2)
        self.assertTrue(pd.isna(result.loc["b", "feature_n_todo"]))
        self.assertFalse(result.loc["b", "pipeline_has_history_rows"])
        self.assertTrue(pd.isna(result.loc["c", "pipeline_last_observed_commit_at"]))
        self.assertEqual(audit["unparseable_commit_dates"], 1)
        self.assertEqual(audit["duplicate_spec_commit_rows"], 1)

    def test_ambiguous_feature_join_fails(self):
        tables = self.fixture()
        tables["spec_content_features"] = pd.concat([tables["spec_content_features"]] * 2)
        with self.assertRaisesRegex(ValueError, "duplicate specification keys"):
            build_analysis_table(tables)

    def test_missing_key_fails(self):
        tables = self.fixture()
        tables["spec_files"].loc[0, "file_url_sha16"] = None
        with self.assertRaisesRegex(ValueError, "missing/blank"):
            build_analysis_table(tables)

    def test_empty_history_and_orphan_feature(self):
        tables = self.fixture()
        tables["spec_file_commits"] = tables["spec_file_commits"].iloc[:0]
        tables["spec_content_features"].loc[0, "file_url_sha16"] = "orphan"
        result, audit = build_analysis_table(tables)
        self.assertEqual(len(result), 3)
        self.assertEqual(audit["feature_rows_without_spec"], 1)
        self.assertEqual(audit["specs_without_history"], 3)


if __name__ == "__main__":
    unittest.main()
