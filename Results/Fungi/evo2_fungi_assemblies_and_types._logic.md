# Logic for `fungal_y_assemblies_with_types.csv`

## Input Files

The output file was made from two inputs:

1. `C:\Users\rfito\Downloads\fungal_list_final.txt`

   This file contains fungal organism names, whether each organism appears in the Evo2 organism file, and one or more matching genome assembly IDs.

2. `Datasets/Genus List & GenBank/all_eukaryotes_and_assembly_genbank.txt`

   This is the NCBI GenBank assembly summary file. The assembly type comes from this file.

## Output File

The generated output is:

```text
Results/Genus List & GenBank/fungal_y_assemblies_with_types.csv
```

It has these columns:

```csv
organism_name,assembly_id,assembly_type
```

## Filtering Logic

The script reads `fungal_list_final.txt` and keeps only rows where the Evo2 match column is `Y`.

Rows marked `N` are skipped.

Example kept row:

```text
Alternaria alternata    Fungi    Y    GCF_001642055.1
```

Example skipped row:

```text
Alternaria citri    Fungi    N
```

## Assembly ID Logic

For every kept `Y` row, the script extracts all assembly IDs that match this pattern:

```text
GCA_#########.#
GCF_#########.#
```

If one fungal organism has multiple assembly IDs separated by semicolons, each assembly ID gets its own output row.

Example:

```text
Alternaria spp.    Fungi    Y    GCA_001950455.1;GCA_002796735.1
```

Becomes:

```csv
Alternaria spp.,GCA_001950455.1,Scaffold
Alternaria spp.,GCA_002796735.1,Contig
```

## Where Assembly Types Came From

The assembly types came from the `assembly_level` column in:

```text
Datasets/Genus List & GenBank/all_eukaryotes_and_assembly_genbank.txt
```

Examples of assembly levels in that file:

```text
Contig
Scaffold
Chromosome
Complete Genome
```

The script matches each assembly ID from `fungal_list_final.txt` to the GenBank summary using:

1. `assembly_accession`

   Usually a `GCA_...` accession.

2. `gbrs_paired_asm`

   The paired RefSeq accession, often a `GCF_...` accession.

This is needed because some IDs in `fungal_list_final.txt` are `GCF_...`, while the main GenBank accession column is often `GCA_...`.

Example:

```text
assembly_accession = GCA_001642055.1
gbrs_paired_asm    = GCF_001642055.1
assembly_level     = Scaffold
```

So this input:

```text
GCF_001642055.1
```

Gets this output:

```csv
Alternaria alternata,GCF_001642055.1,Scaffold
```

## Versionless Fallback Logic

If the exact assembly version is not found, the script tries matching without the version suffix.

Example:

```text
fungal_list_final.txt has:        GCA_000733025.2
all_eukaryotes_and_assembly_genbank.txt has: GCA_000733025.3
```

The script strips the `.2` and `.3`, compares `GCA_000733025`, and uses the available GenBank assembly level.

## Missing Assembly Types

If an assembly ID cannot be found in `all_eukaryotes_and_assembly_genbank.txt`, even with versionless matching, the script writes:

```text
N/A
```

## Script Used

The reproducible script is:

```text
Scripts/create_fungal_y_assemblies_with_types.py
```

Run it from the repository root with:

```powershell
.\.venv\Scripts\python.exe Scripts\create_fungal_y_assemblies_with_types.py
```
