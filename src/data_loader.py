"""Load SpecMine Parquet tables without cleaning, joining, or labeling rows."""

import argparse
import json
from pathlib import Path

import pandas as pd


DEFAULT_TABLES = ("spec_files", "spec_file_commits", "spec_content_features")


def load_tables(data_dir, table_names=None):
    """Return {table_name: DataFrame}; data_dir must contain Parquet files.

    None selects the three broad-census tables. Pass other table names to
    include Kiro or other layers. All columns and source dtypes are preserved.
    """
    directory = Path(data_dir).expanduser().resolve()
    if not directory.is_dir():
        raise FileNotFoundError(f"Data directory does not exist: {directory}")
    names = list(DEFAULT_TABLES if table_names is None else table_names)
    if not names:
        raise ValueError("No Parquet tables selected or found.")
    paths = {}
    for name in names:
        if not name or Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError(f"Use a table name without a path or extension: {name!r}")
        path = directory / f"{name}.parquet"
        if not path.is_file():
            raise FileNotFoundError(f"Required table is missing: {path}")
        paths[name] = path
    tables = {}
    for name, path in paths.items():
        try:
            tables[name] = pd.read_parquet(path, engine="pyarrow")
        except Exception as exc:
            raise RuntimeError(f"Cannot read {path}: {exc}") from exc
    return tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path,
                        help="Directory containing the sample's .parquet files")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--tables", nargs="+", help="Table names without .parquet")
    selection.add_argument("--all", action="store_true", help="Load all Parquet tables")
    parser.add_argument("--summary", type=Path, help="Optional JSON inventory output")
    args = parser.parse_args()
    names = args.tables
    if args.all:
        names = sorted(p.stem for p in args.data_dir.expanduser().glob("*.parquet"))
    try:
        tables = load_tables(args.data_dir, names)
        summary = {}
        for name, frame in tables.items():
            print(f"{name}: {len(frame):,} rows, {len(frame.columns)} columns")
            summary[name] = {
                "rows": len(frame),
                "column_count": len(frame.columns),
                "columns": {str(col): str(dtype) for col, dtype in frame.dtypes.items()},
            }
        if args.summary:
            args.summary.parent.mkdir(parents=True, exist_ok=True)
            args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            print(f"Inventory saved to {args.summary}")
    except (FileNotFoundError, ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, f"Loader error: {exc}\n")


if __name__ == "__main__":
    main()
