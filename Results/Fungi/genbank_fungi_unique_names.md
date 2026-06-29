# Logic for `genbank_fungi_unique_names.csv`

## Script

```text
Scripts/match_names_by_genus.py
```

## Goal

Create a complete list of unique GenBank fungal organism names, excluding viruses and viroids.

## Input File

```text
Datasets/Genus List & GenBank/all_eukaryotes_and_assembly_genbank.txt
```

## Filtering Logic

The script reads the GenBank assembly summary and keeps only rows where:

```text
group = fungi
```

It excludes organism names containing either of these words, case-insensitive:

```text
virus
viroid
```

## Output File

```text
Results/Genus List & GenBank/genbank_fungi_unique_names.csv
```

Columns:

```csv
organism_name
```

The output is deduplicated and sorted alphabetically.
