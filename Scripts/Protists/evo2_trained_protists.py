#!/usr/bin/env python3
"""
Find protist names and assemblies that were included in Evo2 training.

Logic:
1. Load NCBI protozoa assembly IDs and paired GCA/GCF IDs.
2. Read Evo2 eukaryotic Assembly_ID and Species_Name rows.
3. Write Evo2 rows whose assembly IDs match NCBI protists.

Inputs:
- Datasets/Plant Pathogen Preprocessing & Evo2/evo2_eukaryotes_alphabetical.txt
- Datasets/NCBI Database/NCBI_database.txt

Outputs:
- Results/Protists/evo2_protists_names_and_assemblies.csv
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
DEFAULT_OUTPUT = PROJECT_ROOT / "Results" / "Protists" / "evo2_protists_names_and_assemblies.csv"
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


def load_ncbi_protist_assembly_ids(path: Path) -> tuple[set[str], set[str]]:
    """Load exact and versionless assembly IDs for NCBI protozoa rows."""
    exact_ids = set()
    base_ids = set()

    for row in read_assembly_summary_rows(path):
        if row.get("group", "").casefold() != NCBI_PROTIST_GROUP:
            continue

        for assembly_id in [row.get("assembly_accession", ""), row.get("gbrs_paired_asm", "")]:
            assembly_id = assembly_id.strip()
            if not assembly_id or assembly_id.casefold() == "na":
                continue

            exact_ids.add(assembly_id)
            base_ids.add(accession_base(assembly_id))

    return exact_ids, base_ids


def read_evo2_rows(path: Path) -> Iterator[tuple[str, str]]:
    """Yield (assembly_id, organism_name) rows from the Evo2 eukaryotes file."""
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        for row in reader:
            assembly_id = row.get("Assembly_ID", "").strip()
            organism_name = row.get("Species_Name", "").strip()
            if assembly_id and organism_name:
                yield assembly_id, organism_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find Evo2-trained protist names and assembly IDs.")
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

    ncbi_exact_ids, ncbi_base_ids = load_ncbi_protist_assembly_ids(args.ncbi_database)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    total_evo2_rows = 0
    protist_rows = 0
    seen_rows = set()

    with args.output.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["organism_name", "assembly_id"])

        for assembly_id, organism_name in read_evo2_rows(args.evo2_eukaryotes):
            total_evo2_rows += 1
            if assembly_id not in ncbi_exact_ids and accession_base(assembly_id) not in ncbi_base_ids:
                continue

            output_key = (organism_name, assembly_id)
            if output_key in seen_rows:
                continue
            seen_rows.add(output_key)

            writer.writerow([organism_name, assembly_id])
            protist_rows += 1

    print(f"Evo2 eukaryote rows checked: {total_evo2_rows}")
    print(f"Evo2 protist rows written: {protist_rows}")
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
