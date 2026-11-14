"""Run fixed-label threshold comparisons using the existing screening pipeline."""
import argparse
import csv
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

from abandonment_screen import KEY, digest, evaluate


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def load_run(folder, threshold, labels):
    manifest = read_json(folder / 'manifest.json')
    if manifest['stale_days'] != threshold:
        raise ValueError('Threshold does not match manifest')
    for name, expected in manifest['outputs_sha256'].items():
        if digest(folder / name) != expected:
            raise ValueError(f'Output hash mismatch: {folder / name}')
    with (folder / 'screening_all.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for flag in ('baseline_flag', 'candidate_flag'):
            if row[flag] not in ('True', 'False'):
                raise ValueError('Invalid Boolean flag in screening output')
            row[flag] = row[flag] == 'True'
    ids = [r[KEY] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate screening identifiers')
    summary = manifest['summary']
    if len(rows) != summary['rows'] or sum(summary['categories'].values()) != len(rows):
        raise ValueError('Record count mismatch')
    for flag, count in [('candidate_flag', 'candidate_flags'), ('baseline_flag', 'baseline_flags')]:
        if sum(r[flag] for r in rows) != summary[count]:
            raise ValueError('Flag count mismatch')
    metrics = read_json(folder / 'evaluation.json')
    if evaluate(rows, labels) != metrics:
        raise ValueError('Evaluation does not match saved labels and predictions')
    return manifest, rows, metrics


def compare(runs, reference):
    """Validate a controlled comparison and compute exact candidate-set changes."""
    first = runs[min(runs)][0]
    ref_rows = runs[reference][1]
    ref_ids = {r[KEY] for r in ref_rows}
    ref_candidates = {r[KEY] for r in ref_rows if r['candidate_flag']}
    ref_baseline = {r[KEY] for r in ref_rows if r['baseline_flag']}
    previous = None
    table = []
    for threshold, (manifest, rows, metrics) in sorted(runs.items()):
        for key in ('version', 'script_sha256', 'inputs_sha256', 'seed'):
            if manifest[key] != first[key]:
                raise ValueError(f'Runs differ in {key}')
        if {r[KEY] for r in rows} != ref_ids:
            raise ValueError('Runs contain different specification identifiers')
        baseline = {r[KEY] for r in rows if r['baseline_flag']}
        candidates = {r[KEY] for r in rows if r['candidate_flag']}
        if baseline != ref_baseline:
            raise ValueError('Explicit-status baseline changed across thresholds')
        if previous is not None and not candidates <= previous:
            raise ValueError('Candidate sets are not nested as thresholds increase')
        previous = candidates
        row = {'stale_days': threshold, 'records': len(rows),
               'candidate_flags': len(candidates), 'candidate_percent': 100 * len(candidates) / len(rows),
               'baseline_flags': len(baseline), 'added_vs_reference': len(candidates - ref_candidates),
               'removed_vs_reference': len(ref_candidates - candidates),
               'retained_vs_reference': len(candidates & ref_candidates),
               'evaluation_reviewed': metrics['evaluation_reviewed'], 'resolved': metrics['resolved'],
               'unresolved_or_ineligible': metrics['unresolved_or_ineligible']}
        for model, values in metrics['models'].items():
            row.update({f'{model}_{k}': v for k, v in values.items()})
        table.append(row)
    return table


def plot(table, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    x = [r['stale_days'] for r in table]
    y = [r['candidate_flags'] for r in table]
    ax.plot(x, y, 'o-', color='#27658C', label='Broader candidate rule')
    ax.plot(x, [r['baseline_flags'] for r in table], 's--', color='#B45309', label='Explicit-status baseline')
    for a, b in zip(x, y):
        ax.annotate(f'{b:,}', (a, b), xytext=(0, 8), textcoords='offset points', ha='center')
    ax.set(xlabel='Inactivity threshold (days)', ylabel='Flagged specification records',
           title='Screening volume across inactivity thresholds', xticks=x)
    ax.set_ylim(bottom=0, top=max(max(y), table[0]['baseline_flags'], 1) * 1.2)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='y', alpha=.2)
    ax.legend()
    fig.text(.04, .025, 'Flags are review candidates, not confirmed abandonment. Thresholds are not ranked by accuracy.', fontsize=9)
    fig.tight_layout(rect=(0, .07, 1, 1))
    for ext in ('png', 'pdf'):
        fig.savefig(output / f'threshold_comparison.{ext}', dpi=300)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage1-dir', type=Path, required=True)
    parser.add_argument('--labels', type=Path, required=True)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--thresholds', type=int, nargs='+', default=[30, 60, 90, 180])
    parser.add_argument('--reference-days', type=int, default=90)
    args = parser.parse_args()
    thresholds = sorted(args.thresholds)
    if len(set(thresholds)) != len(thresholds) or min(thresholds) <= 0 or args.reference_days not in thresholds:
        parser.error('Use unique positive thresholds including the reference threshold')
    if args.output_dir.exists():
        parser.error('Choose a fresh output directory; existing results are never overwritten')
    here = Path(__file__).resolve().parent
    files = {'specifications': args.stage1_dir / 'specifications.parquet', 'labels': args.labels}
    if args.evidence:
        files['evidence'] = args.evidence
    sources = [here / name for name in ('run_abandonment_sensitivity.py', 'run_abandonment_pipeline.py', 'abandonment_screen.py')]
    for path in list(files.values()) + sources:
        if not path.is_file():
            parser.error(f'Missing file: {path}')
    # Fail before expensive runs if plotting dependencies are unavailable.
    import matplotlib
    labels = read_json(args.labels)
    inputs = {key: digest(path) for key, path in files.items()}
    source_hashes = {p.name: digest(p) for p in sources}
    args.output_dir.mkdir(parents=True)
    runs, commands = {}, []
    for threshold in thresholds:
        command = [sys.executable, str(here / 'run_abandonment_pipeline.py'),
                   '--stage1-dir', str(args.stage1_dir.resolve()), '--labels', str(args.labels.resolve()),
                   '--output-dir', str((args.output_dir / f'days_{threshold}').resolve()), '--stale-days', str(threshold)]
        if args.evidence:
            command.extend(['--evidence', str(args.evidence.resolve())])
        commands.append(command)
        print(f'Running {threshold}-day threshold', flush=True)
        with (args.output_dir / f'days_{threshold}.log').open('w', encoding='utf-8') as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
        runs[threshold] = load_run(args.output_dir / f'days_{threshold}' / 'screening', threshold, labels)
        if runs[threshold][0]['inputs_sha256'] != inputs:
            raise ValueError('Inputs changed during experiment')
        if runs[threshold][0]['script_sha256'] != source_hashes['abandonment_screen.py']:
            raise ValueError('Screening code changed during experiment')
    if inputs != {k: digest(p) for k, p in files.items()} or source_hashes != {p.name: digest(p) for p in sources}:
        raise ValueError('Inputs or source code changed during experiment')
    table = compare(runs, args.reference_days)
    write_csv(args.output_dir / 'sensitivity_summary.csv', table)
    write_json(args.output_dir / 'sensitivity_summary.json', table)
    # Preserve reviewer text exactly; generated samples are NOT new reviewed labels.
    case_rows = []
    for threshold, (_, rows, _) in sorted(runs.items()):
        lookup = {r[KEY]: r for r in rows}
        for label in labels:
            if label['split'] != 'evaluation':
                continue
            prediction = lookup[label[KEY]]
            outcome = label['outcome']
            resolved = outcome in {'abandoned', 'not_abandoned', 'completed', 'superseded'}
            flag = prediction['candidate_flag']
            classification = ('tp' if flag else 'fn') if outcome == 'abandoned' else ('fp' if flag else 'tn')
            case_rows.append({'stale_days': threshold, KEY: label[KEY], 'repo_name': prediction['repo_name'],
                             'file_path': prediction['file_path'], 'outcome': outcome,
                             'screen_category': prediction['screen_category'], 'candidate_flag': flag,
                             'baseline_flag': prediction['baseline_flag'],
                             'classification': classification if resolved else 'excluded_unresolved_or_ineligible',
                             **{k: label[k] for k in ('reviewer', 'reviewed_at', 'evidence_ref', 'rationale')}})
    if case_rows:
        write_csv(args.output_dir / 'reviewed_case_comparison.csv', case_rows)
    plot(table, args.output_dir)
    caption = ('Candidate counts across inactivity thresholds using identical prepared data, reviewed labels, '
               'and screening rules. The explicit-status baseline is independent of the inactivity threshold. '
               'Counts represent screening workload, not verified abandonment or predictive performance.')
    (args.output_dir / 'captions.md').write_text(caption + '\n', encoding='utf-8')
    report = ['# Sensitivity results', '', '| Days | Candidates | Percent | Baseline | Added vs reference | Removed vs reference |',
              '|---:|---:|---:|---:|---:|---:|']
    for r in table:
        report.append(f"| {r['stale_days']} | {r['candidate_flags']} | {r['candidate_percent']:.2f} | {r['baseline_flags']} | {r['added_vs_reference']} | {r['removed_vs_reference']} |")
    report.extend(['', f'Reference threshold: {args.reference_days} days.', '',
                   'All runs use the same saved evaluation labels. No new manual reviews were performed. '
                   'Unclear/ineligible cases are excluded from metrics. Metrics are unweighted reviewed-subset results, not population estimates. '
                   'Blank CSV metrics / JSON null mean undefined. With no reviewed positive cases, recall is undefined. '
                   'These comparisons do not establish an optimal threshold or predictive power. '
                   'Generated review_sample.json files are unused suggestions, not additional evaluation observations.'])
    (args.output_dir / 'report.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    provenance = {'reference_days': args.reference_days, 'thresholds': thresholds, 'inputs_sha256': inputs,
                  'input_paths': {k: str(p.resolve()) for k, p in files.items()}, 'scripts_sha256': source_hashes,
                  'versions': {'python': sys.version, **{k: importlib.metadata.version(k) for k in ('pandas', 'pyarrow', 'matplotlib')}},
                  'commands': commands, 'checks': 'input/code hashes, output hashes, counts, recomputed evaluation, identical IDs/baseline, nested candidate sets',
                  'outputs_sha256': {str(p.relative_to(args.output_dir)): digest(p) for p in sorted(args.output_dir.rglob('*')) if p.is_file()}}
    write_json(args.output_dir / 'sensitivity_manifest.json', provenance)
    print(f'Completed. Results and figures: {args.output_dir}')


if __name__ == '__main__':
    main()
