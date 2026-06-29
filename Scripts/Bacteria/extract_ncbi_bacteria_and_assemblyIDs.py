#!/usr/bin/env python3
"""
Extract bacterial organism names and assembly IDs from the NCBI assembly summary.

Logic:
1. Stream rows from the local NCBI assembly summary file.
2. Keep rows where the NCBI group is bacteria.
3. Write unique organism name and assembly ID pairs.

Inputs:
- Datasets/NCBI Database/NCBI_database.txt

Outputs:
- Results/Bacteria/all_ncbi_bacteria_and_assemblyIDs.txt
"""

import argparse
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "Datasets" / "NCBI Database" / "NCBI_database.txt"
DEFAULT_OUTPUT = PROJECT_ROOT / "Results" / "Bacteria" / "all_ncbi_bacteria_and_assemblyIDs.txt"


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
    parser = argparse.ArgumentParser(
        description="Extract all bacterial organism names and assembly IDs from the NCBI database file."
    )
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
    seen_rows = set()

    with args.output.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file, delimiter="\t", lineterminator="\n")
        writer.writerow(["organism_name", "assembly_id"])

        for row in read_assembly_summary_rows(args.input):
            total_rows += 1
            if row.get("group", "").casefold() != "bacteria":
                continue

            organism_name = row.get("organism_name", "").strip()
            assembly_id = row.get("assembly_accession", "").strip()
            output_key = (organism_name, assembly_id)
            if output_key in seen_rows:
                continue
            seen_rows.add(output_key)

            writer.writerow([organism_name, assembly_id])
            bacteria_rows += 1

    print(f"NCBI rows checked: {total_rows}")
    print(f"Bacterial assembly rows written: {bacteria_rows}")
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
