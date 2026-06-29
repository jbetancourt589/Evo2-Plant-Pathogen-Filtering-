# Logic for `bacteria_names_not_trained_by_evo2.csv`

## Script

```text
Scripts/Bacteria/create_bacteria_names_not_trained_by_evo2.py
```

## Goal

Create a CSV of unique NCBI bacterial organism names that do not appear in the Evo2 trained bacteria file.

## Input Files

### 1. NCBI Bacterial Names

```text
Results/Bacteria/ncbi_bacteria_unique_names.csv
```

This file contains unique NCBI organism names from rows where:

```text
group = bacteria
```

### 2. Evo2 Trained Bacteria

```text
~/Downloads/evo2_trained_bacteria.txt
```

The script reads the `Species_Name` column from this tab-delimited file.

## Comparison Logic

The script normalizes names by trimming whitespace, collapsing repeated spaces, and comparing case-insensitively.

For each NCBI bacterial organism name, the script writes it to the output if the normalized name is not found in the Evo2 trained bacteria `Species_Name` set.

## Output File

```text
Results/Bacteria/bacteria_names_not_trained_by_evo2.csv
```

Columns:

```csv
organism_name
```
