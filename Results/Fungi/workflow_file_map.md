# Workflow File Map

This file maps each reproducible script to the output file it creates and the matching logic file.

## GenBank Fungal Organism Outputs

Script:

```text
Scripts/match_names_by_genus.py
```

What it does: reads the fungal genus list and GenBank assembly summary, keeps GenBank rows where `group = fungi`, excludes organism names containing `virus` or `viroid`, and writes fungal organism outputs.

| Output file | Logic file | Purpose |
|---|---|---|
| `Results/Genus List & GenBank/genbank_fungi_names_by_genus.csv` | `Results/Genus List & GenBank/genbank_fungi_names_by_genus.md` | Fungal genus-list matches with organism names and assembly IDs. |
| `Results/Genus List & GenBank/genbank_fungi_unique_names.csv` | `Results/Genus List & GenBank/genbank_fungi_unique_names.md` | All unique GenBank fungal organism names, excluding viruses and viroids. |
| `Results/Genus List & GenBank/all_genbank_fungi_and_assemblyIDs.csv` | `Results/Genus List & GenBank/all_genbank_fungi_and_assemblyIDs.md` | All GenBank fungal organism names with assembly IDs, excluding viruses and viroids. |

## Evo2 Fungi Classification

Script:

```text
Scripts/create_evo2_trained_fungi.py
```

What it does: identifies which organisms in the Evo2 organism file are fungi by matching against GenBank assembly metadata.

| Output file | Logic file |
|---|---|
| `Results/Genus List & GenBank/evo2_trained_fungi.csv` | `Results/Genus List & GenBank/evo2_trained_fungi_logic.md` |

## Fungal Y Assemblies With Types

Script:

```text
Scripts/create_fungal_y_assemblies_with_types.py
```

What it does: takes fungi marked `Y` in `fungal_list_final.txt`, extracts every assembly ID, and adds the corresponding GenBank assembly type.

| Output file | Logic file |
|---|---|
| `Results/Genus List & GenBank/fungal_y_assemblies_with_types.csv` | `Results/Genus List & GenBank/fungal_y_assemblies_with_types_logic.md` |

## Fungi Not Trained By Evo2

Script:

```text
Scripts/create_fungi_not_trained_by_evo2.py
```

What it does: compares the full GenBank fungi assembly list against the Evo2 fungi output by assembly ID and writes fungi that do not appear to be in Evo2.

| Output file | Logic file |
|---|---|
| `Results/Genus List & GenBank/fungi_not_trained_by_evo2.csv` | `Results/Genus List & GenBank/fungi_not_trained_by_evo2_logic.md` |
