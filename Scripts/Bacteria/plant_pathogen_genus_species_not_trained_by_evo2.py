#!/usr/bin/env python3
"""
Find NCBI bacterial species in plant-pathogen genera that Evo2 was not trained on.

Logic:
1. Load known bacterial plant-pathogen genera.
2. Stream NCBI bacteria and keep species from those genera.
3. Remove exact or versionless Evo2 assembly matches, then write the rest.

Inputs:
- Datasets/Bacterial Plant Pathogens/bacteria_plant_pathogen_genus.txt
- Datasets/NCBI Database/NCBI_database.txt
- ~/Downloads/evo2_trained_bacteria.txt

Outputs:
- Results/Bacteria/plant_pathogen_genus_species_not_trained_by_evo2.csv
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GENUS_FILE = (
    PROJECT_ROOT
    / "Datasets"
    / "Bacterial Plant Pathogens"
    / "bacteria_plant_pathogen_genus.txt"
)
DEFAULT_NCBI_DATABASE = PROJECT_ROOT / "Datasets" / "NCBI Database" / "NCBI_database.txt"
DEFAULT_EVO2_BACTERIA = Path.home() / "Downloads" / "evo2_trained_bacteria.txt"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Results"
    / "Bacteria"
    / "plant_pathogen_genus_species_not_trained_by_evo2.csv"
)


def normalize_genus(value: str) -> str:
    """Normalize a genus name for case-insensitive matching."""
    value = value.strip().strip(" ,;\t\r\n()[]{}")
    if not value:
        return ""
    normalized = value[0].upper() + value[1:].lower()
    if normalized == "Xanthamonas":
        return "Xanthomonas"
    return normalized


def extract_genus(organism_name: str) -> str:
    """
    Extract a comparable genus from an organism name.

    Examples:
    Agrobacterium tumefaciens -> Agrobacterium
    Candidatus Liberibacter asiaticus -> Liberibacter
    [Clostridium] leptum -> Clostridium
    """
    name = " ".join(organism_name.strip().split())
    if not name:
        return ""

    parts = name.split()
    if parts[0].casefold() == "candidatus" and len(parts) >= 2:
        return normalize_genus(parts[1])

    return normalize_genus(parts[0])


def extract_species_name(organism_name: str) -> str:
    """Return the genus and species epithet."""
    name = " ".join(organism_name.strip().split())
    if not name:
        return ""

    parts = name.split()
    if parts[0].casefold() == "candidatus":
        if len(parts) >= 3:
            return f"{normalize_genus(parts[1])} {parts[2]}"
        if len(parts) == 2:
            return normalize_genus(parts[1])
        return ""

    if len(parts) >= 2:
        return f"{normalize_genus(parts[0])} {parts[1]}"

    return normalize_genus(parts[0])


def accession_base(assembly_id: str) -> str:
    """Return accession without version suffix."""
    return assembly_id.rsplit(".", 1)[0]


def load_plant_pathogen_genera(path: Path) -> set[str]:
    """Load genera from the first column of the bacterial plant-pathogen file."""
    genera = set()

    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            pathogen_name = line.split("\t", 1)[0].strip()
            genus = extract_genus(pathogen_name)
            if genus and genus.casefold() != "pathogen":
                genera.add(genus)

    return genera


def load_evo2_bacteria(path: Path) -> tuple[set[str], set[str], set[str]]:
    """Load Evo2 trained bacteria assembly IDs and trained genera."""
    exact_ids = set()
    base_ids = set()
    genera = set()

    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        for row in reader:
            assembly_id = row.get("Assembly_ID", "").strip()
            species_name = row.get("Species_Name", "").strip()

            if assembly_id:
                exact_ids.add(assembly_id)
                base_ids.add(accession_base(assembly_id))

            genus = extract_genus(species_name)
            if genus:
                genera.add(genus)

    return exact_ids, base_ids, genera


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


def is_trained_assembly(
    assembly_id: str,
    paired_assembly_id: str,
    evo2_exact_ids: set[str],
    evo2_base_ids: set[str],
) -> bool:
    """Return True if either NCBI accession for a row is present in Evo2."""
    candidate_ids = [assembly_id, paired_assembly_id]
    for candidate_id in candidate_ids:
        if not candidate_id or candidate_id.casefold() == "na":
            continue
        if candidate_id in evo2_exact_ids:
            return True
        if accession_base(candidate_id) in evo2_base_ids:
            return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Find NCBI bacterial species in plant-pathogen genera that are not present "
            "in Evo2 trained bacteria assemblies."
        )
    )
    parser.add_argument("--genus-file", type=Path, default=DEFAULT_GENUS_FILE)
    parser.add_argument("--ncbi-database", type=Path, default=DEFAULT_NCBI_DATABASE)
    parser.add_argument("--evo2-bacteria", type=Path, default=DEFAULT_EVO2_BACTERIA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.genus_file.exists():
        raise FileNotFoundError(f"Plant pathogen genus file not found: {args.genus_file}")
    if not args.ncbi_database.exists():
        raise FileNotFoundError(f"NCBI database file not found: {args.ncbi_database}")
    if not args.evo2_bacteria.exists():
        raise FileNotFoundError(f"Evo2 trained bacteria file not found: {args.evo2_bacteria}")

    plant_pathogen_genera = load_plant_pathogen_genera(args.genus_file)
    if not plant_pathogen_genera:
        raise ValueError(f"No plant-pathogen genera loaded from {args.genus_file}")

    evo2_exact_ids, evo2_base_ids, evo2_genera = load_evo2_bacteria(args.evo2_bacteria)
    searched_genera = plant_pathogen_genera & evo2_genera
    if not searched_genera:
        raise ValueError("No plant-pathogen genera are represented in Evo2 trained bacteria")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    bacteria_rows = 0
    candidate_rows = 0
    trained_rows = 0
    species_to_all_assemblies: dict[tuple[str, str], set[str]] = defaultdict(set)
    species_to_trained_assemblies: dict[tuple[str, str], set[str]] = defaultdict(set)

    for row in read_assembly_summary_rows(args.ncbi_database):
        total_rows += 1
        if row.get("group", "").casefold() != "bacteria":
            continue

        bacteria_rows += 1
        organism_name = row.get("organism_name", "").strip()
        genus = extract_genus(organism_name)
        if genus not in searched_genera:
            continue

        species_name = extract_species_name(organism_name)
        if not species_name:
            continue

        candidate_rows += 1
        assembly_id = row.get("assembly_accession", "").strip()
        paired_assembly_id = row.get("gbrs_paired_asm", "").strip()
        species_key = (genus, species_name)
        if assembly_id:
            species_to_all_assemblies[species_key].add(assembly_id)

        if is_trained_assembly(assembly_id, paired_assembly_id, evo2_exact_ids, evo2_base_ids):
            trained_rows += 1
            species_to_trained_assemblies[species_key].add(assembly_id)

    species_with_no_trained_assemblies = set(species_to_all_assemblies) - set(
        species_to_trained_assemblies
    )

    with args.output.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file, lineterminator="\n")
        writer.writerow(["species_name", "assembly_ids"])
        for genus, species_name in sorted(species_with_no_trained_assemblies):
            species_key = (genus, species_name)
            assembly_ids = sorted(species_to_all_assemblies[species_key])
            writer.writerow([species_name, ";".join(assembly_ids)])

    print(f"Plant-pathogen genera loaded: {len(plant_pathogen_genera)}")
    print(f"Plant-pathogen genera searched: {len(searched_genera)}")
    print(f"NCBI rows checked: {total_rows}")
    print(f"NCBI bacterial rows checked: {bacteria_rows}")
    print(f"Candidate NCBI assembly rows in searched genera: {candidate_rows}")
    print(f"Candidate rows found in Evo2 training: {trained_rows}")
    print(f"Species with no trained assemblies: {len(species_with_no_trained_assemblies)}")
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
