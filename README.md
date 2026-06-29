# Plant Pathogen Evo2 Data Filtering

This project compares plant-pathogen and NCBI assembly datasets against Evo2/OpenGenome training data. It includes scripts for plant-pathogen preprocessing, bacteria, fungi, protists, and Evo2 FASTA filtering reproduction checks.

## Important Data Note

The full local NCBI assembly-summary database is required for some scripts, but it is not committed to GitHub because it is too large.

Expected local path:

```text
Datasets/NCBI Database/NCBI_database.txt
```

Scripts that use this file read it as an NCBI `assembly_summary` table and use columns such as `assembly_accession`, `gbrs_paired_asm`, `organism_name`, and `group`.

Large non-NCBI files that still need to stay in the repository are tracked with Git LFS.

## Main Folders

```text
Datasets/
Results/
Scripts/
```

`Scripts/` contains the code. `Results/` contains generated outputs that are small enough to keep in the repo, plus a few larger files tracked with Git LFS. The largest raw source file, `Datasets/NCBI Database/NCBI_database.txt`, stays local only.

## Protists

Scripts:

- `Scripts/Protists/ncbi_protists.py`
- `Scripts/Protists/evo2_trained_protists.py`

Inputs:

- `Datasets/NCBI Database/NCBI_database.txt`
- `Datasets/Plant Pathogen Preprocessing & Evo2/evo2_eukaryotes_alphabetical.txt`

Outputs:

- `Results/Protists/ncbi_protist_names.csv`
- `Results/Protists/ncbi_protists_names_and_assemblies.csv`
- `Results/Protists/evo2_protists_names_and_assemblies.csv`

The NCBI protist scripts use NCBI's `protozoa` group as the protist group. The Evo2 protist script starts from the Evo2 eukaryote training list, then uses the NCBI database to identify which Evo2 assemblies are protists.

Run:

```powershell
uv run python Scripts/Protists/ncbi_protists.py
uv run python Scripts/Protists/evo2_trained_protists.py
```

## Bacteria

Scripts:

- `Scripts/Bacteria/extract_ncbi_bacteria_names.py`
- `Scripts/Bacteria/extract_ncbi_bacteria_and_assemblyIDs.py`
- `Scripts/Bacteria/bacteria_names_not_trained_by_evo2.py`
- `Scripts/Bacteria/bacteria_not_trained_by_evo2_with_assemblyIDs.py`
- `Scripts/Bacteria/plant_pathogen_genus_species_not_trained_by_evo2.py`

Key outputs:

- `Results/Bacteria/ncbi_bacteria_unique_names.csv`
- `Results/Bacteria/all_ncbi_bacteria_and_assemblyIDs.txt`
- `Results/Bacteria/bacteria_names_not_trained_by_evo2.csv`
- `Results/Bacteria/bacteria_not_trained_by_evo2_with_assemblyIDs.txt`
- `Results/Bacteria/plant_pathogen_genus_species_not_trained_by_evo2.csv`

These scripts extract bacteria from the NCBI database and compare bacterial names or assembly IDs against Evo2 trained bacteria data.

## Fungi

Scripts:

- `Scripts/Fungi/match_names_by_genus.py`
- `Scripts/Fungi/evo2_trained_fungi.py`
- `Scripts/Fungi/fungi_not_trained_by_evo2.py`
- `Scripts/Fungi/evo2_fungi_assemblies_and_types..py`

Key outputs:

- `Results/Fungi/genbank_fungi_names_by_genus.csv`
- `Results/Fungi/genbank_fungi_unique_names.csv`
- `Results/Fungi/all_genbank_fungi_and_assemblyIDs.csv`
- `Results/Fungi/evo2_trained_fungi.csv`
- `Results/Fungi/fungi_not_trained_by_evo2.csv`
- `Results/Fungi/evo2_fungi_assemblies_and_types.csv`

The fungi workflow uses the GenBank eukaryote assembly summary and fungal genus/name files to identify fungal assemblies, then compares those assemblies against Evo2 training data.

## Plant Pathogen Evo2 Comparison

Script:

- `Scripts/compare_plant_pathogens_to_evo2.py`

Inputs:

- UC IPM disease list
- `Datasets/Plant Pathogen Preprocessing & Evo2/combined_plant_pathogen_list.txt`
- `Datasets/Plant Pathogen Preprocessing & Evo2/evo2_eukaryotic_dataset.txt`
- `Datasets/Plant Pathogen Preprocessing & Evo2/evo2_full_training_dataset.txt`

Outputs:

- `Results/Plant Pathogen Preprocessing Results/plant_pathogens_vs._eukaryotes_evo2`
- `Results/Plant Pathogen Preprocessing Results/plant_pathogen_vs._entire_evo2`

Run:

```powershell
uv run python Scripts/compare_plant_pathogens_to_evo2.py
```

## Evo2/OpenGenome Reproduction Checks

Scripts:

- `Scripts/Data Reproductions/compare_evo2_outputs_1.py`
- `Scripts/Data Reproductions/compare_evo2_outputs_2.py`
- `Scripts/Data Reproductions/compare_evo2_outputs_3.py`
- `Scripts/Data Reproductions/compare_evo2_outputs_gtf.py`

These scripts recreate OpenGenome/Evo2-style FASTA filtering from original NCBI FASTA files and compare the recreated output to official OpenGenome/Evo2 outputs. The recreated FASTA keeps only continuous `A/C/G/T` chunks at least 10,000 bp long.

The GTF script can also remove conservative centromere-region annotations before running the same strict sequence filtering.

Outputs are written under:

```text
Results/Evo2 Data Reproductions/
```

## Python

This repo uses a minimal Python project setup. From the project root, prefer:

```powershell
uv run python path/to/script.py
```

If the virtual environment is already active, direct Python execution also works:

```powershell
python path/to/script.py
```
