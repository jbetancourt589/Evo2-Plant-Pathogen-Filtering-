# Logic for `all_ncbi_bacteria_and_assemblyIDs.csv`

## Script

```text
Scripts/extract_ncbi_bacteria.py
```

## Goal

Create a complete list of NCBI bacterial organism names with their GenBank assembly IDs.

## Input File

```text
Datasets/NCBI Database/NCBI_database.txt
```

## Filtering Logic

The script reads the NCBI assembly summary and keeps only rows where:

```text
group = bacteria
```

## Assembly ID Source

Assembly IDs come from the NCBI assembly summary column:

```text
assembly_accession
```

## Output File

```text
Results/Bacteria/all_ncbi_bacteria_and_assemblyIDs.txt
```

Columns:

```csv
organism_name,assembly_id
```

The TXT file is tab-delimited.

The output is deduplicated by organism name and assembly ID.
