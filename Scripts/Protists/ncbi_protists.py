#!/usr/bin/env python3
"""
Extract protist organism names and assembly IDs from the local NCBI assembly summary.

Logic:
1. Stream rows from the local NCBI assembly summary file.
2. Keep rows where the NCBI group is protozoa.
3. Write unique protist names and name/assembly pairs.

Inputs:
- Datasets/NCBI Database/NCBI_database.txt

Outputs:
- Results/Protists/ncbi_protist_names.csv
- Results/Protists/ncbi_protists_names_and_assemblies.csv
"""

import argparse
import csv
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "Datasets" / "NCBI Database" / "NCBI_database.txt"
DEFAULT_NAMES_OUTPUT = PROJECT_ROOT / "Results" / "Protists" / "ncbi_protist_names.csv"
DEFAULT_ASSEMBLIES_OUTPUT = PROJECT_ROOT / "Results" / "Protists" / "ncbi_protists_names_and_assemblies.csv"
NCBI_PROTIST_GROUP = "protozoa"


def read_assembly_summary_rows(path: Path) -> Iterator[dict[str, str]]:
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
        description="Extract protist names and assembly IDs from the local NCBI database file."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="NCBI assembly_summary-style input file.")
    parser.add_argument(
        "--names-output",
        type=Path,
        default=DEFAULT_NAMES_OUTPUT,
        help="CSV output for unique protist organism names.",
    )
    parser.add_argument(
        "--assemblies-output",
        type=Path,
        default=DEFAULT_ASSEMBLIES_OUTPUT,
        help="CSV output for protist organism names and assembly IDs.",
    )
    return parser.parse_args()


def write_names(path: Path, organism_names: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["organism_name"])
        for organism_name in sorted(organism_names):
            writer.writerow([organism_name])


def write_names_and_assemblies(path: Path, organism_assemblies: set[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["organism_name", "assembly_id"])
        for organism_name, assembly_id in sorted(organism_assemblies):
            writer.writerow([organism_name, assembly_id])


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"NCBI database file not found: {args.input}")

    total_rows = 0
    protist_rows = 0
    protist_names = set()
    protist_name_assemblies = set()

    for row in read_assembly_summary_rows(args.input):
        total_rows += 1
        if row.get("group", "").casefold() != NCBI_PROTIST_GROUP:
            continue

        organism_name = row.get("organism_name", "").strip()
        assembly_id = row.get("assembly_accession", "").strip()
        if not organism_name or not assembly_id:
            continue

        protist_rows += 1
        protist_names.add(organism_name)
        protist_name_assemblies.add((organism_name, assembly_id))

    write_names(args.names_output, protist_names)
    write_names_and_assemblies(args.assemblies_output, protist_name_assemblies)

    print(f"NCBI rows checked: {total_rows}")
    print(f"Protist assembly rows checked: {protist_rows}")
    print(f"Unique protist names written: {len(protist_names)}")
    print(f"Unique protist name/assembly rows written: {len(protist_name_assemblies)}")
    print(f"Wrote: {args.names_output}")
    print(f"Wrote: {args.assemblies_output}")


if __name__ == "__main__":
    main()
