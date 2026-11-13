"""Synthetic integration checks; these are not research observations."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from run_abandonment_sensitivity import compare


class SensitivityTests(unittest.TestCase):
    def test_full_runner_and_output_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / 'stage'
            stage.mkdir()
            records = []
            for ident, days, status in [('a', 45, ''), ('b', 100, ''), ('c', 5, 'abandoned'), ('d', 200, 'completed')]:
                end = pd.Timestamp('2026-10-01', tz='UTC')
                records.append({'file_url_sha16': ident, 'repo_name': 'fixture/repo', 'file_path': ident + '.md',
                                'file_url': 'https://example.invalid/' + ident,
                                'exp_spec_markdown': f'---\nstatus: {status}\n---\n' if status else '# Work\n- [ ] Task',
                                'exp_last_commit_at': end - pd.Timedelta(days=days), 'commit_history_fetched_at': end,
                                'feature_n_checkboxes': 1, 'feature_n_checked': 0, 'feature_has_unfilled_placeholder': False})
            pd.DataFrame(records).to_parquet(stage / 'specifications.parquet')
            labels = [dict(file_url_sha16=k, split='evaluation', outcome=outcome, reviewer='Synthetic test',
                           reviewed_at='2026-10-01', evidence_ref='Synthetic fixture', rationale='Test only')
                      for k, outcome in [('a', 'completed'), ('b', 'unclear'), ('c', 'abandoned'), ('d', 'completed')]]
            label_path = root / 'labels.json'
            label_path.write_text(json.dumps(labels), encoding='utf-8')
            output = root / 'results'
            command = [sys.executable, str(ROOT / 'src/run_abandonment_sensitivity.py'), '--stage1-dir', str(stage),
                       '--labels', str(label_path), '--output-dir', str(output)]
            done = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            table = json.loads((output / 'sensitivity_summary.json').read_text())
            self.assertEqual([r['candidate_flags'] for r in table], [3, 2, 2, 1])
            self.assertEqual([r['candidate_flag_fp'] for r in table], [1, 0, 0, 0])
            self.assertEqual([r['candidate_flag_tp'] for r in table], [1, 1, 1, 1])
            self.assertTrue(all(r['unresolved_or_ineligible'] == 1 for r in table))
            self.assertEqual(table[0]['added_vs_reference'], 1)
            self.assertEqual(table[-1]['removed_vs_reference'], 1)
            self.assertTrue((output / 'threshold_comparison.png').is_file())
            before = (output / 'sensitivity_manifest.json').read_bytes()
            repeat = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(repeat.returncode, 0)
            self.assertEqual(before, (output / 'sensitivity_manifest.json').read_bytes())

    def test_reject_different_inputs(self):
        m = dict(version='v', script_sha256='code', inputs_sha256={'labels': 'one'}, seed=42)
        rows = [dict(file_url_sha16='a', candidate_flag=False, baseline_flag=False)]
        e = dict(evaluation_reviewed=0, resolved=0, unresolved_or_ineligible=0, models={})
        altered = dict(m, inputs_sha256={'labels': 'two'})
        with self.assertRaisesRegex(ValueError, 'inputs_sha256'):
            compare({30: (m, rows, e), 90: (altered, rows, e)}, 90)


if __name__ == '__main__':
    unittest.main()
