#!/usr/bin/env python3
"""
Add assembly-level types to fungal assemblies marked Y.

Logic:
1. Read Y rows and assembly IDs from fungal_list_final.txt.
2. Look up each assembly in the GenBank assembly summary.
3. Write each fungal assembly with its assembly type.

Inputs:
- ~/Downloads/fungal_list_final.txt
- Datasets/Genus List & GenBank/all_eukaryotes_and_assembly_genbank.txt

Outputs:
- Results/Genus List & GenBank/fungal_y_assemblies_with_types.csv
"""

import argparse
from collections import Counter
import csv
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FUNGAL_LIST = Path.home() / "Downloads" / "fungal_list_final.txt"
DEFAULT_ASSEMBLY_SUMMARY = PROJECT_ROOT / "Datasets" / "Genus List & GenBank" / "all_eukaryotes_and_assembly_genbank.txt"
DEFAULT_OUTPUT = PROJECT_ROOT / "Results" / "Genus List & GenBank" / "fungal_y_assemblies_with_types.csv"
ASSEMBLY_ID_RE = re.compile(r"GC[AF]_\d+\.\d+")


def parse_fungal_list(path: Path):
    """Yield Y rows as (organism_name, category, assembly_id)."""
    with path.open("r", encoding="utf-8", errors="replace") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split("\t")
            if len(parts) < 3:
                continue

            organism_name = parts[0].strip()
            category = parts[1].strip()
            status = parts[2].strip().upper()
            if status != "Y":
                continue

            assembly_text = "\t".join(parts[3:]) if len(parts) > 3 else ""
            for assembly_id in ASSEMBLY_ID_RE.findall(assembly_text):
                yield organism_name, category, assembly_id


def accession_base(assembly_id: str) -> str:
    """Return accession without version suffix."""
    return assembly_id.rsplit(".", 1)[0]


def load_assembly_levels(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Map exact and versionless GCA/GCF assembly IDs to GenBank metadata."""
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
                "assembly_level": row.get("assembly_level", ""),
                "genbank_assembly_accession": row.get("assembly_accession", ""),
                "refseq_paired_assembly": row.get("gbrs_paired_asm", ""),
                "genbank_organism_name": row.get("organism_name", ""),
            }

            assembly_accession = row.get("assembly_accession", "")
            if assembly_accession:
                exact_lookup[assembly_accession] = metadata
                base_id = accession_base(assembly_accession)
                if base_id in base_lookup and base_lookup[base_id] != metadata:
                    duplicate_bases.add(base_id)
                else:
                    base_lookup[base_id] = metadata

            paired_accession = row.get("gbrs_paired_asm", "")
            if paired_accession and paired_accession.lower() != "na":
                exact_lookup[paired_accession] = metadata
                base_id = accession_base(paired_accession)
                if base_id in base_lookup and base_lookup[base_id] != metadata:
                    duplicate_bases.add(base_id)
                else:
                    base_lookup[base_id] = metadata

    for base_id in duplicate_bases:
        base_lookup.pop(base_id, None)

    return exact_lookup, base_lookup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add assembly types to Y rows from fungal_list_final.txt.")
    parser.add_argument("--fungal-list", type=Path, default=DEFAULT_FUNGAL_LIST)
    parser.add_argument("--assembly-summary", type=Path, default=DEFAULT_ASSEMBLY_SUMMARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.fungal_list.exists():
        raise FileNotFoundError(f"Fungal list not found: {args.fungal_list}")
    if not args.assembly_summary.exists():
        raise FileNotFoundError(f"Assembly summary not found: {args.assembly_summary}")

    exact_assembly_lookup, base_assembly_lookup = load_assembly_levels(args.assembly_summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    missing_count = 0
    versionless_match_count = 0
    seen = set()
    output_rows = []
    assembly_type_counts = Counter()

    for organism_name, category, assembly_id in parse_fungal_list(args.fungal_list):
        key = (organism_name, category, assembly_id)
        if key in seen:
            continue
        seen.add(key)

        metadata = exact_assembly_lookup.get(assembly_id)
        if metadata is None:
            metadata = base_assembly_lookup.get(accession_base(assembly_id))
            if metadata is not None:
                versionless_match_count += 1

        if metadata is None:
            missing_count += 1
            metadata = {
                "assembly_level": "N/A",
                "genbank_assembly_accession": "",
                "refseq_paired_assembly": "",
                "genbank_organism_name": "",
            }

        assembly_type = metadata["assembly_level"]
        output_rows.append([organism_name, assembly_id, assembly_type])
        assembly_type_counts[assembly_type] += 1
        rows_written += 1

    with args.output.open("w", encoding="utf-8", newline="") as output_file:
        output_file.write("# Assembly type counts\n")
        for assembly_type, count in sorted(assembly_type_counts.items(), key=lambda item: (-item[1], item[0])):
            output_file.write(f"# {assembly_type},{count}\n")
        output_file.write("#\n")

        writer = csv.writer(output_file)
        writer.writerow(["organism_name", "assembly_id", "assembly_type"])
        writer.writerows(output_rows)

    print(f"Wrote: {args.output}")
    print(f"Rows written: {rows_written}")
    print(f"Versionless assembly ID matches: {versionless_match_count}")
    print(f"Assembly IDs not found in GenBank summary: {missing_count}")


if __name__ == "__main__":
    main()
