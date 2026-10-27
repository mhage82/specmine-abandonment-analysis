"""Run existing preparation (optional), then screening, evaluation and reporting."""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--stage1-dir',type=Path)
    source.add_argument('--data-dir',type=Path)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--labels',type=Path)
    p.add_argument('--evidence',type=Path)
    p.add_argument('--stale-days',type=int,default=90)
    args=p.parse_args()
    if args.output_dir.exists():p.error('Choose a fresh output directory')
    here=Path(__file__).resolve().parent
    stage=args.stage1_dir
    if args.data_dir:
        prepare=here/'completion_stage1_prepare.py'
        if not prepare.is_file():p.error('Copy this add-on into the existing project src directory first')
        stage=args.output_dir/'stage1'
        subprocess.run([sys.executable,str(prepare),'--data-dir',str(args.data_dir.resolve()),'--output-dir',str(stage.resolve())],check=True)
    command=[sys.executable,str(here/'abandonment_screen.py'),'--stage1-dir',str(stage.resolve()),
             '--output-dir',str((args.output_dir/'screening').resolve()),'--stale-days',str(args.stale_days)]
    for k in ['labels','evidence']:
        if getattr(args,k):command.extend(['--'+k,str(getattr(args,k).resolve())])
    subprocess.run(command,check=True)

if __name__=='__main__':main()
