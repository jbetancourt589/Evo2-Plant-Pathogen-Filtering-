# Logic for `ncbi_bacteria_unique_names.csv`

## Script

```text
Scripts/extract_ncbi_bacteria_names.py
```

## Goal

Create a deduplicated list of bacterial organism names from the NCBI database file.

## Input File

```text
Datasets/NCBI Database/NCBI_database.txt
```

## Filtering Logic

The script reads the NCBI assembly summary and keeps only rows where:

```text
group = bacteria
```

It collects the `organism_name` value from each bacterial row, deduplicates the names, and sorts them alphabetically.

## Output File

```text
Results/Bacteria/ncbi_bacteria_unique_names.csv
```

Columns:

```csv
organism_name
```
