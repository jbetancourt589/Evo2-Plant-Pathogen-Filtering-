#!/usr/bin/env python3
"""
Extract unique bacterial organism names from the NCBI assembly summary.

Logic:
1. Stream rows from the local NCBI assembly summary file.
2. Keep rows where the NCBI group is bacteria.
3. Write one sorted row per unique organism name.

Inputs:
- Datasets/NCBI Database/NCBI_database.txt

Outputs:
- Results/Bacteria/ncbi_bacteria_unique_names.csv
"""

import argparse
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "Datasets" / "NCBI Database" / "NCBI_database.txt"
DEFAULT_OUTPUT = PROJECT_ROOT / "Results" / "Bacteria" / "ncbi_bacteria_unique_names.csv"


def read_assembly_summary_rows(path: Path):
    """Yield rows from an NCBI assembly_summary-style tab-delimited file."""
    header = None

    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        for line in file:
            line = line.rstrip("\n").lstrip("\ufeff")
            if not line:
                continue

            if line.startswith("#assembly_accession"):
                header = line.lstrip("#").split("\t")
                continue

            if line.startswith("#"):
                continue

            if header is None:
                raise ValueError("Could not find header line beginning with #assembly_accession")

            values = line.split("\t")
            if len(values) < len(header):
                values += [""] * (len(header) - len(values))

            yield dict(zip(header, values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract unique bacterial names from the NCBI database file.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"NCBI database file not found: {args.input}")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    bacteria_rows = 0
    bacteria_names = set()

    for row in read_assembly_summary_rows(args.input):
        total_rows += 1
        if row.get("group", "").casefold() != "bacteria":
            continue

        bacteria_rows += 1
        organism_name = row.get("organism_name", "").strip()
        if organism_name:
            bacteria_names.add(organism_name)

    with args.output.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["organism_name"])
        for organism_name in sorted(bacteria_names):
            writer.writerow([organism_name])

    print(f"NCBI rows checked: {total_rows}")
    print(f"Bacterial assembly rows checked: {bacteria_rows}")
    print(f"Unique bacterial names written: {len(bacteria_names)}")
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
