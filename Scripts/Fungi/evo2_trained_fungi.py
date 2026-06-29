#!/usr/bin/env python3
"""
Classify Evo2 eukaryotic entries as fungi or not fungi.

Logic:
1. Load Evo2 eukaryotic assembly/species rows.
2. Match assemblies to GenBank group metadata, with name matching as fallback.
3. Write rows showing which Evo2 entries are fungi.

Inputs:
- Datasets/Plant Pathogen Preprocessing & Evo2/evo2_eukaryotic_dataset.txt
- Datasets/Genus List & GenBank/all_eukaryotes_and_assembly_genbank.txt
- Results/Genus List & GenBank/genbank_fungi_unique_names.csv

Outputs:
- Results/Genus List & GenBank/evo2_trained_fungi.csv
"""

import argparse
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVO2_FILE = PROJECT_ROOT / "Datasets" / "Plant Pathogen Preprocessing & Evo2" / "evo2_eukaryotic_dataset.txt"
DEFAULT_ASSEMBLY_SUMMARY = PROJECT_ROOT / "Datasets" / "Genus List & GenBank" / "all_eukaryotes_and_assembly_genbank.txt"
DEFAULT_FUNGAL_NAMES = PROJECT_ROOT / "Results" / "Genus List & GenBank" / "genbank_fungi_unique_names.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "Results" / "Genus List & GenBank" / "evo2_trained_fungi.csv"


def normalize_name(value: str) -> str:
    """Normalize organism names for exact name fallback matching."""
    return " ".join(value.strip().casefold().split())


def accession_base(assembly_id: str) -> str:
    """Return accession without version suffix."""
    return assembly_id.rsplit(".", 1)[0]


def load_fungal_names(path: Path) -> set[str]:
    """Load known fungal organism names for fallback name matching."""
    names = set()
    if not path.exists():
        return names

    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames and "organism_name" in reader.fieldnames:
            for row in reader:
                name = normalize_name(row.get("organism_name", ""))
                if name:
                    names.add(name)
        else:
            file.seek(0)
            for line in file:
                name = normalize_name(line)
                if name and name != "organism_name":
                    names.add(name)

    return names


def load_assembly_group_lookup(path: Path):
    """
    Map assembly IDs to GenBank metadata.

    Exact IDs are preferred. Versionless IDs are used only when the base
    accession maps unambiguously to one row in the assembly summary.
    """
    exact_lookup = {}
    base_lookup = {}
    duplicate_bases = set()
    header = None

    with path.open("r", encoding="utf-8", errors="replace") as file:
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
                raise ValueError("Could not find #assembly_accession header")

            values = line.split("\t")
            if len(values) < len(header):
                values += [""] * (len(header) - len(values))
            row = dict(zip(header, values))

            metadata = {
                "group": row.get("group", ""),
                "assembly_level": row.get("assembly_level", ""),
                "genbank_assembly_accession": row.get("assembly_accession", ""),
                "refseq_paired_assembly": row.get("gbrs_paired_asm", ""),
                "genbank_organism_name": row.get("organism_name", ""),
            }

            for accession in [row.get("assembly_accession", ""), row.get("gbrs_paired_asm", "")]:
                if not accession or accession.lower() == "na":
                    continue

                exact_lookup[accession] = metadata
                base_id = accession_base(accession)
                if base_id in base_lookup and base_lookup[base_id] != metadata:
                    duplicate_bases.add(base_id)
                else:
                    base_lookup[base_id] = metadata

    for base_id in duplicate_bases:
        base_lookup.pop(base_id, None)

    return exact_lookup, base_lookup


