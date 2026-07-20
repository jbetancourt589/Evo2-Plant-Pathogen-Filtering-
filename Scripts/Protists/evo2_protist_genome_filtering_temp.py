#!/usr/bin/env python3
"""
Temporary copy for filtering a test list of Evo2-trained protist assemblies.

Logic:
1. Read test assembly IDs, with --limit available for smaller test runs.
2. Download each assembly's NCBI genomic FASTA into a local cache.
3. If an NCBI GTF/GFF annotation file exists, remove true centromere-region intervals.
4. Write one combined FASTA containing only A/C/G/T chunks at least 10,000 bp long.

GTF/GFF lookup:
- The script uses each assembly's NCBI ftp_path to build expected companion
  annotation URLs ending in _genomic.gtf.gz and _genomic.gff.gz.
- Genome FASTA files are cached in Datasets/Protists/Protist Genomes NCBI/.
- Annotation files are cached separately in Datasets/Protists/Protist Annotations NCBI/.
- If no NCBI annotation file exists for an assembly, annotation filtering is skipped.

Inputs:
- Datasets/Protists/list_of_50_test_protist_genomes_opengenom2.txt
- Datasets/NCBI Database/NCBI_database.txt
- Datasets/Protists/Protist Genomes NCBI/ cached or downloaded genome FASTA files
- Datasets/Protists/Protist Annotations NCBI/ cached or downloaded GTF/GFF files when available

Outputs:
- Results/Protists/evo2_protist_genome_filtered_temp.fasta
- Results/Protists/evo2_protist_genome_filtered_summary_temp.csv
"""

import argparse
import csv
import gzip
import re
import subprocess
import textwrap
import urllib.request
from urllib.error import HTTPError
from urllib.error import URLError
from collections import Counter
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Iterator, TextIO


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRAINED_PROTISTS = PROJECT_ROOT / "Datasets" / "Protists" / "list_of_50_test_protist_genomes_opengenom2.txt"
DEFAULT_NCBI_DATABASE = PROJECT_ROOT / "Datasets" / "NCBI Database" / "NCBI_database.txt"
DEFAULT_CACHE_DIR = PROJECT_ROOT / "Datasets" / "Protists" / "Protist Genomes NCBI"
DEFAULT_ANNOTATION_CACHE_DIR = PROJECT_ROOT / "Datasets" / "Protists" / "Protist Annotations NCBI"
DEFAULT_OUTPUT = PROJECT_ROOT / "Results" / "Protists" / "evo2_protist_genome_filtered_temp.fasta"
DEFAULT_SUMMARY_OUTPUT = PROJECT_ROOT / "Results" / "Protists" / "evo2_protist_genome_filtered_summary_temp.csv"
DEFAULT_LIMIT = 0
MIN_CHUNK_LENGTH = 10_000
ACGT_RUN_RE = re.compile(r"[ACGTacgt]+")
GENE_LIKE_FEATURES = {
    "gene",
    "transcript",
    "mrna",
    "exon",
    "cds",
    "start_codon",
    "stop_codon",
    "five_prime_utr",
    "three_prime_utr",
    "utr",
}


@dataclass(frozen=True)
class TargetAssembly:
    """One Evo2-trained protist assembly selected for filtering."""

    organism_name: str
    assembly_id: str


@dataclass(frozen=True)
class NcbiAssembly:
    """NCBI metadata needed to download one assembly FASTA."""

    assembly_id: str
    paired_assembly_id: str
    organism_name: str
    ftp_path: str


@dataclass
class FilterStats:
    """Filtering counts for one assembly."""

    organism_name: str
    assembly_id: str
    source_url: str
    cached_fasta_gz: str
    cached_fasta_gz_size_bytes: int = 0
    input_records: int = 0
    input_bp: int = 0
    non_acgt_bp_removed: int = 0
    short_acgt_bp_removed: int = 0
    kept_chunks: int = 0
    kept_bp: int = 0
    filtered_fasta_size_bytes: int = 0
    removed_base_counts: Counter[str] = field(default_factory=Counter)
    annotation_path: str = ""
    annotation_records: int = 0
    centromere_regions_removed: int = 0
    centromere_bp_removed: int = 0


@dataclass
class AnnotationResult:
    """Centromere-region intervals parsed from a GTF/GFF annotation file."""

    path: Path
    intervals_by_seqid: dict[str, list[tuple[int, int]]]
    total_records: int
    true_centromere_regions: int
    total_centromere_bp_removed: int


