# Logic for `plant_pathogen_genus_species_not_trained_by_evo2.csv`

## Script

```text
Scripts/Bacteria/create_plant_pathogen_genus_species_not_trained_by_evo2.py
```

## Goal

Find every NCBI bacterial species in the known plant-pathogen genera for which Evo2 has no matching trained assembly.

The result is based on genus membership. Some species in these genera may not be plant pathogens.

## Input Files

```text
Datasets/Bacterial Plant Pathogens/bacteria_plant_pathogen_genus.txt
Datasets/NCBI Database/NCBI_database.txt
~/Downloads/evo2_trained_bacteria.txt
```

## Matching Logic

1. Read the first tab-delimited column from `bacteria_plant_pathogen_genus.txt`.
2. Extract and deduplicate the genus names.
3. Normalize the `Xanthamonas` spelling in the input to `Xanthomonas`.
4. Read the Evo2 trained bacterial assembly IDs and species names.
5. Keep plant-pathogen genera represented in the Evo2 trained bacteria file.
6. Stream `NCBI_database.txt` and keep rows where `group = bacteria`.
7. Keep NCBI rows whose organism genus is one of the selected plant-pathogen genera.
8. Reduce each organism name to `Genus species`. For names beginning with `Candidatus`, omit that qualifier from the output name.
9. Compare both the NCBI `assembly_accession` and paired `gbrs_paired_asm` against Evo2 assembly IDs.
10. Match assembly IDs exactly and without their version suffix.
11. Exclude a species if Evo2 contains at least one matching assembly for that species.
12. For each remaining species, combine all correlated NCBI assembly IDs into one semicolon-delimited value.

## Output Columns

```text
species_name
assembly_ids
```

- `species_name`: Genus and species name.
- `assembly_ids`: All correlated NCBI assembly accessions separated by semicolons.

## Current Result

- Plant-pathogen genera loaded: 11
- Plant-pathogen genera searched: 11
- NCBI rows checked: 3,562,018
- NCBI bacterial rows checked: 3,156,788
- Candidate assembly rows in the selected genera: 79,894
- Candidate assembly rows found in Evo2 training: 1,143
- Species with no Evo2-trained assembly: 206
