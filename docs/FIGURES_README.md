# Preliminary result figures

Copy the src files into the project src directory and requirements-figures.txt into the project root. The updated wrapper adds optional --figures-dir; the screening rules are unchanged.

Install in PowerShell:

    .\.venv-completion\Scripts\python.exe -m pip install -r requirements-figures.txt

Generate figures from an existing verified run:

    .\.venv-completion\Scripts\python.exe src/plot_abandonment_results.py --screening-dir "results/abandonment_full_check_01/screening" --output-dir "figures/abandonment_preliminary_01"

Use a fresh figures directory. Outputs: screening_categories.png/.pdf, evaluation_counts.png/.pdf, captions.md, figure_manifest.json. The evaluation figure is omitted if no resolved cases exist. Inputs are manifest.json and evaluation.json; hashes are recorded for provenance. No metrics are recalculated and no review labels are changed.

For a future full run including figures:

    .\.venv-completion\Scripts\python.exe src/run_abandonment_pipeline.py --data-dir "data/specmine-official/data" --output-dir "results/abandonment_with_figures_01" --labels "docs/reviewed_labels.json" --stale-days 90 --figures-dir "figures/abandonment_with_figures_01"

Both output directories must be new. Install figure requirements before running with --figures-dir.

Figure 1 uses a symmetric-log count axis so rare categories remain visible. Read the printed counts and percentages; bar lengths are not linear proportions. Categories are screening decisions, not confirmed outcomes. Figure 2 reports raw confusion counts for the resolved reviewed subset only. With no positive cases, zero false negatives does not show sensitivity and recall is undefined.

Commit the plotting script, updated wrapper, requirements file, and this guide. Generated figures remain ignored under the existing repository policy. Add a link to this guide from the root README.

Validation: Python syntax checked; plotting executed with a fixture reproducing the user's reported category and evaluation counts; both PNGs visually inspected. This is not an independent rerun of the raw dataset or the Windows pipeline. Generate final report figures from the actual run files using the command above.
