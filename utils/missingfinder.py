#!/usr/bin/env python3
"""
Script to find bib entries whose PDFs are not in the library.
Compares keys in a bib file with filenames in a papers list file.

Usage:
    python missingfinder.py <bib_file> <papers_file>

Output files are automatically generated:
    - <bib_file>.missing_pdfs.txt - Entries without PDFs
    - <bib_file>.extras_in_library.txt - PDFs not in bib
    - <bib_file>.dups_in_library.txt - Duplicate PDF groups
    - <bib_file>.missingfinder.log - Execution log
"""

import argparse
import re
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from logging_utils import Logger, get_repo_dir


def extract_bib_entries(bib_file: str) -> dict[str, str]:
    """Extract all bib entries with their keys and full content."""
    with open(bib_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern to match bib entries: @type{key, ... }
    # This handles nested braces properly
    entries = {}
    pattern = r"@\w+\s*\{\s*([^,]+),"

    # Find all entry starts
    for match in re.finditer(pattern, content):
        key = match.group(1).strip()
        start = match.start()

        # Find the matching closing brace
        brace_count = 0
        end = start
        for i, char in enumerate(content[start:], start):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break

        entries[key] = content[start:end]

    return entries


def extract_pdf_keys(papers_file: str) -> set[str]:
    """Extract keys from PDF filenames in papers.txt."""
    keys = set()
    with open(papers_file, "r", encoding="utf-16") as f:
        for line in f:
            # Look for .pdf files
            match = re.search(r"(\S+)\.pdf", line, re.IGNORECASE)
            if match:
                key = match.group(1)
                keys.add(key)
    return keys


def extract_pdf_filenames(papers_file: str) -> list[str]:
    """Extract original PDF filenames (including extension) from papers.txt."""
    names: list[str] = []
    with open(papers_file, "r", encoding="utf-16") as f:
        for line in f:
            m = re.search(r"(\S+\.pdf)\b", line, re.IGNORECASE)
            if m:
                names.append(m.group(1))
    return names


def normalize_for_dedup(name_no_ext: str) -> str:
    """Normalize a library key (base filename) for duplicate detection.

    Rules:
    - Lowercase
    - Replace any sequence of non-alphanumeric with single underscore
    - Collapse multiple underscores
    - Strip leading/trailing underscores
    """
    s = name_no_ext.lower()
    # Replace non-alphanumeric (keep underscore as separator)
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    # Collapse underscores
    s = re.sub(r"_+", "_", s)
    # Strip
    s = s.strip("_")
    return s


def parse_args():
    parser = argparse.ArgumentParser(
        description="Find bib entries whose PDFs are not in the library."
    )
    parser.add_argument("bib_file", type=Path, help="Path to the bib file")
    parser.add_argument(
        "papers_file",
        type=Path,
        help="Path to the papers list file (directory listing of PDFs)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    bib_file = args.bib_file
    papers_file = args.papers_file

    # Auto-generate output file paths in repo directory
    repo_dir = get_repo_dir()
    base_name = bib_file.name
    output_file = repo_dir / f"{base_name}.missing_pdfs.txt"
    extras_out = repo_dir / f"{base_name}.extras_in_library.txt"
    dups_out = repo_dir / f"{base_name}.dups_in_library.txt"

    # Create unified logger
    with Logger("missingfinder", input_file=bib_file) as logger:
        log = logger.log

        log(f"Reading bib entries from {bib_file}...")
        bib_entries = extract_bib_entries(bib_file)
        log(f"Found {len(bib_entries)} bib entries")

        log(f"Reading PDF keys from {papers_file}...")
        pdf_keys = extract_pdf_keys(papers_file)
        log(f"Found {len(pdf_keys)} PDFs in library")

        # Find missing PDFs (in bib but not in library)
        bib_keys = set(bib_entries.keys())
        missing_keys = bib_keys - pdf_keys
        extra_keys = pdf_keys - bib_keys

        # Duplicate detection within library
        pdf_filenames = extract_pdf_filenames(str(papers_file))
        # Map normalized base name -> list of original filenames
        dup_groups: dict[str, list[str]] = {}
        for fn in pdf_filenames:
            base = fn[:-4] if fn.lower().endswith(".pdf") else fn
            norm = normalize_for_dedup(base)
            dup_groups.setdefault(norm, []).append(fn)
        duplicate_sets = {
            norm: files for norm, files in dup_groups.items() if len(files) > 1
        }

        log(f"\nMissing PDFs: {len(missing_keys)} entries")
        log(f"Extra PDFs in library (not in bib): {len(extra_keys)} entries")
        log(f"Potential duplicate groups in library: {len(duplicate_sets)} groups")

        # Write missing entries to output file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"% Missing PDFs: {len(missing_keys)} entries\n")
            f.write(
                f"% Keys in bib: {len(bib_keys)}, PDFs in library: {len(pdf_keys)}\n\n"
            )

            for key in sorted(missing_keys):
                f.write(bib_entries[key])
                f.write("\n\n")

        log(f"Missing entries written to {output_file}")

        # Also log the missing keys
        log("\nMissing keys:")
        for key in sorted(missing_keys):
            log(f"  - {key}")

        if duplicate_sets:
            log("\nDuplicate groups (preview up to 5 groups):")
            for i, (norm, files) in enumerate(
                sorted(duplicate_sets.items())[:5], start=1
            ):
                log(f"  {i}. {norm} -> {files}")

        # Write extras (library-only) keys to file
        with open(extras_out, "w", encoding="utf-8") as f:
            f.write(
                f"% PDFs present in library but not in bib: {len(extra_keys)} entries\n\n"
            )
            for key in sorted(extra_keys):
                f.write(f"{key}.pdf\n")
        log(f"\nExtra library PDFs written to {extras_out}")

        # Write duplicate groups report
        with open(dups_out, "w", encoding="utf-8") as f:
            f.write(
                f"% Potential duplicate groups in library: {len(duplicate_sets)} groups\n\n"
            )
            for norm, files in sorted(duplicate_sets.items()):
                f.write(f"[{norm}]\n")
                for fn in files:
                    f.write(f"- {fn}\n")
                # Suggest a canonical name if matching a bib key exists
                # Prefer exact base name match among files intersecting bib key set
                candidates = [fn[:-4] for fn in files if fn.lower().endswith(".pdf")]
                preferred = next(
                    (c for c in candidates if c in bib_keys),
                    candidates[0] if candidates else None,
                )
                if preferred:
                    f.write(f"Suggested canonical: {preferred}.pdf\n")
                f.write("\n")
        log(f"Duplicate groups report written to {dups_out}")


if __name__ == "__main__":
    main()
