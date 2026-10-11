from pathlib import Path
import pandas as pd

folder = Path(
    r"C:\Users\moham\workspace\21_ML\CSC580\specmine-abandonment-analysis\data\raw\specmine-full-inspection"
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

# Unfiltered subset: no abandonment keywords or classifications applied.
df.head(1000).to_csv(
    folder / "original_metadata_first_1000.csv",
    index=False,
    encoding="utf-8-sig",
)