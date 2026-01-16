#!/usr/bin/env python3
"""
Script to find bib entries whose PDFs are not in the library.
Compares keys in a bib file with filenames in a papers list file.

Usage:
    python missingfinder.py <bib_file> <papers_file> [-o output_file]
"""

import argparse
import re
from pathlib import Path


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
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output file path (default: <bib_file>.missing_pdfs.txt)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    bib_file = args.bib_file
    papers_file = args.papers_file
    output_file = args.output or bib_file.with_suffix(".missing_pdfs.txt")

    print(f"Reading bib entries from {bib_file}...")
    bib_entries = extract_bib_entries(bib_file)
    print(f"Found {len(bib_entries)} bib entries")

    print(f"Reading PDF keys from {papers_file}...")
    pdf_keys = extract_pdf_keys(papers_file)
    print(f"Found {len(pdf_keys)} PDFs in library")

    # Find missing PDFs (in bib but not in library)
    bib_keys = set(bib_entries.keys())
    missing_keys = bib_keys - pdf_keys

    print(f"\nMissing PDFs: {len(missing_keys)} entries")

    # Write missing entries to output file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"% Missing PDFs: {len(missing_keys)} entries\n")
        f.write(f"% Keys in bib: {len(bib_keys)}, PDFs in library: {len(pdf_keys)}\n\n")

        for key in sorted(missing_keys):
            f.write(bib_entries[key])
            f.write("\n\n")

    print(f"Missing entries written to {output_file}")

    # Also print the missing keys to console
    print("\nMissing keys:")
    for key in sorted(missing_keys):
        print(f"  - {key}")


if __name__ == "__main__":
    main()
