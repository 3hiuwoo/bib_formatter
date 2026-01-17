#!/usr/bin/env python3
"""
Rename downloaded PDFs to match bib keys based on temporal order.
Assumes PDFs were downloaded in the same order as entries in the missing report.

Usage:
    python pdfrenamer.py <missing_report> <pdf_folder> [--dry-run]

Output:
    - Automatically generates <report>.pdfrenamer.log
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from logging_utils import Logger


def extract_keys_from_report(report_file: Path) -> list[str]:
    """Extract bib keys from the missing PDFs report in order."""
    keys = []
    with open(report_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Match @type{key, pattern
    pattern = r"@\w+\s*\{\s*([^,]+),"
    for match in re.finditer(pattern, content):
        key = match.group(1).strip()
        keys.append(key)

    return keys


def get_pdfs_by_time(pdf_folder: Path) -> list[Path]:
    """Get PDF files sorted by modification time (oldest first)."""
    pdfs = list(pdf_folder.glob("*.pdf"))
    pdfs.sort(key=lambda p: p.stat().st_mtime)
    return pdfs


def main():
    parser = argparse.ArgumentParser(
        description="Rename PDFs to match bib keys based on download order."
    )
    parser.add_argument(
        "report", type=Path, help="Path to the missing PDFs report file"
    )
    parser.add_argument(
        "pdf_folder", type=Path, help="Path to the folder containing downloaded PDFs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview renames without actually renaming",
    )
    args = parser.parse_args()

    # Create unified logger
    with Logger("pdfrenamer", input_file=args.report) as logger:
        log = logger.log

        log(f"Reading keys from {args.report}...")
        keys = extract_keys_from_report(args.report)
        log(f"Found {len(keys)} keys")

        log(f"Scanning PDFs in {args.pdf_folder}...")
        pdfs = get_pdfs_by_time(args.pdf_folder)
        log(f"Found {len(pdfs)} PDFs")

        if len(keys) != len(pdfs):
            log(f"\n⚠️  Warning: Key count ({len(keys)}) != PDF count ({len(pdfs)})")
            log("Proceeding with the minimum of both...")

        count = min(len(keys), len(pdfs))

        log(f"\n{'[DRY RUN] ' if args.dry_run else ''}Renaming {count} files:\n")

        for i, (pdf, key) in enumerate(zip(pdfs[:count], keys[:count]), 1):
            new_name = f"{key}.pdf"
            new_path = pdf.parent / new_name

            log(f"{i:3}. {pdf.name}")
            log(f"     -> {new_name}")

            if not args.dry_run:
                if new_path.exists() and new_path != pdf:
                    log(f"     ⚠️  Target exists, skipping")
                    continue
                shutil.move(pdf, new_path)

        if args.dry_run:
            log(f"\n[DRY RUN] No files were renamed. Remove --dry-run to apply.")
        else:
            log(f"\n✅ Renamed {count} files")


if __name__ == "__main__":
    main()