def parse_evo2_rows(path: Path):
    """
    Yield Evo2 rows as (assembly_id, organism_name).

    Expected input is tab-delimited with columns like:
    Assembly_ID    Species_Name
    """
    with path.open("r", encoding="utf-8", errors="replace") as file:
        header = None
        for line in file:
            line = line.rstrip("\n")
            if not line:
                continue

            parts = line.split("\t")
            if header is None:
                lower_parts = [part.strip().casefold() for part in parts]
                if "assembly_id" in lower_parts and ("species_name" in lower_parts or "organism_name" in lower_parts):
                    header = lower_parts
                    continue
                header = []

            if header:
                row = dict(zip(header, parts))
                assembly_id = row.get("assembly_id", "").strip()
                organism_name = (row.get("species_name") or row.get("organism_name") or "").strip()
            else:
                assembly_id = parts[0].strip() if parts else ""
                organism_name = parts[1].strip() if len(parts) > 1 else ""

            if assembly_id or organism_name:
                yield assembly_id, organism_name


def classify_row(assembly_id: str, organism_name: str, exact_lookup: dict, base_lookup: dict, fungal_names: set[str]):
    """Classify one Evo2 row as fungi or not."""
    metadata = None
    match_method = ""

    if assembly_id:
        metadata = exact_lookup.get(assembly_id)
        if metadata is not None:
            match_method = "assembly_exact"
        else:
            metadata = base_lookup.get(accession_base(assembly_id))
            if metadata is not None:
                match_method = "assembly_versionless"

    if metadata is not None:
        is_fungi = metadata["group"].casefold() == "fungi"
        return is_fungi, match_method, metadata

    if normalize_name(organism_name) in fungal_names:
        return True, "name_exact", {
            "group": "fungi",
            "assembly_level": "",
            "genbank_assembly_accession": "",
            "refseq_paired_assembly": "",
            "genbank_organism_name": organism_name,
        }

    return False, "not_matched", {
        "group": "",
        "assembly_level": "",
        "genbank_assembly_accession": "",
        "refseq_paired_assembly": "",
        "genbank_organism_name": "",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find fungi in an Evo2 eukaryote organism file.")
    parser.add_argument("--evo2-file", type=Path, default=DEFAULT_EVO2_FILE)
    parser.add_argument("--assembly-summary", type=Path, default=DEFAULT_ASSEMBLY_SUMMARY)
    parser.add_argument("--fungal-names", type=Path, default=DEFAULT_FUNGAL_NAMES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--all-rows",
        action="store_true",
        help="Write every Evo2 row with an is_fungi column. Default writes only fungi rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.evo2_file.exists():
        raise FileNotFoundError(f"Evo2 file not found: {args.evo2_file}")
    if not args.assembly_summary.exists():
        raise FileNotFoundError(f"Assembly summary not found: {args.assembly_summary}")

    exact_lookup, base_lookup = load_assembly_group_lookup(args.assembly_summary)
    fungal_names = load_fungal_names(args.fungal_names)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    rows_read = 0
    rows_written = 0
    fungi_count = 0

    with args.output.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow([
            "assembly_id",
            "organism_name",
            "is_fungi",
            "match_method",
            "genbank_group",
            "assembly_level",
            "genbank_assembly_accession",
            "refseq_paired_assembly",
            "genbank_organism_name",
        ])

        for assembly_id, organism_name in parse_evo2_rows(args.evo2_file):
            rows_read += 1
            is_fungi, match_method, metadata = classify_row(
                assembly_id,
                organism_name,
                exact_lookup,
                base_lookup,
                fungal_names,
            )
            if is_fungi:
                fungi_count += 1
            if not args.all_rows and not is_fungi:
                continue

            writer.writerow([
                assembly_id,
                organism_name,
                "Y" if is_fungi else "N",
                match_method,
                metadata["group"],
                metadata["assembly_level"],
                metadata["genbank_assembly_accession"],
                metadata["refseq_paired_assembly"],
                metadata["genbank_organism_name"],
            ])
            rows_written += 1

    print(f"Read Evo2 rows: {rows_read}")
    print(f"Fungi rows found: {fungi_count}")
    print(f"Rows written: {rows_written}")
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
