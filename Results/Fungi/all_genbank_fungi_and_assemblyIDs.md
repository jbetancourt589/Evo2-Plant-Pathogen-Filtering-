# Logic for `all_genbank_fungi_and_assemblyIDs.csv`

## Script

```text
Scripts/match_names_by_genus.py
```

## Goal

Create a complete list of GenBank fungal organism names with their assembly IDs, excluding viruses and viroids.

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

## Assembly ID Source

Assembly IDs come from the GenBank assembly summary column:

```text
assembly_accession
```

## Output File

```text
Results/Genus List & GenBank/all_genbank_fungi_and_assemblyIDs.csv
```

Columns:

```csv
organism_name,assembly_id
```

The output is deduplicated and sorted by organism name and assembly ID.
