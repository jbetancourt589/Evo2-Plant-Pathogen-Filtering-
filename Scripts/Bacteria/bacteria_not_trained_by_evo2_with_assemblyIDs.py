#!/usr/bin/env python3
"""
Find NCBI bacterial assemblies that are not in the Evo2 trained bacteria list.

Logic:
1. Load exact and versionless Evo2 trained bacterial assembly IDs.
2. Compare each NCBI bacterial name/assembly row.
3. Write assemblies that are not found in Evo2.

Inputs:
- Results/Bacteria/all_ncbi_bacteria_and_assemblyIDs.txt
- ~/Downloads/evo2_trained_bacteria.txt

Outputs:
- Results/Bacteria/bacteria_not_trained_by_evo2_with_assemblyIDs.txt
"""

import argparse
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NCBI_BACTERIA = PROJECT_ROOT / "Results" / "Bacteria" / "all_ncbi_bacteria_and_assemblyIDs.txt"
DEFAULT_EVO2_BACTERIA = Path.home() / "Downloads" / "evo2_trained_bacteria.txt"
DEFAULT_OUTPUT = PROJECT_ROOT / "Results" / "Bacteria" / "bacteria_not_trained_by_evo2_with_assemblyIDs.txt"


def accession_base(assembly_id: str) -> str:
    """Return accession without version suffix."""
    return assembly_id.rsplit(".", 1)[0]


def load_evo2_bacteria_assembly_ids(path: Path) -> tuple[set[str], set[str]]:
    """Load exact and versionless assembly IDs from the Evo2 trained bacteria TXT file."""
    exact_ids = set()
    base_ids = set()

    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        for row in reader:
            assembly_id = row.get("Assembly_ID", "").strip()
            if not assembly_id:
                continue
            exact_ids.add(assembly_id)
            base_ids.add(accession_base(assembly_id))

    return exact_ids, base_ids


def read_ncbi_bacteria_rows(path: Path):
    """Yield organism_name and assembly_id rows from the NCBI bacteria TXT file."""
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        for row in reader:
            organism_name = row.get("organism_name", "").strip()
            assembly_id = row.get("assembly_id", "").strip()
            if organism_name or assembly_id:
                yield organism_name, assembly_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find NCBI bacterial assemblies not trained on by Evo2.")
    parser.add_argument("--ncbi-bacteria", type=Path, default=DEFAULT_NCBI_BACTERIA)
    parser.add_argument("--evo2-bacteria", type=Path, default=DEFAULT_EVO2_BACTERIA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.ncbi_bacteria.exists():
        raise FileNotFoundError(f"NCBI bacteria assembly file not found: {args.ncbi_bacteria}")
    if not args.evo2_bacteria.exists():
        raise FileNotFoundError(f"Evo2 trained bacteria file not found: {args.evo2_bacteria}")

    evo2_exact_ids, evo2_base_ids = load_evo2_bacteria_assembly_ids(args.evo2_bacteria)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    total_ncbi_assemblies = 0
    skipped_exact = 0
    skipped_versionless = 0
    not_trained_rows = 0
    seen_output_rows = set()

    with args.output.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file, delimiter="\t", lineterminator="\n")
        writer.writerow(["organism_name", "assembly_id", "not_trained_reason"])

        for organism_name, assembly_id in read_ncbi_bacteria_rows(args.ncbi_bacteria):
            total_ncbi_assemblies += 1

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

            writer.writerow([organism_name, assembly_id, "not_found_in_evo2_trained_bacteria"])
            not_trained_rows += 1

    print(f"Total NCBI bacterial assembly rows checked: {total_ncbi_assemblies}")
    print(f"Skipped exact Evo2 assembly matches: {skipped_exact}")
    print(f"Skipped versionless Evo2 assembly matches: {skipped_versionless}")
    print(f"Rows written as not trained by Evo2: {not_trained_rows}")
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
