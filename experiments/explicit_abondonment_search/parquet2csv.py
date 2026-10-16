from pathlib import Path
import pandas as pd

folder = Path(
    r"C:\Users\moham\workspace\21_ML\CSC580"
    r"\specmine-abandonment-analysis\data\raw"
    r"\specmine-full-inspection"
)

df = pd.read_parquet(
    folder / "spec_files.parquet",
    columns=[
        "file_url_sha16",
        "repo_name",
        "file_path",
        "file_url",
        "file_last_commit_html_url",
        "file_last_commit_message",
    ],
)

keywords = r"\babandon(?:ed|ing)?\b|\bcancel(?:led|ed)\b|\bshelved\b"

candidates = df[
    df["file_last_commit_message"].str.contains(
        keywords, case=False, na=False
    )
].head(20)

# Plain text alternative for document-based upload interfaces.
output = folder / "candidate_records.txt"

with output.open("w", encoding="utf-8") as file:
    file.write(
        "First 20 keyword-matched SpecMine metadata records.\n"
        "These are unverified candidates, not abandonment labels.\n\n"
    )

    for number, (_, row) in enumerate(candidates.iterrows(), start=1):
        file.write(f"RECORD {number}\n")
        for column in candidates.columns:
            file.write(f"{column}: {row[column]}\n")
        file.write("\n---\n\n")

print(f"Saved {len(candidates)} candidates to {output}")
print(f"File size: {output.stat().st_size / 1024:.1f} KB")
