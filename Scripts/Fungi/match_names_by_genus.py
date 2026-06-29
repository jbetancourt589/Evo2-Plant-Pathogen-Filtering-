#!/usr/bin/env python3
"""
Match organism names from a large NCBI assembly_summary file using a genus list.

Logic:
1. Load target fungal genera.
2. Stream GenBank eukaryote assembly rows and keep fungi.
3. Write matched genus rows plus unique fungal names and assemblies.

Inputs:
- Datasets/Genus List & GenBank/fungal_genus_only_no_duplicates.txt
- Datasets/Genus List & GenBank/all_eukaryotes_and_assembly_genbank.txt

Outputs:
- Results/Genus List & GenBank/genbank_fungi_names_by_genus.csv
- Results/Genus List & GenBank/genbank_fungi_unique_names.csv
- Results/Genus List & GenBank/all_genbank_fungi_and_assemblyIDs.csv
"""

import argparse
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "Datasets" / "Genus List & GenBank"
DEFAULT_GENUS_FILE = DEFAULT_INPUT_DIR / "fungal_genus_only_no_duplicates.txt"
DEFAULT_ASSEMBLY_FILE = DEFAULT_INPUT_DIR / "all_eukaryotes_and_assembly_genbank.txt"
DEFAULT_OUTDIR = PROJECT_ROOT / "Results" / "Genus List & GenBank"


def normalize_genus(value: str) -> str:
    """Normalize a genus name to Genus capitalization."""
    value = value.strip()
    if not value:
        return ""

    value = value.strip(" ,;\t\r\n()[]{}")
    if not value:
        return ""

    return value[0].upper() + value[1:].lower()


