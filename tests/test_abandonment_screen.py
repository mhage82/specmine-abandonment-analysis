import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from abandonment_screen import screen, evaluate, run, COLUMNS


def record(ident='a',text='---\nstatus: active\n---\n'):
    return dict(zip(COLUMNS,[ident,'owner/repo','spec.md','https://example.org/spec',text,
        '2026-01-01T00:00:00Z','2026-07-01T00:00:00Z',3,1,False]))

class ScreeningTests(unittest.TestCase):
    def test_prose_not_status(self):
        r=screen(record(text='A cancelled request returns an error.'),None,90)
        self.assertFalse(r['baseline_flag'])
    def test_conflict_and_supersession(self):
        row=record(text='---\nstatus: abandoned\n---\n')
        r=screen(row,{'source_status':'completed'},90)
        self.assertTrue(r['status_conflict']);self.assertFalse(r['candidate_flag'])
        r=screen(row,{'source_reason':'Superseded by another implementation'},90)
        self.assertTrue(r['baseline_flag']);self.assertFalse(r['candidate_flag'])
    def test_missing_and_future_dates(self):
        row=record();row['exp_last_commit_at']='2027-01-01'
        self.assertFalse(screen(row,None,90)['candidate_flag'])
        row=record();row['feature_n_checked']=None;row['feature_has_unfilled_placeholder']=None
        self.assertFalse(screen(row,None,90)['candidate_flag'])
    def test_unknown_never_negative(self):
        rows=[{'file_url_sha16':'a','baseline_flag':True,'candidate_flag':True}]
        m=evaluate(rows,[{'file_url_sha16':'a','split':'evaluation','outcome':'unclear'}])
        self.assertEqual(m['resolved'],0);self.assertIsNone(m['models']['candidate_flag']['precision'])
    def test_development_excluded(self):
        rows=[{'file_url_sha16':'a','baseline_flag':True,'candidate_flag':False}]
        self.assertEqual(evaluate(rows,[{'file_url_sha16':'a','split':'development','outcome':'abandoned'}])['resolved'],0)
    def test_metrics(self):
        rows=[{'file_url_sha16':str(i),'baseline_flag':True,'candidate_flag':i<2} for i in range(3)]
        labels=[{'file_url_sha16':str(i),'split':'evaluation','outcome':o} for i,o in enumerate(['abandoned','superseded','abandoned'])]
        m=evaluate(rows,labels)['models']['candidate_flag']
        self.assertEqual((m['tp'],m['fp'],m['fn']),(1,1,1));self.assertEqual(m['precision'],0.5)
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);stage=p/'stage1';stage.mkdir()
            pd.DataFrame([record('a'),record('b','---\nstatus: completed\n---\n')]).to_parquet(stage/'specifications.parquet',index=False)
            args=SimpleNamespace(stage1_dir=stage,output_dir=p/'out',stale_days=90,sample_per_stratum=15,seed=42,labels=None,evidence=None)
            run(args)
            self.assertEqual(len(json.loads((p/'out/review_sample.json').read_text())),2)
            self.assertEqual(json.loads((p/'out/evaluation.json').read_text())['status'],'not_evaluated_no_resolved_evaluation_labels')
            with self.assertRaises(ValueError):run(args)

if __name__=='__main__':unittest.main()
