"""
BibTeX Completer - Enhanced version with new template structure support.

This module completes BibTeX entries by adding missing metadata fields from templates.
It supports the new optimized template structure that separates journals (year-agnostic)
from proceedings (year-specific).

New workflow for missing templates:
1. Run completer.py (this file) - generates YAML file with missing combos
2. User fills in the YAML file directly with required fields
3. Run yaml2templates.py to update templates from the filled YAML
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import bibtexparser

from logging_utils import Logger, get_repo_dir
from templates import JOURNAL_TEMPLATES, PROCEEDINGS_TEMPLATES


def normalize_text(text: Optional[str]) -> str:
    """Normalize text for comparison by removing braces and lowercasing."""
    if not text:
        return ""
    return text.replace("{", "").replace("}", "").strip().lower()


def _write_log(path: Path, header: str, rows: List[str]) -> None:
    """Write a simple log file with header and rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = [header]
    content.extend(rows if rows else ["(none)"])
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def _write_yaml_missing_templates(
    path: Path,
    missing_templates: Dict[Tuple[str, str], Tuple[str, str, str]],
) -> None:
    """
    Write missing templates to a YAML file for user to fill in.

    The YAML format allows users to directly specify fields without
    needing to collect BibTeX entries first.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Missing templates - fill in the 'fields' section for each entry",
        "# Then run: python yaml2templates.py {} --update".format(path.name),
        "#",
        "# Entry types:",
        '#   - "journal": For journal articles (year-agnostic, keyed by journal name)',
        '#   - "proceedings": For conference papers (year-specific)',
        "",
        "templates:",
    ]

    for venue_raw, year, entry_type in missing_templates.values():
        # Escape backslashes for YAML double-quoted strings (e.g., \& -> \\&)
        venue_escaped = venue_raw.replace("\\", "\\\\")
        lines.append(f'  - venue: "{venue_escaped}"')
        lines.append(f'    year: "{year}"')
        lines.append(f"    type: {entry_type}")
        lines.append("    fields:")

        if entry_type == "journal":
            lines.append('      publisher: ""  # e.g., IEEE, Elsevier, Springer')
            lines.append('      issn: ""')
            lines.append('      # address: ""  # optional, e.g., New York, NY, USA')
        else:
            lines.append('      venue: ""  # e.g., City, Country')
            lines.append('      publisher: ""')
            lines.append('      month: ""  # e.g., June, October')
            lines.append('      # isbn: ""')
            lines.append('      # issn: ""')
            lines.append('      # editor: ""')
            lines.append('      # series: ""')
            lines.append('      # address: ""')
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _detect_entry_type(entry: Dict[str, Any]) -> str:
    """Detect if an entry is a journal article or proceedings."""
    entry_type = entry.get("ENTRYTYPE", "").lower()

    # Article type is typically journal
    if entry_type == "article":
        return "journal"

    # Inproceedings is typically proceedings/conference
    if entry_type in ("inproceedings", "proceedings", "conference"):
        return "proceedings"

    # Check by field presence
    if entry.get("journal"):
        return "journal"
    if entry.get("booktitle"):
        return "proceedings"

    return "proceedings"  # default


def find_template(
    venue: str,
    year: str,
    entry_type: str,
) -> Optional[Dict[str, str]]:
    """
    Find matching template for a venue/year combination.

    For journals: looks up by venue name only (year-agnostic)
    For proceedings: looks up by (venue, year) tuple
    """
    clean_venue = normalize_text(venue)
    clean_year = normalize_text(year)

    if entry_type == "journal":
        # Journal lookup: by name only
        for tmpl_name, fields in JOURNAL_TEMPLATES.items():
            if normalize_text(tmpl_name) == clean_venue:
                return fields
    else:
        # Proceedings lookup: by (venue, year)
        for (tmpl_venue, tmpl_year), fields in PROCEEDINGS_TEMPLATES.items():
            if (
                normalize_text(tmpl_venue) == clean_venue
                and normalize_text(tmpl_year) == clean_year
            ):
                return fields
    return None


def main(
    input_path: str,
    output_path: str,
    dry_run: bool = False,
    log_dir: Path | None = None,
    log: Optional[Callable[[str], None]] = None,
):
    """Main entry point for the completer."""
    log = log or print
    log(f"Reading {input_path}...")
    log("📦 Using template structure (journals + proceedings)")

    # --- PASS 1: THE BRAIN ---
    # Parse to understand the data
    with open(input_path, "r", encoding="utf-8") as f:
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        bib_db = bibtexparser.load(f, parser=parser)

    # Create a "Patch List": { "ENTRY_ID": { "field": "value", ... } }
    patches: Dict[str, Dict[str, str]] = {}
    conflicts: Dict[str, List[Tuple[str, str, str]]] = {}

    # Map normalized key -> (raw_venue, year, entry_type) for unique reporting
    missing_templates: Dict[Tuple[str, str], Tuple[str, str, str]] = {}

    # Incomplete entries: missing year or venue (e.g., arxiv misc)
    # These are reported separately and do NOT contribute to the YAML file
    incomplete_entries: List[Tuple[str, str, str]] = []  # (entry_id, venue, year)

    for entry in bib_db.entries:
        entry_id = entry["ID"]
        year = entry.get("year", "")
        venue_raw = entry.get("booktitle") or entry.get("journal") or ""
        entry_type = _detect_entry_type(entry)

        if not year or not venue_raw:
            # Incomplete entry - missing year or venue, likely arxiv/misc
            incomplete_entries.append((entry_id, venue_raw, year))
            continue

        # Find matching template
        clean_venue = normalize_text(venue_raw)
        clean_year = normalize_text(year)

        matched_template = find_template(venue_raw, year, entry_type)

        if not matched_template:
            # For journals, key is venue only (year-agnostic)
            # For proceedings, key is (venue, year)
            if entry_type == "journal":
                key = (clean_venue, "")  # journals are year-agnostic
            else:
                key = (clean_venue, clean_year)
            missing_templates.setdefault(key, (venue_raw, year, entry_type))
            continue

        fields_to_add = {}
        conflicts_to_add = []
        for k, v in matched_template.items():
            if k not in entry:
                fields_to_add[k] = v
            else:
                existing_val = entry.get(k, "")
                if normalize_text(existing_val) != normalize_text(v):
                    conflicts_to_add.append((k, existing_val, v))

        if fields_to_add:
            patches[entry_id] = fields_to_add
        if conflicts_to_add:
            conflicts[entry_id] = conflicts_to_add

    log(f"  Identified {len(patches)} entries to patch.")

    # Prepare log paths - always output to repo directory
    repo_dir = get_repo_dir()
    output_dir = Path(log_dir) if log_dir else repo_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    base = Path(input_path).name
    conflict_log = output_dir / f"{base}.conflicts.txt"
    missing_txt_log = output_dir / f"{base}.missing_templates.txt"
    missing_yaml_log = output_dir / f"{base}.missing_templates.yaml"

    # Collect log rows
    conflict_rows: List[str] = []
    for eid, rows in conflicts.items():
        for k, existing_val, tmpl_val in rows:
            conflict_rows.append(
                f"{eid}\t{k}\tEXISTING={existing_val}\tTEMPLATE={tmpl_val}"
            )

    missing_rows: List[str] = []
    for venue_raw, year, entry_type in missing_templates.values():
        missing_rows.append(f"{venue_raw}\t{year}\t{entry_type}")

    incomplete_rows: List[str] = []
    for entry_id, venue, year in incomplete_entries:
        incomplete_rows.append(
            f"{entry_id}\tvenue={venue or '(empty)'}\tyear={year or '(empty)'}"
        )

    # Dry-run summary
    if dry_run:
        if patches:
            log("\n🧪 Dry-run additions:")
            for eid, fields in patches.items():
                log(f"Entry ID: {eid}")
                for k, v in fields.items():
                    log(f"    add {k} = {{{v}}}")
        else:
            log("\n🧪 Dry-run: no additions needed.")

        if conflicts:
            log(
                "\n⚠️  Conflicts (existing value differs from template, not overwritten):"
            )
            for eid, conflicts_fields in conflicts.items():
                log(f"Entry ID: {eid}")
                for k, existing_val, tmpl_val in conflicts_fields:
                    log(
                        f"  field '{k}': existing='{existing_val}', template='{tmpl_val}'"
                    )
        else:
            log("\n✅ No conflicts detected.")

        if incomplete_entries:
            log(
                "\n📭 Incomplete entries (missing year or venue, e.g., arxiv/misc) - skipped:"
            )
            for entry_id, venue, year in incomplete_entries:
                log(
                    f"  🔸 {entry_id}: venue='{venue or '(empty)'}' year='{year or '(empty)'}'"
                )

        if missing_templates:
            log(
                "\nℹ️  Missing (venue, year) combinations not in templates (deduplicated):"
            )
            for venue_raw, year, entry_type in missing_templates.values():
                type_icon = "📰" if entry_type == "journal" else "📋"
                log(f"  {type_icon} [{entry_type}] venue='{venue_raw}' year='{year}'")
        else:
            log("\n✅ All complete entries matched existing templates.")

        # Write logs
        _write_log(
            conflict_log,
            "conflicts: entry_id\tfield\texisting\ttemplate",
            conflict_rows,
        )
        _write_log(
            missing_txt_log,
            "missing templates: venue\tyear\ttype",
            missing_rows,
        )

        # Write incomplete entries log
        incomplete_log = output_dir / f"{base}.incomplete_entries.txt"
        _write_log(
            incomplete_log,
            "incomplete entries (missing year or venue): entry_id\tvenue\tyear",
            incomplete_rows,
        )

        # Write YAML file for missing templates (new workflow!)
        # Only include entries with both venue and year (not incomplete ones)
        if missing_templates:
            _write_yaml_missing_templates(missing_yaml_log, missing_templates)
            log(f"\n📝 YAML template file created: {missing_yaml_log}")
            log(
                "   Fill in the fields and run: python yaml2templates.py {} --update".format(
                    missing_yaml_log
                )
            )

        log(f"\nLogs saved: {conflict_log}, {missing_txt_log}, {incomplete_log}")
        return

    # --- PASS 2: THE SURGEON ---
    # Read the file as plain text lines to preserve comments
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(output_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line)

            match = re.search(r"@\w+\s*\{\s*([^,]+),", line)

            if match:
                current_id = match.group(1).strip()

                if current_id in patches:
                    new_data = patches[current_id]

                    for key, val in new_data.items():
                        f.write(f"  {key:<12} = {{{val}}},\n")

                    del patches[current_id]

    log(f"✅ Done! Saved to {output_path} (Comments preserved)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enhance a BibTeX (.bib) file by adding missing metadata fields from templates."
    )
    parser.add_argument("input", type=str, help="Path to the input BibTeX (.bib) file")
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Path to save the output enhanced BibTeX (.bib) file (omit for dry-run).",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="",
        help="Directory to write logs (conflicts/missing). Default: current directory.",
    )
    args = parser.parse_args()

    dry_run = not bool(args.output)
    log_dir = Path(args.log_dir) if args.log_dir else None

    with Logger("completer", input_file=args.input, log_dir=log_dir) as logger:
        main(
            args.input,
            args.output or args.input,
            dry_run=dry_run,
            log_dir=log_dir,
            log=logger.log,
        )
