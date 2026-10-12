import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from exploratory_analysis import indicator_summary


class IndicatorTests(unittest.TestCase):
    def test_unknown_values_do_not_become_negative_cases(self):
        f = pd.DataFrame({"feature_n_todo": [1, 0, None, -1],
                          "feature_has_unfilled_placeholder": [1, 0, None, 2],
                          "feature_n_checkboxes": [3, 2, None, 1],
                          "feature_n_checked": [1, 2, 0, 2]})
        for row in indicator_summary(f).itertuples():
            self.assertEqual(row.positive, 1)
            self.assertEqual(row.observed, 2)
            self.assertEqual(row.unknown, 2)
            self.assertEqual(row.percent_of_observed, 50)

    def test_all_unknown_has_undefined_percentage(self):
        f = pd.DataFrame({c: [None] for c in ["feature_n_todo", "feature_has_unfilled_placeholder",
                                              "feature_n_checkboxes", "feature_n_checked"]})
        r = indicator_summary(f)
        self.assertTrue(r.percent_of_observed.isna().all())
        self.assertTrue(r.observed.eq(0).all())


if __name__ == "__main__":
    unittest.main()
