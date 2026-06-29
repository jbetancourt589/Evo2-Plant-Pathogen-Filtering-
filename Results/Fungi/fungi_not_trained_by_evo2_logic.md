# Logic for `fungi_not_trained_by_evo2.csv`

## Goal

Create a file of GenBank fungal assemblies that do not appear to be in the Evo2 fungi set.

## Script

The script used is:

```text
Scripts/create_fungi_not_trained_by_evo2.py
```

Run it from the repository root:

```powershell
.\.venv\Scripts\python.exe Scripts\create_fungi_not_trained_by_evo2.py
```

## Input Files

### 1. Full GenBank Fungi Set

```text
Results/Genus List & GenBank/all_genbank_fungi_and_assemblyIDs.csv
```

This file was created from `all_eukaryotes_and_assembly_genbank.txt` using only rows where:

```text
group = fungi
```

It excludes organism names containing:

```text
virus
viroid
```

It has:

```csv
organism_name,assembly_id
```

### 2. Evo2 Fungi Set

```text
Results/Genus List & GenBank/evo2_trained_fungi.csv
```

This file contains Evo2 entries classified as fungi by matching against GenBank assembly metadata.

## Comparison Logic

For each row in `all_genbank_fungi_and_assemblyIDs.csv`, the script checks whether that fungal assembly appears in the Evo2 fungi set.

The script excludes a fungal row from the output if any of these are true:

### 1. Exact Assembly ID Match

The GenBank fungal `assembly_id` exactly appears in `evo2_trained_fungi.csv`.

Example:

```text
GCA_000359685.2 == GCA_000359685.2
```

### 2. Versionless Assembly ID Match

If exact matching fails, the script compares the accession without the version suffix.

Example:

```text
GCA_000733025.2 -> GCA_000733025
GCA_000733025.3 -> GCA_000733025
```

This catches related assembly versions.

The script does not use organism-name matching for this output. A shared
organism name does not prove that a specific GenBank assembly was used by Evo2,
because one organism can have many GenBank assemblies.

## Output File

The generated output is:

```text
Results/Genus List & GenBank/fungi_not_trained_by_evo2.csv
```

Columns:

```csv
organism_name,assembly_id,not_trained_reason
```

Rows in this file are GenBank fungal assemblies that were not found in the Evo2 fungi set by exact assembly ID or versionless assembly ID.

## Current Run Summary

```text
Total GenBank fungal assembly rows checked: 21,524
Skipped exact Evo2 assembly matches: 4,284
Skipped versionless Evo2 assembly matches: 25
Rows written as not trained by Evo2: 17,215
```
