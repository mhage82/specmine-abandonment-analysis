"""Replay the completion experiment using preserved annotation decisions.

This rebuilds data products; it does not repeat AI evidence review or fetch GitHub.
The raw source snapshot is supplied separately and verified against the bundle.
Every run requires a new output directory and leaves earlier experiments intact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy
import pandas as pd
import pyarrow


REPO_ROOT = Path(__file__).resolve().parents[1]
KEY = "file_url_sha16"
FIELDS = ["manual_status", "manual_scope_match", "manual_evidence_url",
          "manual_outcome_date", "manual_notes", "reviewer", "reviewed_at"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def check_inputs(bundle_dir: Path, data_dir: Path) -> dict:
    manifest = read_json(bundle_dir / "manifest.json")
    if manifest["schema_version"] != 1:
        raise ValueError("Unsupported annotation bundle version")
    for relative, expected in manifest["script_sha256"].items():
        script = (REPO_ROOT / relative).resolve()
        if not script.is_relative_to(REPO_ROOT) or sha256(script) != expected:
            raise ValueError(f"Experiment script differs from the preserved version: {relative}")
    for name, item in manifest["raw_inputs"].items():
        source = (data_dir / item["relative_to_data_dir"]).resolve()
        if not source.is_file() or sha256(source) != item["sha256"]:
            raise ValueError(f"Missing or different raw snapshot input: {name}: {source}")
    for ident, expected in manifest["decision_sha256"].items():
        path = bundle_dir / "decisions" / f"{ident}.json"
        if sha256(path) != expected:
            raise ValueError(f"Preserved annotation bytes changed: {ident}")
        decision = read_json(path)
        if decision.get(KEY) != ident or not set(FIELDS).issubset(decision):
            raise ValueError(f"Malformed preserved annotation: {ident}")
    for name, cohort in manifest["cohorts"].items():
        ids = cohort["identifiers"]
        if len(ids) != len(set(ids)) or not set(ids).issubset(manifest["decision_sha256"]):
            raise ValueError(f"Invalid preserved cohort: {name}")
    return manifest


def restore_decisions(bundle_dir: Path, stage_dir: Path, cohort: dict) -> None:
    review = pd.read_csv(stage_dir / "completion_review.csv", dtype=str, keep_default_na=False)
    if review[KEY].tolist() != cohort["identifiers"]:
        raise ValueError(f"Regenerated cohort selection/order differs: {stage_dir.name}")
    evidence = stage_dir / "annotation_evidence"
    evidence.mkdir(exist_ok=True)
    for ident in cohort["identifiers"]:
        original = (bundle_dir / "decisions" / f"{ident}.json").read_bytes()
        destination = evidence / f"{ident}.json"
        if destination.exists() and destination.read_bytes() != original:
            raise ValueError(f"Carried-forward annotation differs: {ident}")
        if not destination.exists():
            destination.write_bytes(original)


def verify_replayed_labels(bundle_dir: Path, stage_dir: Path, cohort: dict) -> dict:
    review = pd.read_csv(stage_dir / "completion_review.csv", dtype=str, keep_default_na=False)
    if review[KEY].tolist() != cohort["identifiers"]:
        raise ValueError(f"Replayed identifiers/order differ: {stage_dir.name}")
    for row in review.to_dict("records"):
        decision = read_json(bundle_dir / "decisions" / f"{row[KEY]}.json")
        if any(row[field] != decision[field] for field in FIELDS):
            raise ValueError(f"Replayed manual annotation differs: {row[KEY]}")
    counts = review.manual_status.value_counts().sort_index().to_dict()
    if counts != cohort["status_counts"]:
        raise ValueError(f"Replayed label counts differ: {stage_dir.name}")
    return {"rows": len(review), "status_counts": counts,
            "identifiers_order_and_all_manual_fields_match": True,
            "review_csv_sha256": sha256(stage_dir / "completion_review.csv"),
            "csv_bytes_match_original": sha256(stage_dir / "completion_review.csv") == cohort["review_csv_sha256"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data/raw/specmine-official/data")
    parser.add_argument("--bundle-dir", type=Path, default=REPO_ROOT / "reproducibility/completion_annotations")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "results/completion_reproduction")
    args = parser.parse_args()
    data_dir, bundle_dir, output = (path.resolve() for path in
                                  (args.data_dir, args.bundle_dir, args.output_root))
    if output.exists():
        raise ValueError("Output root already exists. Choose a NEW --output-root; earlier results are never overwritten.")
    if output.is_relative_to(data_dir) or output.is_relative_to(bundle_dir):
        raise ValueError("Output root must be outside the raw dataset and preserved annotation bundle")
    manifest = check_inputs(bundle_dir, data_dir)
    output.mkdir(parents=True)
    stage1, stage2, all140, all564, cutoff, status = [output / name for name in
                                                  ("stage1", "stage2", "all140", "all564", "cutoff", "cutoff_status")]
    commands = []
    environment = dict(os.environ, PYTHONIOENCODING="utf-8")
    # Preserve errors/warnings in the log while keeping the terminal readable.
    with (output / "reproduction.log").open("w", encoding="utf-8") as log:
        def run(script: str, *arguments: object) -> None:
            command = [sys.executable, str(REPO_ROOT / "src" / script), *map(str, arguments)]
            print(f"[{len(commands) + 1:02d}] {script}", flush=True)
            log.write("\nCOMMAND_ARGUMENTS " + json.dumps(command) + "\n")
            log.flush()
            result = subprocess.run(command, cwd=REPO_ROOT, env=environment, stdout=log,
                                    stderr=subprocess.STDOUT, check=False)
            commands.append({"argv": command, "returncode": result.returncode})
            write_json(output / "commands.json", {"working_directory": REPO_ROOT.as_posix(), "commands": commands})
            if result.returncode:
                raise RuntimeError(f"{script} failed; inspect {output / 'reproduction.log'}")

        def apply(directory: Path, cohort_name: str) -> None:
            restore_decisions(bundle_dir, directory, manifest["cohorts"][cohort_name])
            run("completion_apply_annotations.py", "--review-csv", directory / "completion_review.csv",
                "--evidence-dir", directory / "annotation_evidence")

        run("completion_stage1_prepare.py", "--data-dir", data_dir, "--output-dir", stage1)
        run("completion_stage2_candidates.py", "--input-dir", stage1, "--output-dir", stage2,
            "--min-spec-commits", 2, "--sample-size", 10, "--seed", 42)
        apply(stage2, "stage2")
        run("completion_stage3_review_all.py", "--stage1-dir", stage1, "--stage2-dir", stage2,
            "--output-dir", all140)
        apply(all140, "all140")
        run("completion_summarize_review.py", "--review-dir", all140)
        run("completion_stage4_include_archived.py", "--stage1-dir", stage1, "--stage2-dir", stage2,
            "--prior-dir", all140, "--output-dir", all564)
        apply(all564, "all564")
        run("completion_summarize_review.py", "--review-dir", all564)
        run("completion_verify_expansion.py", "--review-dir", all564, "--prior-dir", all140,
            "--stage1-dir", stage1, "--stage2-dir", stage2)
        run("completion_stage5_cutoff.py", "--stage1-dir", stage1, "--review-dir", all564,
            "--output-dir", cutoff, "--primary-days", 7, "--windows", 7, 14, 30, 60, 90)
        run("completion_verify_cutoff.py", "--output-dir", cutoff)
        run("completion_stage6_status.py", "--cutoff-dir", cutoff, "--output-dir", status)
    checks = {name: verify_replayed_labels(bundle_dir, directory, manifest["cohorts"][name])
              for name, directory in [("stage2", stage2), ("all140", all140), ("all564", all564)]}
    actual_cutoffs = pd.read_csv(cutoff / "cutoff_comparison.csv").to_dict("records")
    actual_status = pd.read_csv(status / "cutoff_status_summary.csv").to_dict("records")
    if actual_cutoffs != manifest["expected_cutoff_comparison"]:
        raise ValueError("Replayed cutoff counts differ from the preserved experiment")
    if actual_status != manifest["expected_status_summary"]:
        raise ValueError("Replayed cutoff-status counts differ from the preserved experiment")
    result = {
        "interpretation": "Replayed preserved AI-assisted annotations; no new evidence review or GitHub fetch.",
        "bundle_manifest_sha256": sha256(bundle_dir / "manifest.json"),
        "source_dataset": manifest["source_dataset"],
        "versions": {"python": platform.python_version(), "numpy": numpy.__version__,
                     "pandas": pd.__version__, "pyarrow": pyarrow.__version__},
        "cohort_checks": checks, "cutoff_counts_match": True, "cutoff_status_counts_match": True,
        "successful_script_commands": len(commands), "output_root": output.as_posix(),
        "original_experiment_was_not_modified": True,
    }
    write_json(output / "reproduction_verification.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
