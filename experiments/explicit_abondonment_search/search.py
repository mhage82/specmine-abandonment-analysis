from pathlib import Path
import argparse
import re
import pandas as pd
import pyarrow.parquet as pq

parser = argparse.ArgumentParser(description="Find SpecMine abandonment candidates.")
parser.add_argument("--limit", type=int, default=100,
                    help="Maximum candidates to save (default: 100; 0 searches all).")
parser.add_argument("--output", default="candidates.csv",
                    help="CSV filename inside results (default: candidates.csv).")
args = parser.parse_args()
if args.limit < 0:
    parser.error("--limit must be zero or positive")

# Locate the repository from this script's folder.
repo = Path(__file__).resolve().parents[2]
data_file = repo / "data/raw/specmine-full-inspection/spec_files.parquet"

columns = ["repo_name", "file_path", "file_url", "file_last_commit_message"]

# Find messages that mention possible abandonment.
keywords = (
    r"\babandon(?:ed|ing)?\b|\bcancel(?:led|ed)\b|\bshelved\b"
    r"|not implemented|no implementation progress"
)

pattern = re.compile(keywords, re.IGNORECASE)

# Read batches so a limited search can stop before loading the whole table.
found = []
searched = 0
for batch in pq.ParquetFile(data_file).iter_batches(batch_size=1000, columns=columns):
    for row in batch.to_pylist():
        searched += 1
        message = row["file_last_commit_message"] or ""
        match = pattern.search(message)
        if match:
            # Keep the keyword and surrounding context, without multiline cells.
            excerpt = message[max(0, match.start() - 100):match.end() + 200]
            row["file_last_commit_message"] = re.sub(r"\s+", " ", excerpt).strip()
            found.append(row)
            if args.limit and len(found) >= args.limit:
                break
    if args.limit and len(found) >= args.limit:
        break

matches = pd.DataFrame(found, columns=columns).rename(
    columns={"file_last_commit_message": "message_excerpt"}
)

# Save matches for manual review.
results = Path(__file__).resolve().parent / "results"
results.mkdir(exist_ok=True)
output_file = results / args.output
matches.to_csv(output_file, index=False, encoding="utf-8-sig")

print(f"Searched {searched:,} records.")
print(f"Saved {len(matches):,} candidates (limit: {args.limit or 'unlimited'}).")
if args.limit and len(matches) >= args.limit:
    print("Stopped at the limit; this is not the total candidate count.")
print("Candidates follow dataset order, not a random or representative sample.")
print(f"Saved to {output_file}")
