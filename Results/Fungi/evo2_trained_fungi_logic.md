# Logic for `evo2_trained_fungi.csv`

## Goal

Given an Evo2 organism file, identify which entries are fungi.

The script for this is:

```text
Scripts/create_evo2_trained_fungi.py
```

## Default Input

By default, the script reads:

```text
Datasets/Plant Pathogen Preprocessing/evo2_eukaryotic_dataset.txt
```

You can use a different Evo2 file with:

```powershell
.\.venv\Scripts\python.exe Scripts\create_evo2_trained_fungi.py --evo2-file path\to\evo2_file.txt
```

## Cross-Examined Source

The main reference source is:

```text
Datasets/Genus List & GenBank/all_eukaryotes_and_assembly_genbank.txt
```

The script uses these columns:

```text
assembly_accession
gbrs_paired_asm
organism_name
group
assembly_level
```

The key classification field is:

```text
group
```

If `group` is `fungi`, the Evo2 entry is classified as fungi.

## Matching Priority

### 1. Exact Assembly ID Match

The script first tries to match the Evo2 assembly ID exactly against:

```text
assembly_accession
gbrs_paired_asm
```

This catches both GenBank and RefSeq IDs:

```text
GCA_...
GCF_...
```

If the matched GenBank row has:

```text
group = fungi
```

then the Evo2 entry is fungi.

### 2. Versionless Assembly ID Match

If no exact match is found, the script tries matching without the version suffix.

Example:

```text
GCA_000733025.2 -> GCA_000733025
GCA_000733025.3 -> GCA_000733025
```

This is only used when that base accession maps unambiguously to one GenBank summary row.

### 3. Exact Organism Name Fallback

If assembly ID matching fails, the script optionally checks the organism name against:

```text
Results/Genus List & GenBank/genbank_fungi_unique_names.csv
```

That file was generated from `all_eukaryotes_and_assembly_genbank.txt` where:

```text
group = fungi
```

This is weaker than assembly-ID matching, but useful when an Evo2 row has a name and no assembly ID match.

## Output

Default output:

```text
Results/Genus List & GenBank/evo2_trained_fungi.csv
```

Columns:

```csv
assembly_id,organism_name,is_fungi,match_method,genbank_group,assembly_level,genbank_assembly_accession,refseq_paired_assembly,genbank_organism_name
```

By default, only fungi rows are written.

To write every Evo2 row with `is_fungi` as `Y` or `N`, use:

```powershell
.\.venv\Scripts\python.exe Scripts\create_evo2_trained_fungi.py --all-rows
```

## Match Methods

The `match_method` column can be:

```text
assembly_exact
assembly_versionless
name_exact
not_matched
```

`assembly_exact` is the strongest evidence.

`assembly_versionless` means the accession matched only after removing the version suffix, such as `.1` or `.2`.

`name_exact` means the organism name matched the known fungal organism name list.

`not_matched` appears only when using `--all-rows`.
