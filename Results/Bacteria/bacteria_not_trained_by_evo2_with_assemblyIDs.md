# Logic for `bacteria_not_trained_by_evo2_with_assemblyIDs.txt`

## Script

```text
Scripts/Bacteria/create_bacteria_not_trained_by_evo2_with_assemblyIDs.py
```

## Goal

Create a tab-delimited TXT file of NCBI bacterial assemblies that do not appear in the Evo2 trained bacteria file.

## Input Files

### 1. All NCBI Bacterial Assemblies

```text
Results/Bacteria/all_ncbi_bacteria_and_assemblyIDs.txt
```

This file contains bacterial organism names and assembly IDs from NCBI rows where:

```text
group = bacteria
```

### 2. Evo2 Trained Bacteria

```text
~/Downloads/evo2_trained_bacteria.txt
```

The script reads the `Assembly_ID` column from this tab-delimited file.

## Comparison Logic

For each NCBI bacterial assembly row, the script checks whether the assembly appears in the Evo2 trained bacteria set.

The script excludes an NCBI row from the output if either condition is true:

### 1. Exact Assembly ID Match

The NCBI bacterial `assembly_id` exactly appears in `evo2_trained_bacteria.txt`.

Example:

```text
GCA_000003135.1 == GCA_000003135.1
```

### 2. Versionless Assembly ID Match

If exact matching fails, the script compares accessions without the version suffix.

Example:

```text
GCA_000733025.2 -> GCA_000733025
GCA_000733025.3 -> GCA_000733025
```

The script does not use organism-name matching for this output. A shared organism name does not prove that a specific NCBI assembly was used by Evo2.

## Output File

```text
Results/Bacteria/bacteria_not_trained_by_evo2_with_assemblyIDs.txt
```

Columns:

```text
organism_name	assembly_id	not_trained_reason
```