def accession_base(assembly_id: str) -> str:
    """Return accession without version suffix."""
    return assembly_id.rsplit(".", 1)[0]


def read_assembly_summary_rows(path: Path) -> Iterator[dict[str, str]]:
    """Yield rows from an NCBI assembly_summary-style tab-delimited file."""
    header = None

    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        for line in file:
            line = line.rstrip("\n").lstrip("\ufeff")
            if not line:
                continue

            if line.startswith("#assembly_accession"):
                header = line.lstrip("#").split("\t")
                continue

            if line.startswith("#"):
                continue

            if header is None:
                raise ValueError("Could not find header line beginning with #assembly_accession")

            values = line.split("\t")
            if len(values) < len(header):
                values += [""] * (len(header) - len(values))

            yield dict(zip(header, values))


def read_target_assemblies(path: Path, limit: int) -> list[TargetAssembly]:
    """Read target assemblies from a CSV or a plain assembly-ID list."""
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        first_line = file.readline()

    if "," not in first_line and "\t" not in first_line:
        return read_target_assembly_ids(path, limit)

    targets = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            organism_name = row.get("organism_name", "").strip()
            assembly_id = row.get("assembly_id", "").strip()
            if not organism_name or not assembly_id:
                continue

            targets.append(TargetAssembly(organism_name=organism_name, assembly_id=assembly_id))
            if limit > 0 and len(targets) >= limit:
                break

    return targets


def read_target_assembly_ids(path: Path, limit: int) -> list[TargetAssembly]:
    """Read target assemblies from a plain one-assembly-ID-per-line file."""
    targets = []

    with path.open("r", encoding="utf-8", errors="replace") as file:
        for raw_line in file:
            assembly_id = raw_line.strip()
            if not assembly_id or assembly_id.startswith("#"):
                continue

            targets.append(TargetAssembly(organism_name=assembly_id, assembly_id=assembly_id))
            if limit > 0 and len(targets) >= limit:
                break

    return targets


def load_ncbi_metadata(path: Path, targets: list[TargetAssembly]) -> dict[str, NcbiAssembly]:
    """Load NCBI rows matching the selected target assembly IDs."""
    target_by_exact_id = {target.assembly_id: target for target in targets}
    target_by_base_id = {accession_base(target.assembly_id): target for target in targets}
    metadata_by_target_id = {}

    for row in read_assembly_summary_rows(path):
        assembly_id = row.get("assembly_accession", "").strip()
        paired_assembly_id = row.get("gbrs_paired_asm", "").strip()
        ftp_path = row.get("ftp_path", "").strip()
        if not ftp_path or ftp_path.casefold() == "na":
            continue

        matched_target_ids = []
        for candidate_id in [assembly_id, paired_assembly_id]:
            if not candidate_id or candidate_id.casefold() == "na":
                continue

            if candidate_id in target_by_exact_id:
                matched_target_ids.append(candidate_id)

            candidate_base_id = accession_base(candidate_id)
            if candidate_base_id in target_by_base_id:
                matched_target_ids.append(target_by_base_id[candidate_base_id].assembly_id)

        if not matched_target_ids:
            continue

        organism_name = row.get("organism_name", "").strip()
        metadata = NcbiAssembly(
            assembly_id=assembly_id,
            paired_assembly_id=paired_assembly_id,
            organism_name=organism_name,
            ftp_path=ftp_path,
        )
        for target_id in matched_target_ids:
            metadata_by_target_id.setdefault(target_id, metadata)

        if len(metadata_by_target_id) == len(targets):
            break

    return metadata_by_target_id


def genomic_fasta_url(ftp_path: str) -> str:
    """Build the NCBI genomic FASTA URL from an assembly FTP path."""
    clean_path = ftp_path.rstrip("/")
    assembly_dir_name = clean_path.rsplit("/", 1)[-1]
    return f"{clean_path}/{assembly_dir_name}_genomic.fna.gz"


def genomic_annotation_urls(ftp_path: str) -> list[str]:
    """Build candidate NCBI annotation URLs from an assembly FTP path."""
    clean_path = ftp_path.rstrip("/")
    assembly_dir_name = clean_path.rsplit("/", 1)[-1]
    return [
        f"{clean_path}/{assembly_dir_name}_genomic.gtf.gz",
        f"{clean_path}/{assembly_dir_name}_genomic.gff.gz",
    ]


def safe_header_text(value: str) -> str:
    """Make text compact enough to use safely inside a FASTA header."""
    return re.sub(r"\s+", "_", value.strip())


