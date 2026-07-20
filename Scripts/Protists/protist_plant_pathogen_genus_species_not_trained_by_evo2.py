#!/usr/bin/env python3
"""
Find NCBI protist species from plant-pathogen genera that Evo2 was not trained on.

Logic: Adds species with same genus but with species not trained by evo2.
1. Load genera from the protist plant-pathogen file.
2. Read NCBI protist name/assembly rows and keep species from those genera.
3. Remove species that Evo2 was trained on, then write the rest.

Inputs:
- Datasets/Protists/evo2_protist_plant_pathogens.txt
- Results/Protists/ncbi_protists_names_and_assemblies.csv
- Results/Protists/evo2_protists_names_and_assemblies.csv

Outputs:
- Results/Protists/protist_plant_pathogen_genus_species_not_trained_by_evo2.csv
"""

import argparse
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GENUS_FILE = PROJECT_ROOT / "Datasets" / "Protists" / "evo2_protist_plant_pathogens.txt"
DEFAULT_NCBI_PROTISTS = PROJECT_ROOT / "Results" / "Protists" / "ncbi_protists_names_and_assemblies.csv"
DEFAULT_EVO2_PROTISTS = PROJECT_ROOT / "Results" / "Protists" / "evo2_protists_names_and_assemblies.csv"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Results"
    / "Protists"
    / "protist_plant_pathogen_genus_species_not_trained_by_evo2.csv"
)


def normalize_genus(value: str) -> str:
    """Normalize a genus name for case-insensitive matching."""
    value = value.strip().strip(" ,;\t\r\n()[]{}")
    if not value:
        return ""
    return value[0].upper() + value[1:].lower()


def extract_genus(organism_name: str) -> str:
    """Extract a comparable genus from an organism name."""
    name = " ".join(organism_name.strip().split())
    if not name:
        return ""

    parts = name.split()
    if parts[0].casefold() == "candidatus" and len(parts) >= 2:
        return normalize_genus(parts[1])

    return normalize_genus(parts[0])


def extract_species_name(organism_name: str) -> str:
    """Return the genus and species epithet from an organism name."""
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


def is_virus_or_viroid_name(organism_name: str) -> bool:
    """Return True for viral/viroid organism names."""
    name = organism_name.casefold()
    return "virus" in name or "viroid" in name


def load_plant_pathogen_genera_and_species(path: Path) -> tuple[set[str], set[str], set[str]]:
    """Load genera plus Y/N species from the protist plant-pathogen file."""
    genera = set()
    trained_species = set()
    not_trained_species = set()

    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split("\t")
            pathogen_name = parts[0].strip()
            status = parts[2].strip().upper() if len(parts) >= 3 else ""
            genus = extract_genus(pathogen_name)
            if genus and genus.casefold() != "pathogen":
                genera.add(genus)

            species_name = extract_species_name(pathogen_name)
            if not species_name:
                continue

            if status == "Y":
                trained_species.add(species_name)
            elif status == "N":
                not_trained_species.add(species_name)

    return genera, trained_species, not_trained_species


def load_evo2_trained_species(path: Path, genera: set[str]) -> set[str]:
    """Load trained species names from the Evo2-trained protists CSV."""
    trained_species = set()
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            organism_name = row.get("organism_name", "").strip()
            if not organism_name:
                continue

            if extract_genus(organism_name) in genera:
                trained_species.add(extract_species_name(organism_name))

    return trained_species


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find NCBI protist species from plant-pathogen genera not trained on by Evo2."
    )
    parser.add_argument("--genus-file", type=Path, default=DEFAULT_GENUS_FILE)
    parser.add_argument("--ncbi-protists", type=Path, default=DEFAULT_NCBI_PROTISTS)
    parser.add_argument("--evo2-protists", type=Path, default=DEFAULT_EVO2_PROTISTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.genus_file.exists():
        raise FileNotFoundError(f"Protist plant-pathogen file not found: {args.genus_file}")
    if not args.ncbi_protists.exists():
        raise FileNotFoundError(f"NCBI protists file not found: {args.ncbi_protists}")
    if not args.evo2_protists.exists():
        raise FileNotFoundError(f"Evo2-trained protists file not found: {args.evo2_protists}")

    genera, file_trained_species, file_not_trained_species = load_plant_pathogen_genera_and_species(args.genus_file)
    if not genera:
        raise ValueError(f"No genera loaded from {args.genus_file}")

    evo2_trained_species = load_evo2_trained_species(args.evo2_protists, genera)
    trained_species = file_trained_species | evo2_trained_species
    output_rows = set()

    total_ncbi_protist_rows = 0
    genus_matched_rows = 0
    trained_species_rows = 0
    virus_viroid_rows = 0

    with args.ncbi_protists.open("r", encoding="utf-8", errors="replace", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            total_ncbi_protist_rows += 1
            organism_name = row.get("organism_name", "").strip()
            assembly_id = row.get("assembly_id", "").strip()
            if not organism_name or not assembly_id:
                continue

            if is_virus_or_viroid_name(organism_name):
                virus_viroid_rows += 1
                continue

            genus = extract_genus(organism_name)
            if genus not in genera:
                continue

            genus_matched_rows += 1
            species_name = extract_species_name(organism_name)
            if species_name in trained_species:
                trained_species_rows += 1
                continue

            output_rows.add((genus, species_name, assembly_id))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["genus", "species", "assembly_id"])
        for row in sorted(output_rows):
            writer.writerow(row)

    print(f"Plant-pathogen genera loaded: {len(genera)}")
    print(f"Plant-pathogen species marked N: {len(file_not_trained_species)}")
    print(f"Plant-pathogen/Evo2 species treated as trained: {len(trained_species)}")
    print(f"NCBI protist rows checked: {total_ncbi_protist_rows}")
    print(f"Rows matching plant-pathogen genera: {genus_matched_rows}")
    print(f"Rows skipped because species was found in Evo2: {trained_species_rows}")
    print(f"Virus/viroid rows skipped: {virus_viroid_rows}")
    print(f"Rows written as not trained by Evo2: {len(output_rows)}")
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
