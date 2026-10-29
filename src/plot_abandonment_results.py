"""Create research figures from a screening run's manifest and evaluation JSON."""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(screening_dir, output_dir):
    if output_dir.exists():
        raise ValueError('Choose a fresh figures output directory')
    manifest_path = screening_dir / 'manifest.json'
    evaluation_path = screening_dir / 'evaluation.json'
    summary = json.loads(manifest_path.read_text(encoding='utf-8-sig'))['summary']
    evaluation = json.loads(evaluation_path.read_text(encoding='utf-8-sig'))
    categories = summary['categories']
    if sum(categories.values()) != summary['rows']:
        raise ValueError('Category counts do not sum to total records')
    for model in evaluation['models'].values():
        if sum(model[k] for k in ('tp', 'fp', 'tn', 'fn')) != evaluation['resolved']:
            raise ValueError('Confusion counts do not sum to resolved cases')
    output_dir.mkdir(parents=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False})
    labels = {'no_rule_trigger': 'No rule triggered', 'source_completed': 'Source marked completed',
              'stale_with_incomplete_content': 'Stale with incomplete content',
              'explicit_discontinuation': 'Explicit discontinuation status',
              'superseded': 'Supersession indicator', 'conflicting_status': 'Conflicting statuses'}
    items = sorted(categories.items(), key=lambda item: item[1], reverse=True)
    fig, ax = plt.subplots(figsize=(10, 5.4))
    counts = [v for _, v in items]
    bars = ax.barh([labels.get(k, k.replace('_', ' ')) for k, _ in items], counts,
                   color='#27658C', height=.62)
    ax.invert_yaxis()
    ax.set_xscale('symlog', linthresh=1)
    ax.set_xlabel('Specification records (symmetric-log scale; linear from 0 to 1)')
    ax.set_title(f"Screening categories across {summary['rows']:,} records", loc='left', fontweight='bold', pad=15)
    ax.set_xlim(0, max(counts) * 4)
    ax.grid(axis='x', alpha=.18)
    ax.set_axisbelow(True)
    for bar, count in zip(bars, counts):
        ax.annotate(f'{count:,} ({count / summary["rows"]:.2%})',
                    (count, bar.get_y()+bar.get_height()/2), xytext=(5, 0),
                    textcoords='offset points', va='center', fontsize=10)
    fig.text(.04, .025, 'Screening categories are not confirmed abandonment outcomes. Records may share repository paths.', fontsize=9)
    fig.tight_layout(rect=(0, .06, 1, 1))
    for ext in ('png', 'pdf'):
        fig.savefig(output_dir / f'screening_categories.{ext}', dpi=300)
    plt.close(fig)

    captions = [f"Figure 1. Screening categories for {summary['rows']:,} specification records across {summary['repositories']:,} repositories. Counts and percentages describe rule outputs, not confirmed abandonment. A symmetric-log count axis makes rare categories visible. Duplicate repository-path records are preserved."]
    if evaluation['resolved']:
        names = [('baseline_flag', 'Explicit-status baseline'), ('candidate_flag', 'Broader candidate rule')]
        keys = ['tp', 'fp', 'tn', 'fn']
        fig, ax = plt.subplots(figsize=(9, 5.4))
        for offset, (key, label) in zip([-.19, .19], names):
            values = [evaluation['models'][key][k] for k in keys]
            positions = [i+offset for i in range(4)]
            bars = ax.bar(positions, values, width=.36, label=label,
                          color='#27658C' if offset < 0 else '#D97732')
            ax.bar_label(bars, padding=4)
        ax.set_xticks(range(4), ['True positives', 'False positives', 'True negatives', 'False negatives'])
        ax.set_ylabel('Resolved reviewed cases')
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_ylim(0, evaluation['resolved']+1.5)
        ax.set_title(f"Preliminary evaluation: {evaluation['resolved']} resolved cases", loc='left', fontweight='bold', pad=15)
        ax.legend(frameon=False)
        ax.grid(axis='y', alpha=.18)
        ax.set_axisbelow(True)
        m = evaluation['models']['baseline_flag']
        positive_count = m['tp'] + m['fn']
        note = f"{evaluation['evaluation_reviewed']} reviewed; {evaluation['unresolved_or_ineligible']} unresolved/ineligible excluded. Unweighted subset, not population estimates."
        if positive_count == 0:
            note += '\nNo confirmed abandoned cases: recall is undefined; zero false negatives does not demonstrate sensitivity.'
        fig.text(.04, .025, note, fontsize=9)
        fig.tight_layout(rect=(0, .10, 1, 1))
        for ext in ('png', 'pdf'):
            fig.savefig(output_dir / f'evaluation_counts.{ext}', dpi=300)
        plt.close(fig)
        captions.append('Figure 2. Confusion counts for the explicit-status baseline and broader candidate rule on resolved reviewed evaluation cases. '+note.replace('\n', ' '))
    else:
        captions.append('No evaluation figure generated: no resolved evaluation labels were supplied.')
    (output_dir / 'captions.md').write_text('\n\n'.join(captions)+'\n', encoding='utf-8')
    provenance = {'inputs_sha256': {p.name: sha(p) for p in (manifest_path, evaluation_path)},
                  'script_sha256': sha(Path(__file__)), 'matplotlib_version': matplotlib.__version__,
                  'outputs_sha256': {p.name: sha(p) for p in sorted(output_dir.iterdir())}}
    (output_dir / 'figure_manifest.json').write_text(json.dumps(provenance, indent=2)+'\n', encoding='utf-8')
    print(f'Figures and captions saved to {output_dir}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screening-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    run(args.screening_dir, args.output_dir)
