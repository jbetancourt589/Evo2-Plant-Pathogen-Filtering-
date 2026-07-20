#!/usr/bin/env python3
"""
Find NCBI protist assemblies that were not included in Evo2 training.

Logic:
1. Load exact and versionless Evo2 eukaryotic assembly IDs.
2. Stream NCBI rows where the group is protozoa.
3. Write protist name/assembly rows whose assembly IDs are not in Evo2.

Inputs:
- Datasets/Plant Pathogen Preprocessing & Evo2/evo2_eukaryotes_alphabetical.txt
- Datasets/NCBI Database/NCBI_database.txt

Outputs:
- Results/Protists/evo2_not_trained_protists_name_and_assemblies.csv
"""

import argparse
import csv
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVO2_EUKARYOTES = (
    PROJECT_ROOT
    / "Datasets"
    / "Plant Pathogen Preprocessing & Evo2"
    / "evo2_eukaryotes_alphabetical.txt"
)
DEFAULT_NCBI_DATABASE = PROJECT_ROOT / "Datasets" / "NCBI Database" / "NCBI_database.txt"
DEFAULT_OUTPUT = PROJECT_ROOT / "Results" / "Protists" / "evo2_not_trained_protists_name_and_assemblies.csv"
NCBI_PROTIST_GROUP = "protozoa"


def accession_base(assembly_id: str) -> str:
    """Return accession without version suffix."""
    return assembly_id.rsplit(".", 1)[0]


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


def load_evo2_assembly_ids(path: Path) -> tuple[set[str], set[str]]:
    """Load exact and versionless Evo2 assembly IDs."""
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


def is_trained_assembly(assembly_id: str, paired_assembly_id: str, exact_ids: set[str], base_ids: set[str]) -> bool:
    """Return True when an NCBI assembly or paired GCA/GCF assembly appears in Evo2."""
    for candidate_id in [assembly_id, paired_assembly_id]:
        candidate_id = candidate_id.strip()
        if not candidate_id or candidate_id.casefold() == "na":
            continue

        if candidate_id in exact_ids or accession_base(candidate_id) in base_ids:
            return True

    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find NCBI protist assemblies not trained on by Evo2.")
    parser.add_argument("--evo2-eukaryotes", type=Path, default=DEFAULT_EVO2_EUKARYOTES)
    parser.add_argument("--ncbi-database", type=Path, default=DEFAULT_NCBI_DATABASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.evo2_eukaryotes.exists():
        raise FileNotFoundError(f"Evo2 eukaryotes file not found: {args.evo2_eukaryotes}")
    if not args.ncbi_database.exists():
        raise FileNotFoundError(f"NCBI database file not found: {args.ncbi_database}")

    evo2_exact_ids, evo2_base_ids = load_evo2_assembly_ids(args.evo2_eukaryotes)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    total_ncbi_rows = 0
    protist_rows = 0
    trained_rows = 0
    not_trained_rows = 0
    seen_output_rows = set()

    with args.output.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["organism_name", "assembly_id"])

        for row in read_assembly_summary_rows(args.ncbi_database):
            total_ncbi_rows += 1
            if row.get("group", "").casefold() != NCBI_PROTIST_GROUP:
                continue

            organism_name = row.get("organism_name", "").strip()
            assembly_id = row.get("assembly_accession", "").strip()
            paired_assembly_id = row.get("gbrs_paired_asm", "").strip()
            if not organism_name or not assembly_id:
                continue

            protist_rows += 1
            if is_trained_assembly(assembly_id, paired_assembly_id, evo2_exact_ids, evo2_base_ids):
                trained_rows += 1
                continue

            output_key = (organism_name, assembly_id)
            if output_key in seen_output_rows:
                continue
            seen_output_rows.add(output_key)

            writer.writerow([organism_name, assembly_id])
            not_trained_rows += 1

    print(f"NCBI rows checked: {total_ncbi_rows}")
    print(f"NCBI protist assembly rows checked: {protist_rows}")
    print(f"Protist assembly rows found in Evo2: {trained_rows}")
    print(f"Protist assembly rows written as not trained by Evo2: {not_trained_rows}")
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
