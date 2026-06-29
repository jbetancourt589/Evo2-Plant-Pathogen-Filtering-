#!/usr/bin/env python3
"""
Find NCBI bacterial names that are not in the Evo2 trained bacteria list.

Logic:
1. Load Evo2 trained bacterial Species_Name values.
2. Compare each unique NCBI bacterial name after simple normalization.
3. Write names that are not found in the Evo2 list.

Inputs:
- Results/Bacteria/ncbi_bacteria_unique_names.csv
- ~/Downloads/evo2_trained_bacteria.txt

Outputs:
- Results/Bacteria/bacteria_names_not_trained_by_evo2.csv
"""

import argparse
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NCBI_NAMES = PROJECT_ROOT / "Results" / "Bacteria" / "ncbi_bacteria_unique_names.csv"
DEFAULT_EVO2_BACTERIA = Path.home() / "Downloads" / "evo2_trained_bacteria.txt"
DEFAULT_OUTPUT = PROJECT_ROOT / "Results" / "Bacteria" / "bacteria_names_not_trained_by_evo2.csv"


def normalize_name(value: str) -> str:
    """Normalize organism names for exact name comparison."""
    return " ".join(value.strip().casefold().split())


def load_evo2_bacteria_names(path: Path) -> set[str]:
    """Load normalized Species_Name values from the Evo2 trained bacteria TXT file."""
    names = set()
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        for row in reader:
            name = normalize_name(row.get("Species_Name", ""))
            if name:
                names.add(name)
    return names


def read_ncbi_names(path: Path):
    """Yield organism_name values from the NCBI bacteria unique-name CSV."""
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            organism_name = row.get("organism_name", "").strip()
            if organism_name:
                yield organism_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find NCBI bacterial names not trained on by Evo2.")
    parser.add_argument("--ncbi-names", type=Path, default=DEFAULT_NCBI_NAMES)
    parser.add_argument("--evo2-bacteria", type=Path, default=DEFAULT_EVO2_BACTERIA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.ncbi_names.exists():
        raise FileNotFoundError(f"NCBI bacteria names file not found: {args.ncbi_names}")
    if not args.evo2_bacteria.exists():
        raise FileNotFoundError(f"Evo2 trained bacteria file not found: {args.evo2_bacteria}")

    evo2_names = load_evo2_bacteria_names(args.evo2_bacteria)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    total_ncbi_names = 0
    matched_names = 0
    not_trained_names = []

    for organism_name in read_ncbi_names(args.ncbi_names):
        total_ncbi_names += 1
        if normalize_name(organism_name) in evo2_names:
            matched_names += 1
            continue
        not_trained_names.append(organism_name)

    with args.output.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["organism_name"])
        for organism_name in sorted(not_trained_names):
            writer.writerow([organism_name])

    print(f"Total unique NCBI bacterial names checked: {total_ncbi_names}")
    print(f"Names found in Evo2 trained bacteria: {matched_names}")
    print(f"Names written as not trained by Evo2: {len(not_trained_names)}")
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
