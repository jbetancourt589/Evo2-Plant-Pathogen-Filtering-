#!/usr/bin/env python3
"""
Find GenBank fungal assemblies that Evo2 was not trained on.

Logic:
1. Load GenBank fungal name/assembly rows.
2. Load Evo2 fungal assembly IDs.
3. Write GenBank fungal assemblies not found in Evo2 by exact or versionless ID.

Inputs:
- Results/Genus List & GenBank/all_genbank_fungi_and_assemblyIDs.csv
- Results/Genus List & GenBank/evo2_trained_fungi.csv

Outputs:
- Results/Genus List & GenBank/fungi_not_trained_by_evo2.csv
"""

import argparse
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FUNGAL_ASSEMBLIES = PROJECT_ROOT / "Results" / "Genus List & GenBank" / "all_genbank_fungi_and_assemblyIDs.csv"
DEFAULT_EVO2_FUNGI = PROJECT_ROOT / "Results" / "Genus List & GenBank" / "evo2_trained_fungi.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "Results" / "Genus List & GenBank" / "fungi_not_trained_by_evo2.csv"


def accession_base(assembly_id: str) -> str:
    """Return accession without version suffix."""
    return assembly_id.rsplit(".", 1)[0]


def read_csv_rows(path: Path):
    """Read a CSV file into dictionaries."""
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        yield from csv.DictReader(file)


def load_evo2_fungi(path: Path) -> tuple[set[str], set[str]]:
    """Load assembly IDs classified as fungi in Evo2."""
    exact_assembly_ids = set()
    base_assembly_ids = set()

    for row in read_csv_rows(path):
        if row.get("is_fungi", "").strip().upper() not in {"", "Y"}:
            continue

        assembly_id = row.get("assembly_id", "").strip()
        if assembly_id:
            exact_assembly_ids.add(assembly_id)
            base_assembly_ids.add(accession_base(assembly_id))

    return exact_assembly_ids, base_assembly_ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find GenBank fungi not trained on by Evo2.")
    parser.add_argument("--fungal-assemblies", type=Path, default=DEFAULT_FUNGAL_ASSEMBLIES)
    parser.add_argument("--evo2-fungi", type=Path, default=DEFAULT_EVO2_FUNGI)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.fungal_assemblies.exists():
        raise FileNotFoundError(f"Fungal assemblies file not found: {args.fungal_assemblies}")
    if not args.evo2_fungi.exists():
        raise FileNotFoundError(f"Evo2 fungi file not found: {args.evo2_fungi}")

    evo2_exact_ids, evo2_base_ids = load_evo2_fungi(args.evo2_fungi)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    total_fungal_assemblies = 0
    not_trained_rows = 0
    skipped_exact = 0
    skipped_versionless = 0
    seen_output_rows = set()

    with args.output.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["organism_name", "assembly_id", "not_trained_reason"])

        for row in read_csv_rows(args.fungal_assemblies):
            organism_name = row.get("organism_name", "").strip()
            assembly_id = row.get("assembly_id", "").strip()
            total_fungal_assemblies += 1

            if assembly_id in evo2_exact_ids:
                skipped_exact += 1
                continue

            if assembly_id and accession_base(assembly_id) in evo2_base_ids:
                skipped_versionless += 1
                continue

            output_key = (organism_name, assembly_id)
            if output_key in seen_output_rows:
                continue
            seen_output_rows.add(output_key)

            writer.writerow([organism_name, assembly_id, "not_found_in_evo2_fungi"])
            not_trained_rows += 1

    print(f"Total GenBank fungal assembly rows checked: {total_fungal_assemblies}")
    print(f"Skipped exact Evo2 assembly matches: {skipped_exact}")
    print(f"Skipped versionless Evo2 assembly matches: {skipped_versionless}")
    print(f"Rows written as not trained by Evo2: {not_trained_rows}")
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
