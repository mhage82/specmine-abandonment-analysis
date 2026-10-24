"""Apply reviewed evidence JSONs to the CSV; this does not infer any labels.

Uses only the standard library. Existing differing annotations are protected.
"""

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path


FIELDS = (
    "manual_status", "manual_scope_match", "manual_evidence_url",
    "manual_outcome_date", "manual_notes", "reviewer", "reviewed_at",
)
STATUSES = {"completed", "abandoned", "in_progress", "deferred", "unclear"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-csv", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    original = args.review_csv.read_bytes()
    reader = csv.DictReader(io.StringIO(original.decode("utf-8-sig"), newline=""))
    columns = reader.fieldnames
    if not columns or not set(("file_url_sha16", *FIELDS)).issubset(columns):
        raise ValueError("CSV is missing required review columns")
    if len(columns) != len(set(columns)):
        raise ValueError("CSV contains duplicate column names")
    rows = list(reader)
    ids = [row["file_url_sha16"] for row in rows]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Expected a nonempty CSV with unique identifiers")
    changed = False
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed CSV row")
        ident = row["file_url_sha16"]
        if not re.fullmatch(r"[0-9a-f]{16}", ident):
            raise ValueError(f"Invalid identifier: {ident}")
        evidence = json.loads((args.evidence_dir / f"{ident}.json").read_text(encoding="utf-8-sig"))
        if evidence.get("file_url_sha16") != ident:
            raise ValueError(f"Evidence identifier mismatch: {ident}")
        for field in FIELDS:
            value = evidence.get(field)
            if not isinstance(value, str) or "\n" in value or "\r" in value:
                raise ValueError(f"Expected single-line string: {ident}/{field}")
            if field != "manual_outcome_date" and not value.strip():
                raise ValueError(f"Missing annotation: {ident}/{field}")
            if row[field] and row[field] != value:
                raise ValueError(f"Refusing to overwrite existing annotation: {ident}/{field}")
            changed |= row[field] != value
            row[field] = value
        if row["manual_status"] not in STATUSES:
            raise ValueError(f"Invalid status: {ident}")
        if row["manual_scope_match"] not in {"yes", "partial", "unclear"}:
            raise ValueError(f"Invalid scope match: {ident}")
        for field in ("manual_outcome_date", "reviewed_at"):
            if row[field]:
                date.fromisoformat(row[field])
    counts = dict(Counter(row["manual_status"] for row in rows))
    if not changed:
        print(json.dumps({"rows": len(rows), "status_counts": counts, "changed": False}))
        return
    digest = hashlib.sha256(original).hexdigest()
    backup = args.evidence_dir / "backups" / f"{args.review_csv.stem}.before_codex_{digest[:12]}.csv"
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        if backup.read_bytes() != original:
            raise ValueError(f"Existing backup content differs: {backup}")
    else:
        with backup.open("xb") as stream:
            stream.write(original)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    encoded = output.getvalue().encode("utf-8-sig")
    temporary = args.review_csv.with_name(args.review_csv.name + ".annotation.tmp")
    with temporary.open("xb") as stream:
        stream.write(encoded)
    try:
        if args.review_csv.read_bytes() != original:
            raise ValueError("CSV changed during annotation; original preserved")
        temporary.replace(args.review_csv)
    finally:
        if temporary.exists():
            temporary.unlink()
    print(json.dumps({"rows": len(rows), "status_counts": counts, "changed": True,
                      "backup": str(backup), "original_sha256": digest,
                      "annotated_sha256": hashlib.sha256(encoded).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