def load_genera(genus_file: Path) -> set[str]:
    """Load genus names from a CSV or TXT file."""
    genera = set()

    with genus_file.open("r", encoding="utf-8", errors="replace", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        sample_lines = sample.splitlines()
        first_line = sample_lines[0] if sample_lines else ""

        if "," in first_line or first_line.strip().lower() == "genus":
            reader = csv.DictReader(f)
            lower_fieldnames = [name.lower() for name in reader.fieldnames or []]
            if "genus" in lower_fieldnames:
                genus_col = next(name for name in reader.fieldnames or [] if name.lower() == "genus")
                for row in reader:
                    genus = normalize_genus(row.get(genus_col, ""))
                    if genus:
                        genera.add(genus)
            else:
                f.seek(0)
                reader2 = csv.reader(f)
                for row in reader2:
                    if not row:
                        continue
                    genus = normalize_genus(row[0])
                    if genus and genus.lower() != "genus":
                        genera.add(genus)
        else:
            for line in f:
                genus = normalize_genus(line)
                if genus and genus.lower() != "genus":
                    genera.add(genus)

    return genera


def extract_genus(organism_name: str) -> str:
    """
    Extract genus from an assembly_summary organism_name.

    Examples:
    Fusarium oxysporum -> Fusarium
    Candidatus Liberibacter asiaticus -> Liberibacter
    [Candida] auris -> Candida
    """
    name = " ".join(organism_name.strip().split())
    if not name:
        return ""

    parts = name.split()
    if not parts:
        return ""

    if parts[0].lower() == "candidatus" and len(parts) >= 2:
        return normalize_genus(parts[1])

    return normalize_genus(parts[0])


def is_virus_or_viroid_name(organism_name: str) -> bool:
    """Return True for viral/viroid GenBank organism names."""
    name = organism_name.casefold()
    return "virus" in name or "viroid" in name


def read_assembly_summary_rows(assembly_file: Path):
    """
    Yield (header, row) pairs from an NCBI assembly_summary.txt file.

    The file can be very large, so this streams rows instead of loading the
    whole assembly summary into memory.
    """
    header = None

    with assembly_file.open("r", encoding="utf-8", errors="replace", newline="") as f:
        for line in f:
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

            yield header, dict(zip(header, values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Match assembly organism names by genus list.")
    parser.add_argument(
        "--genus-file",
        default=DEFAULT_GENUS_FILE,
        type=Path,
        help=f"CSV/TXT file containing genus names. Default: {DEFAULT_GENUS_FILE}",
    )
    parser.add_argument(
        "--assembly-file",
        default=DEFAULT_ASSEMBLY_FILE,
        type=Path,
        help=f"NCBI assembly_summary.txt file. Default: {DEFAULT_ASSEMBLY_FILE}",
    )
    parser.add_argument(
        "--outdir",
        default=DEFAULT_OUTDIR,
        type=Path,
        help=f"Output directory. Default: {DEFAULT_OUTDIR}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    if not args.genus_file.exists():
        raise FileNotFoundError(f"Genus file not found: {args.genus_file}")
    if not args.assembly_file.exists():
        raise FileNotFoundError(f"Assembly file not found: {args.assembly_file}")

    genera = load_genera(args.genus_file)
    if not genera:
        raise ValueError(f"No genera loaded from {args.genus_file}")

    organism_rows = set()
    fungal_organism_names = set()
    fungal_organism_assembly_rows = set()

    total_rows = 0
    fungi_rows = 0
    matched_rows = 0
    unmatched_rows = 0
    excluded_fungal_virus_viroid_rows = 0
    fungal_rows_written = 0

    organism_names_path = args.outdir / "genbank_fungi_names_by_genus.csv"
    fungal_names_path = args.outdir / "genbank_fungi_unique_names.csv"
    fungal_assembly_ids_path = args.outdir / "all_genbank_fungi_and_assemblyIDs.csv"

    for _header, row in read_assembly_summary_rows(args.assembly_file):
        total_rows += 1
        if row.get("group", "").casefold() != "fungi":
            continue

        fungi_rows += 1
        organism_name = row.get("organism_name", "")
        assembly_id = row.get("assembly_accession", "")
        extracted_genus = extract_genus(organism_name)

        if is_virus_or_viroid_name(organism_name):
            excluded_fungal_virus_viroid_rows += 1
        else:
            fungal_organism_names.add(organism_name)
            fungal_organism_assembly_rows.add((organism_name, assembly_id))
            fungal_rows_written += 1

            if extracted_genus in genera:
                matched_rows += 1
                organism_rows.add((extracted_genus, organism_name, assembly_id))
            else:
                unmatched_rows += 1

    with organism_names_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["genus", "organism_name", "assembly_id"])
        for genus in sorted(genera):
            genus_rows = [row for row in organism_rows if row[0] == genus]
            if not genus_rows:
                writer.writerow([genus, "", ""])
                continue

            for row in sorted(genus_rows, key=lambda item: (item[1], item[2])):
                writer.writerow(row)

    with fungal_names_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["organism_name"])
        for organism_name in sorted(fungal_organism_names):
            writer.writerow([organism_name])

    with fungal_assembly_ids_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["organism_name", "assembly_id"])
        for organism_name, assembly_id in sorted(fungal_organism_assembly_rows):
            writer.writerow([organism_name, assembly_id])

    print("DONE: Genus matching complete.")
    print(f"Genera loaded: {len(genera)}")
    print(f"Assembly rows processed: {total_rows}")
    print(f"Fungi rows processed: {fungi_rows}")
    print(f"Matched rows: {matched_rows}")
    print(f"Unmatched rows: {unmatched_rows}")
    print(f"Fungal virus/viroid rows excluded: {excluded_fungal_virus_viroid_rows}")
    print(f"Fungal organism rows written with assembly IDs: {fungal_rows_written}")
    print(f"Unique fungal organism names written: {len(fungal_organism_names)}")
    print(f"Wrote: {organism_names_path}")
    print(f"Wrote: {fungal_names_path}")
    print(f"Wrote: {fungal_assembly_ids_path}")


if __name__ == "__main__":
    main()
