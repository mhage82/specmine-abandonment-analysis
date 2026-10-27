"""Retrospective screening of completion stage-one data; no automatic outcome labels."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import pandas as pd

KEY = 'file_url_sha16'
VERSION = 'screen-v1'
COLUMNS = [KEY, 'repo_name', 'file_path', 'file_url', 'exp_spec_markdown',
           'exp_last_commit_at', 'commit_history_fetched_at',
           'feature_n_checkboxes', 'feature_n_checked', 'feature_has_unfilled_placeholder']
POS = {'abandoned', 'cancelled', 'canceled', 'discontinued'}
DONE = {'completed', 'complete', 'done', 'implemented', 'shipped', 'deployed'}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def clean(value):
    return '' if value is None or pd.isna(value) else str(value)


def status_from_markdown(text):
    # Only a top-level scalar status in the opening frontmatter, never prose/code.
    match = re.match(r'\A\ufeff?\s*---\s*\n(.*?)\n---(?:\s|$)', text, re.S)
    if not match:
        return '', False
    values = re.findall(r'(?im)^status:\s*[\"\x27]?([a-z_-]+)[\"\x27]?\s*(?:#.*)?$', match[1])
    return (values[0].lower() if len(values) == 1 else '', len(values) > 1)


def known_bool(value):
    if value is None or pd.isna(value):
        return None
    if value in (True, 1, 'True', 'true'):
        return True
    if value in (False, 0, 'False', 'false'):
        return False
    raise ValueError('Invalid placeholder Boolean')


def screen(record, evidence, stale_days):
    text = clean(record.get('exp_spec_markdown'))
    status, ambiguous = status_from_markdown(text)
    extra = evidence or {}
    other = extra.get('source_status', '').strip().lower()
    reason = extra.get('source_reason', '')
    statuses = {s for s in (status, other) if s}
    groups = {('positive' if s in POS else 'done' if s in DONE else s) for s in statuses}
    conflict = ambiguous or len(groups) > 1
    superseded = 'superseded' in statuses or bool(re.search(r'\bsupersed\w*\b', reason, re.I))
    explicit = bool(statuses & POS)
    count, checked = record.get('feature_n_checkboxes'), record.get('feature_n_checked')
    valid_counts = all(v is not None and not pd.isna(v) and math.isfinite(float(v))
                       and float(v) >= 0 and float(v).is_integer() for v in (count, checked))
    valid_counts = valid_counts and checked <= count
    unchecked = int(count - checked) if valid_counts else None
    placeholder = known_bool(record.get('feature_has_unfilled_placeholder'))
    last = pd.to_datetime(record.get('exp_last_commit_at'), utc=True, errors='coerce')
    end = pd.to_datetime(record.get('commit_history_fetched_at'), utc=True, errors='coerce')
    valid_dates = not pd.isna(last) and not pd.isna(end) and last <= end
    gap = (end-last).total_seconds()/86400 if valid_dates else None
    weak = gap is not None and gap >= stale_days and (bool(unchecked) or placeholder is True)
    baseline = explicit
    candidate = (explicit or weak) and not (superseded or conflict or bool(statuses & DONE))
    category = ('conflicting_status' if conflict else 'superseded' if superseded else
                'source_completed' if statuses & DONE else 'explicit_discontinuation' if explicit else
                'stale_with_incomplete_content' if weak else 'no_rule_trigger')
    return {KEY:record[KEY], 'repo_name':record['repo_name'], 'file_path':record['file_path'],
            'file_url':record['file_url'], 'spec_status':status, 'supplemental_status':other,
            'source_reason':reason, 'supplemental_evidence':extra.get('evidence_ref',''),
            'spec_content_available':bool(text), 'status_conflict':conflict,
            'supersession_indicator':superseded, 'unchecked_in_spec':unchecked,
            'placeholder_in_spec':placeholder, 'inactivity_days_at_collection':gap,
            'date_coverage_valid':valid_dates, 'baseline_flag':baseline,
            'candidate_flag':bool(candidate), 'screen_category':category,
            'review_needed':bool(candidate or conflict),
            'research_outcome':'unreviewed'}


def evaluate(rows, labels):
    lookup = {r[KEY]:r for r in rows}
    selected = [r for r in labels if r['split']=='evaluation']
    resolved = [r for r in selected if r['outcome'] in {'abandoned','not_abandoned','completed','superseded'}]
    result = {'evaluation_reviewed':len(selected), 'resolved':len(resolved),
              'unresolved_or_ineligible':len(selected)-len(resolved),
              'scope':'Unweighted metrics on supplied resolved evaluation cases only; not population estimates.',
              'models':{}}
    for name in ['baseline_flag','candidate_flag']:
        tp=fp=tn=fn=0
        for r in resolved:
            y = r['outcome']=='abandoned'; pred=lookup[r[KEY]][name]
            tp+=int(y and pred); fp+=int(not y and pred)
            tn+=int(not y and not pred); fn+=int(y and not pred)
        result['models'][name]={'tp':tp,'fp':fp,'tn':tn,'fn':fn,
            'precision':tp/(tp+fp) if tp+fp else None,
            'recall_on_resolved_reviewed_cases':tp/(tp+fn) if tp+fn else None,
            'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None}
    result['status']='evaluated_reviewed_subset' if resolved else 'not_evaluated_no_resolved_evaluation_labels'
    return result


def read_records(path, ids, kind):
    if path is None:
        return []
    rows=json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(rows,list): raise ValueError(f'{kind} must be a JSON array')
    seen=set()
    for r in rows:
        ident=r.get(KEY)
        if ident not in ids or ident in seen: raise ValueError(f'Unknown/duplicate {kind} identifier: {ident}')
        seen.add(ident)
        if kind=='labels':
            if r.get('outcome') not in {'abandoned','not_abandoned','completed','superseded','unclear','ineligible'}:
                raise ValueError('Invalid reviewed outcome')
            if r.get('split') not in {'development','evaluation'}: raise ValueError('Invalid split')
            for k in ['reviewer','reviewed_at','evidence_ref','rationale']:
                if not isinstance(r.get(k),str) or not r[k].strip(): raise ValueError(f'Missing {k}')
            if pd.isna(pd.to_datetime(r['reviewed_at'],errors='coerce')): raise ValueError('Invalid review date')
        else:
            for k in ['source_status','source_reason','evidence_ref']:
                if not isinstance(r.get(k),str): raise ValueError(f'Missing evidence field {k}')
            if not r['evidence_ref'].strip(): raise ValueError('Missing evidence provenance')
    return rows


def run(args):
    if args.output_dir.exists(): raise ValueError('Choose a new output directory')
    if args.stale_days<=0 or args.sample_per_stratum<=0: raise ValueError('Thresholds must be positive')
    frame=pd.read_parquet(args.stage1_dir/'specifications.parquet',columns=COLUMNS)
    if frame.empty or frame[KEY].isna().any() or frame[KEY].duplicated().any() or frame[KEY].astype(str).str.strip().eq('').any():
        raise ValueError('Specifications must have unique nonblank identifiers')
    ids=set(frame[KEY]); evidence=read_records(args.evidence,ids,'evidence')
    labels=read_records(args.labels,ids,'labels'); evidence={r[KEY]:r for r in evidence}
    rows=[screen(r,evidence.get(r[KEY]),args.stale_days) for r in frame.to_dict('records')]
    by_id={r[KEY]:r for r in labels}
    for r in rows:
        if r[KEY] in by_id: r['research_outcome']=by_id[r[KEY]]['outcome']
    output=pd.DataFrame(rows); metrics=evaluate(rows,labels)
    reviewed=set(by_id); sample=[]
    for flag in [True,False]:
        eligible=[r for r in rows if r['candidate_flag']==flag and r[KEY] not in reviewed]
        eligible.sort(key=lambda r:hashlib.sha256((str(args.seed)+r[KEY]).encode()).hexdigest())
        for r in eligible[:args.sample_per_stratum]:
            sample.append({KEY:r[KEY], 'repo_name':r['repo_name'],'file_path':r['file_path'],
                'file_url':r['file_url'],'sampling_stratum':'flagged' if flag else 'unflagged',
                'stratum_population':len(eligible),'split':'evaluation','outcome':'',
                'reviewer':'','reviewed_at':'','evidence_ref':'','rationale':''})
    args.output_dir.mkdir(parents=True)
    output.to_csv(args.output_dir/'screening_all.csv',index=False,encoding='utf-8-sig')
    output.loc[output.review_needed].to_csv(args.output_dir/'review_queue.csv',index=False,encoding='utf-8-sig')
    for filename,data in [('evaluation.json',metrics),('review_sample.json',sample)]:
        (args.output_dir/filename).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    summary={'rows':len(rows),'repositories':int(frame.repo_name.nunique()),
             'candidate_flags':int(output.candidate_flag.sum()),'baseline_flags':int(output.baseline_flag.sum()),
             'categories':output.screen_category.value_counts().to_dict(), 'evaluation_status':metrics['status']}
    report='# Abandonment screening report\n\n'+json.dumps(summary,indent=2)+'\n\n'
    report+='Candidates require review; flags are not confirmed outcomes. No automatic deletion.\n\n'
    report+='Staleness is measured to history collection, not today. Checkboxes refer to the specification itself, not linked task files. Supplemental metadata is used only when supplied with provenance. No GitHub fetching occurs.\n\n'
    report+='## Evaluation\n\n'+json.dumps(metrics,indent=2)+'\n\n'
    report+='Metrics are conditional on resolved reviewed cases. Stratified or purposive samples do not establish population accuracy. Unknown cases are not negatives. Existing development cases must not be reused as independent evaluation.\n\n'
    report+='## Prediction\n\nThis stage is retrospective and does not train a model or certify temporal eligibility. Snapshot indicators must not be reused as historical predictors.\n'
    (args.output_dir/'report.md').write_text(report,encoding='utf-8')
    inputs={'specifications':digest(args.stage1_dir/'specifications.parquet')}
    for k in ['labels','evidence']:
        if getattr(args,k): inputs[k]=digest(getattr(args,k))
    manifest={'version':VERSION,'script_sha256':digest(__file__),'inputs_sha256':inputs,
              'stale_days':args.stale_days,'seed':args.seed,'summary':summary,
              'outputs_sha256':{p.name:digest(p) for p in sorted(args.output_dir.iterdir())}}
    (args.output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage1-dir',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--labels',type=Path)
    parser.add_argument('--evidence',type=Path)
    parser.add_argument('--stale-days',type=int,default=90)
    parser.add_argument('--sample-per-stratum',type=int,default=15)
    parser.add_argument('--seed',type=int,default=42)
    run(parser.parse_args())