def cache_path_for(cache_dir: Path, assembly_id: str, url: str) -> Path:
    """Return a local cache path for one downloaded NCBI file."""
    file_name = url.rsplit("/", 1)[-1]
    return cache_dir / f"{assembly_id}_{file_name}"


def download_with_curl(url: str, output_path: Path) -> bool:
    """Download with curl.exe when available; return False if curl is unavailable."""
    curl_cmd = [
        "curl.exe",
        "-L",
        "--fail",
        "--silent",
        "--show-error",
        "--retry",
        "3",
        "--retry-delay",
        "5",
        "--connect-timeout",
        "60",
        "--max-time",
        "900",
        "-o",
        str(output_path),
        url,
    ]
    try:
        subprocess.run(curl_cmd, check=True)
    except FileNotFoundError:
        return False
    return True


def download_with_urllib(url: str, output_path: Path) -> None:
    """Download a file with urllib as a fallback when curl is unavailable."""
    request = urllib.request.Request(url, headers={"User-Agent": "plant-pathogen-genome-filtering/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        with output_path.open("wb") as output_file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output_file.write(chunk)


def download_if_needed(url: str, output_path: Path) -> None:
    """Download one genome FASTA if it is not already cached."""
    if output_path.exists() and output_path.stat().st_size > 0:
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = output_path.with_suffix(output_path.suffix + ".part")
    if partial_path.exists():
        partial_path.unlink()

    if not download_with_curl(url, partial_path):
        download_with_urllib(url, partial_path)

    partial_path.replace(output_path)


def try_download_if_needed(url: str, output_path: Path) -> bool:
    """Download a file when it exists; return False for missing/unreachable optional files."""
    if output_path.exists() and output_path.stat().st_size > 0:
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = output_path.with_suffix(output_path.suffix + ".part")
    if partial_path.exists():
        partial_path.unlink()

    try:
        download_with_urllib(url, partial_path)
    except (HTTPError, URLError, TimeoutError):
        if partial_path.exists():
            partial_path.unlink()
        return False

    partial_path.replace(output_path)
    return output_path.exists() and output_path.stat().st_size > 0


def download_annotation_if_available(
    ftp_path: str,
    cache_dir: Path,
    assembly_id: str,
) -> Path | None:
    """Download the first available NCBI GTF/GFF annotation file for one assembly."""
    for url in genomic_annotation_urls(ftp_path):
        annotation_path = cache_path_for(cache_dir, assembly_id, url)
        if try_download_if_needed(url, annotation_path):
            return annotation_path

    return None


def open_text_maybe_gzip(path: Path):
    """Open plain text or gzip-compressed text."""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")

    return path.open("r", encoding="utf-8", errors="replace")


def parse_annotation_file(path: Path) -> AnnotationResult:
    """Parse a GTF/GFF file and collect conservative centromere intervals."""
    selected_intervals: dict[str, list[tuple[int, int]]] = {}
    total_records = 0
    true_centromere_regions = 0

    with open_text_maybe_gzip(path) as annotation_file:
        for line_number, raw_line in enumerate(annotation_file, start=1):
            line = raw_line.rstrip("\n")
            if not line or line.startswith("#"):
                continue

            total_records += 1
            columns = line.split("\t")
            if len(columns) < 9:
                continue

            seqid, _, feature, start_text, end_text = columns[:5]
            attributes = columns[8]

            try:
                start = int(start_text)
                end = int(end_text)
            except ValueError:
                continue

            selected, _ = is_true_centromere_region(feature, attributes)
            if selected:
                start_index = start - 1
                end_index = end
                if end_index > start_index:
                    selected_intervals.setdefault(seqid, []).append((start_index, end_index))
                    true_centromere_regions += 1

    merged_intervals = merge_intervals(selected_intervals)
    total_bp_removed = sum(
        end - start
        for intervals in merged_intervals.values()
        for start, end in intervals
    )

    return AnnotationResult(
        path=path,
        intervals_by_seqid=merged_intervals,
        total_records=total_records,
        true_centromere_regions=true_centromere_regions,
        total_centromere_bp_removed=total_bp_removed,
    )


def is_true_centromere_region(feature: str, attributes: str) -> tuple[bool, str]:
    """Return whether an annotation row marks the region itself as centromere."""
    feature_lower = feature.strip().lower()
    if feature_lower == "centromere":
        return True, 'feature type is exactly "centromere"'

    if feature_lower in GENE_LIKE_FEATURES:
        return False, "gene/protein feature type is not a centromere region"

    attributes_by_key = parse_attributes(attributes)
    for key, values in attributes_by_key.items():
        key_lower = key.lower()
        if key_lower in {"product", "gene", "gene_id", "transcript_id", "protein_id", "locus_tag"}:
            continue

        for value in values:
            value_lower = value.lower()
            if value_lower in {"centromere", "centromere region", "centromeric region"}:
                return True, f'attribute {key} marks a centromere region'
            if re.search(r"\bcentromeric\s+region\b", value_lower):
                return True, f'attribute {key} marks a centromeric region'
            if re.search(r"\bcentromere\s+region\b", value_lower):
                return True, f'attribute {key} marks a centromere region'
            if key_lower in {"gbkey", "rpt_type", "region_name"} and re.search(r"\bcentromere\b", value_lower):
                return True, f'attribute {key} marks a centromere region'

    return False, "not a true centromere-region annotation"


def parse_attributes(attributes: str) -> dict[str, list[str]]:
    """Parse simple GTF key \"value\" and GFF key=value attributes."""
    parsed: dict[str, list[str]] = {}
    for item in attributes.strip().strip(";").split(";"):
        item = item.strip()
        if not item:
            continue

        if "=" in item:
            key, value = item.split("=", 1)
        else:
            parts = item.split(None, 1)
            if len(parts) != 2:
                continue
            key, value = parts

        key = key.strip()
        value = value.strip().strip('"')
        parsed.setdefault(key, []).append(value)

    return parsed


def merge_intervals(intervals_by_seqid: dict[str, list[tuple[int, int]]]) -> dict[str, list[tuple[int, int]]]:
    """Merge overlapping half-open intervals for each sequence ID."""
    merged_by_seqid: dict[str, list[tuple[int, int]]] = {}

    for seqid, intervals in intervals_by_seqid.items():
        if not intervals:
            continue

        sorted_intervals = sorted(intervals)
        merged = [sorted_intervals[0]]
        for start, end in sorted_intervals[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end:
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))

        merged_by_seqid[seqid] = merged

    return merged_by_seqid


def subtract_intervals(sequence_length: int, removal_intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Return half-open intervals left after removing centromere intervals."""
    if not removal_intervals:
        return [(0, sequence_length)]

    kept_intervals = []
    current_start = 0
    for remove_start, remove_end in removal_intervals:
        clipped_start = max(0, min(remove_start, sequence_length))
        clipped_end = max(0, min(remove_end, sequence_length))
        if clipped_end <= clipped_start:
            continue
        if current_start < clipped_start:
            kept_intervals.append((current_start, clipped_start))
        current_start = max(current_start, clipped_end)

    if current_start < sequence_length:
        kept_intervals.append((current_start, sequence_length))

    return kept_intervals


def count_removed_intervals(
    sequence: str,
    removal_intervals: list[tuple[int, int]],
    stats: FilterStats,
) -> None:
    """Count bases removed by annotation intervals."""
    for remove_start, remove_end in removal_intervals:
        clipped_start = max(0, min(remove_start, len(sequence)))
        clipped_end = max(0, min(remove_end, len(sequence)))
        if clipped_end <= clipped_start:
            continue

        removed_sequence = sequence[clipped_start:clipped_end]
        stats.removed_base_counts.update(removed_sequence.upper())
        stats.centromere_bp_removed += len(removed_sequence)


def write_chunk(
    output_file: TextIO,
    sequence_id: str,
    chunk_start: int,
    chunk_sequence: str,
    target: TargetAssembly,
    stats: FilterStats,
) -> None:
    """Write one kept chunk if it is long enough."""
    chunk_length = len(chunk_sequence)
    if chunk_length < MIN_CHUNK_LENGTH:
        return

    chunk_end = chunk_start + chunk_length
    chunk_id = f"{target.assembly_id}|{sequence_id}:{chunk_start}-{chunk_end}"
    organism_text = safe_header_text(target.organism_name)
    header = f">{chunk_id} organism={organism_text} assembly={target.assembly_id}\n"
    wrapped_sequence = textwrap.fill(chunk_sequence.upper(), width=80)
    output_text = f"{header}{wrapped_sequence}\n"
    output_file.write(output_text)
    stats.kept_chunks += 1
    stats.kept_bp += chunk_length
    stats.filtered_fasta_size_bytes += len(output_text.encode("utf-8"))


def process_fasta_record(
    output_file: TextIO,
    sequence_id: str,
    sequence_lines: list[str],
    target: TargetAssembly,
    stats: FilterStats,
    annotation_result: AnnotationResult | None,
) -> None:
    """Split one FASTA record into A/C/G/T chunks and write long enough chunks."""
    sequence = "".join(sequence_lines)
    stats.input_bp += len(sequence)
    removal_intervals = []
    if annotation_result is not None:
        removal_intervals = annotation_result.intervals_by_seqid.get(sequence_id, [])

    count_removed_intervals(sequence, removal_intervals, stats)
    kept_intervals = subtract_intervals(len(sequence), removal_intervals)

    for interval_start, interval_end in kept_intervals:
        process_sequence_interval(output_file, sequence_id, sequence, interval_start, interval_end, target, stats)


def process_sequence_interval(
    output_file: TextIO,
    sequence_id: str,
    sequence: str,
    interval_start: int,
    interval_end: int,
    target: TargetAssembly,
    stats: FilterStats,
) -> None:
    """Split one kept interval into A/C/G/T chunks and write long enough chunks."""
    interval_sequence = sequence[interval_start:interval_end]
    acgt_bp = 0
    last_acgt_end = 0

    for match in ACGT_RUN_RE.finditer(interval_sequence):
        removed_non_acgt_sequence = interval_sequence[last_acgt_end : match.start()]
        stats.removed_base_counts.update(removed_non_acgt_sequence.upper())

        chunk_sequence = match.group(0)
        chunk_start = interval_start + match.start()
        acgt_bp += len(chunk_sequence)
        if len(chunk_sequence) >= MIN_CHUNK_LENGTH:
            write_chunk(output_file, sequence_id, chunk_start, chunk_sequence, target, stats)
        else:
            stats.short_acgt_bp_removed += len(chunk_sequence)
            stats.removed_base_counts.update(chunk_sequence.upper())

        last_acgt_end = match.end()

    removed_non_acgt_sequence = interval_sequence[last_acgt_end:]
    stats.removed_base_counts.update(removed_non_acgt_sequence.upper())
    stats.non_acgt_bp_removed += len(interval_sequence) - acgt_bp


def bases_to_megabases(base_count: int) -> str:
    """Format a sequence size in megabases rounded to three decimal places."""
    return f"{base_count / 1_000_000:.3f}"


def removed_base_columns(stats_rows: list[FilterStats]) -> list[str]:
    """Return removed-base symbols to include as CSV columns."""
    observed_bases = {
        base
        for stats in stats_rows
        for base, count in stats.removed_base_counts.items()
        if count > 0
    }
    preferred_order = ["A", "C", "G", "T"]
    ordered_bases = [base for base in preferred_order if base in observed_bases]
    ordered_bases.extend(sorted(observed_bases - set(preferred_order)))
    return ordered_bases


def filter_cached_fasta(
    path: Path,
    output_file: TextIO,
    target: TargetAssembly,
    source_url: str,
    annotation_result: AnnotationResult | None,
) -> FilterStats:
    """Filter one cached gzipped FASTA into the combined output FASTA."""
    stats = FilterStats(
        organism_name=target.organism_name,
        assembly_id=target.assembly_id,
        source_url=source_url,
        cached_fasta_gz=str(path),
        cached_fasta_gz_size_bytes=path.stat().st_size,
    )
    if annotation_result is not None:
        stats.annotation_path = str(annotation_result.path)
        stats.annotation_records = annotation_result.total_records
        stats.centromere_regions_removed = annotation_result.true_centromere_regions
    sequence_id = None
    sequence_lines = []

    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as input_file:
        for raw_line in input_file:
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith(">"):
                if sequence_id is not None:
                    process_fasta_record(output_file, sequence_id, sequence_lines, target, stats, annotation_result)

                sequence_id = line[1:].split()[0]
                sequence_lines = []
                stats.input_records += 1
                continue

            if sequence_id is None:
                raise ValueError(f"Sequence data found before a FASTA header in {path}")

            sequence_lines.append(line)

    if sequence_id is not None:
        process_fasta_record(output_file, sequence_id, sequence_lines, target, stats, annotation_result)

    return stats


def write_summary(path: Path, stats_rows: list[FilterStats]) -> None:
    """Write per-assembly filtering summary statistics."""
    path.parent.mkdir(parents=True, exist_ok=True)
    base_columns = removed_base_columns(stats_rows)
    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(
            [
                "organism",
                "assembly ID",
                "size before filtering (MB)",
                "size after filtering (MB)",
            ]
            + [f"# {base} removed" for base in base_columns]
        )
        for stats in stats_rows:
            writer.writerow(
                [
                    stats.organism_name,
                    stats.assembly_id,
                    bases_to_megabases(stats.input_bp),
                    bases_to_megabases(stats.kept_bp),
                ]
                + [stats.removed_base_counts[base] for base in base_columns]
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter Evo2-trained protist genomes using OpenGenome-style rules.")
    parser.add_argument("--trained-protists", type=Path, default=DEFAULT_TRAINED_PROTISTS)
    parser.add_argument("--ncbi-database", type=Path, default=DEFAULT_NCBI_DATABASE)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--annotation-cache-dir", type=Path, default=DEFAULT_ANNOTATION_CACHE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Number of protist assemblies to filter. Use 0 for all.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.trained_protists.exists():
        raise FileNotFoundError(f"Trained protists file not found: {args.trained_protists}")
    if not args.ncbi_database.exists():
        raise FileNotFoundError(f"NCBI database file not found: {args.ncbi_database}")
    if args.limit < 0:
        raise ValueError("--limit must be 0 or a positive integer")

    targets = read_target_assemblies(args.trained_protists, args.limit)
    if not targets:
        raise ValueError(f"No target assemblies found in {args.trained_protists}")

    metadata_by_target_id = load_ncbi_metadata(args.ncbi_database, targets)
    missing_targets = [target.assembly_id for target in targets if target.assembly_id not in metadata_by_target_id]
    if missing_targets:
        missing_text = ", ".join(missing_targets)
        raise ValueError(f"Missing NCBI metadata for selected assembly IDs: {missing_text}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    stats_rows = []

    with args.output.open("w", encoding="utf-8", newline="\n") as output_file:
        for index, target in enumerate(targets, start=1):
            metadata = metadata_by_target_id[target.assembly_id]
            target_for_filtering = target
            if metadata.organism_name and target.organism_name == target.assembly_id:
                target_for_filtering = TargetAssembly(
                    organism_name=metadata.organism_name,
                    assembly_id=target.assembly_id,
                )

            source_url = genomic_fasta_url(metadata.ftp_path)
            cached_path = cache_path_for(args.cache_dir, target.assembly_id, source_url)
            print(
                f"[{index}/{len(targets)}] Downloading/filtering "
                f"{target_for_filtering.organism_name} ({target.assembly_id})"
            )
            download_if_needed(source_url, cached_path)
            annotation_path = download_annotation_if_available(
                metadata.ftp_path,
                args.annotation_cache_dir,
                target.assembly_id,
            )
            annotation_result = parse_annotation_file(annotation_path) if annotation_path is not None else None
            if annotation_result is not None:
                print(
                    "  GTF/GFF centromere filtering: "
                    f"{annotation_result.true_centromere_regions} regions from {annotation_path.name}"
                )
            else:
                print("  GTF/GFF centromere filtering: no annotation file found")
            stats_rows.append(
                filter_cached_fasta(cached_path, output_file, target_for_filtering, source_url, annotation_result)
            )

    write_summary(args.summary_output, stats_rows)

    total_input_bp = sum(stats.input_bp for stats in stats_rows)
    total_kept_bp = sum(stats.kept_bp for stats in stats_rows)
    total_kept_chunks = sum(stats.kept_chunks for stats in stats_rows)
    total_non_acgt_bp_removed = sum(stats.non_acgt_bp_removed for stats in stats_rows)
    total_short_acgt_bp_removed = sum(stats.short_acgt_bp_removed for stats in stats_rows)
    total_centromere_bp_removed = sum(stats.centromere_bp_removed for stats in stats_rows)
    total_filtered_fasta_size_bytes = sum(stats.filtered_fasta_size_bytes for stats in stats_rows)
    print(f"Assemblies filtered: {len(stats_rows)}")
    print(f"Input bp checked: {total_input_bp}")
    print(f"Non-ACGT bp removed: {total_non_acgt_bp_removed}")
    print(f"Short A/C/G/T bp removed: {total_short_acgt_bp_removed}")
    print(f"Centromere bp removed by GTF/GFF: {total_centromere_bp_removed}")
    print(f"Kept chunks written: {total_kept_chunks}")
    print(f"Kept bp written: {total_kept_bp}")
    print(f"Filtered FASTA size bytes: {total_filtered_fasta_size_bytes}")
    print(f"Wrote FASTA: {args.output}")
    print(f"Wrote summary: {args.summary_output}")


if __name__ == "__main__":
    main()
