# Logic for `genbank_fungi_names_by_genus.csv`

## Script

```text
Scripts/match_names_by_genus.py
```

## Goal

Create a file listing every genus from the genus-list input and the GenBank fungal organism names that match that genus.

## Input Files

```text
Datasets/Genus List & GenBank/fungal_genus_only_no_duplicates.txt
Datasets/Genus List & GenBank/all_eukaryotes_and_assembly_genbank.txt
```

## Filtering Logic

The script reads `all_eukaryotes_and_assembly_genbank.txt` and keeps only rows where:

```text
group = fungi
```

It excludes fungal rows if the organism name contains either of these words, case-insensitive:

```text
virus
viroid
```

## Genus Matching Logic

The script extracts the genus from each GenBank `organism_name`.

For normal organism names, it uses the first word:

```text
Fusarium oxysporum -> Fusarium
```

For names beginning with `Candidatus`, it uses the second word:

```text
Candidatus Liberibacter asiaticus -> Liberibacter
```

The extracted genus is matched against the genus list after normalizing capitalization.

## Output File

```text
Results/Genus List & GenBank/genbank_fungi_names_by_genus.csv
```

Columns:

```csv
genus,organism_name,assembly_id
```

Each matching organism gets one row. If a genus from the input list has no matching GenBank fungal organism, the genus is still written with blank `organism_name` and `assembly_id` fields.
