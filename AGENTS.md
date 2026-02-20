# AGENTS.md - BibCC

> BibTeX Check & Complete toolkit - Python CLI tools for auto-completing missing fields, checking formatting quality, and managing reusable templates.

## Quick Reference

```bash
mamba activate pmq                               # Required environment
pip install bibtexparser pyyaml                  # Dependencies

# --- Unified CLI (recommended) ---
python bibcc.py check    input.bib --fields month                  # Check missing fields
python bibcc.py check    input.bib --title-case                    # Title case check (APA style)
python bibcc.py check    input.bib --quote --quote-terms Gaussian  # Term protection
python bibcc.py check    input.bib --check-keys                   # Citation key legibility
python bibcc.py check    --check-templates                        # Validate templates
python bibcc.py complete input.bib                                 # Preview completion
python bibcc.py complete input.bib --output out.bib                # Write output
python bibcc.py librarian missing  input.bib papers.txt           # Missing PDFs
python bibcc.py librarian extra    input.bib papers.txt           # Extra PDFs
python bibcc.py librarian rename   input.bib ~/papers --dry-run   # Preview rename
python bibcc.py scholar  cite   input.bib                         # Citation URLs
python bibcc.py scholar  titles input.bib                         # Title verification
python bibcc.py compose  compose ./bibs combined.bib              # Compose .bib files

# --- Standalone tools (same options as above) ---
python checker.py input.bib --fields month
python completer.py input.bib --output out.bib
python utils/librarian.py missing input.bib papers.txt
python utils/scholar.py cite input.bib
python utils/scholar.py titles input.bib
python utils/composer.py compose ./bibs combined.bib
```

## Architecture

```text
bibcc/
├── bibcc.py           # Unified CLI entry point (check/complete/librarian/scholar/compose)
├── checker.py         # Quality checks: missing fields, title case, term protection
├── completer.py       # Auto-fills missing BibTeX fields from templates
├── yaml2templates.py  # Updates templates.py from user-filled YAML
├── templates.py       # Template database (journals + proceedings)
├── titlecases.py      # APA-style title case transformation
├── logging_utils.py   # Unified logging, report writing, format constants
├── logs/              # Auto-generated log files
├── checkers/          # Sub-checker modules (imported by checker.py)
│   ├── __init__.py
│   ├── citation_keys.py      # METHOD_AUTHOR_VENUEYEAR convention check
│   ├── missing_fields.py     # Required field detection
│   ├── smart_protection.py   # Brace protection for technical terms
│   ├── template_fields.py    # Template completeness check
│   └── title_case.py         # Title case wrapper
└── utils/
    ├── scholar.py       # Citation counts + title verification (cite/titles)
    ├── librarian.py     # PDF library ↔ bib alignment (missing/extra/rename)
    └── composer.py      # Compose .bib files from folders into one file
```

### Template System

- **`JOURNAL_TEMPLATES`**: Keyed by journal name (year-agnostic) — journals have consistent metadata (publisher, ISSN)
- **`PROCEEDINGS_TEMPLATES`**: Keyed by `(venue_name, year)` tuple — conferences vary by year (venue city, ISBN)

## Code Style

### Imports

```python
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import bibtexparser

from logging_utils import Logger, get_repo_dir
```

Order: `__future__` → stdlib → third-party → local modules (no blank lines between)

### Type Hints (Required)

```python
def find_template(
    venue: str,
    year: str,
    entry_type: str,
) -> Optional[Dict[str, str]]:
    ...

# Use Optional[Callable[[str], None]] for log callbacks
# Use Path from pathlib for file paths
```

### Dataclasses

```python
@dataclass
class TitleMatch:
    source: str
    original_title: str
    confidence: str  # "high", "medium", "low"
    url: Optional[str] = None
```

### Docstrings

Module-level required with usage examples. Function docstrings for public APIs:

```python
def normalize_text(text: Optional[str]) -> str:
    """Normalize text for comparison by removing braces and lowercasing."""
```

### Path Handling

**Always use `pathlib.Path`:**

```python
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(content, encoding="utf-8")
```

### Logging & Output Formatting

Always keep output format consistent regarding emoji and characters used for status indicators and separator, etc.
All format constants live in `logging_utils.py` and must be used instead of hard-coded values:

```python
from logging_utils import (
    SEPARATOR_WIDTH,    # 70 — standard width for all separators
    SEPARATOR_HEAVY,    # "=" — headers, section boundaries
    SEPARATOR_LIGHT,    # "-" — subsection breaks
    SEPARATOR_THIN,     # "─" — summary lines
    Logger,
    write_report,       # Shared report-file writer
    get_repo_dir,
)

# Logger usage
with Logger("checker", input_file="my.bib") as logger:
    logger.log("Processing...")
    logger.log("Found 10 entries", prefix="✅")
# Auto-saves to: logs/my.bib.checker.log

# Report file usage (canonical format: header + rows)
from pathlib import Path
write_report(Path("out.txt"), "header\tcol1\tcol2", ["row1", "row2"])

# Separators — always use constants, never hard-code widths
logger.log(SEPARATOR_HEAVY * SEPARATOR_WIDTH)  # ====...====
logger.log(SEPARATOR_LIGHT * SEPARATOR_WIDTH)  # ----...----
```

**Important**: Never use raw `print()` in tool code — always accept and use a `log: Callable[[str], None]` callback.

### Text Normalization

```python
def normalize_text(text: str) -> str:
    return text.replace("{", "").replace("}", "").strip().lower()
```

### Constants

Use UPPER_CASE for constants, sets for vocabularies:

```python
DEFAULT_VOCAB = {"gaussian", "bayesian", "markov"}
```

### CLI Pattern

Every tool exposes `build_parser()` → `run(args)` for integration with `bibcc.py`:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BibTeX Quality Checker")
    parser.add_argument("input", help="Input .bib file")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--dry-run", action="store_true")
    return parser

def run(args: argparse.Namespace) -> None:
    """Run tool with parsed arguments."""
    ...

if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    run(args)
```

Utils tools (`librarian.py`, `scholar.py`, `composer.py`) use `build_parser()` + `main()` with subparsers.

## Key Patterns

### Entry Type Detection

```python
def _detect_entry_type(entry: Dict[str, Any]) -> str:
    entry_type = entry.get("ENTRYTYPE", "").lower()
    if entry_type == "article":
        return "journal"
    if entry_type in ("inproceedings", "proceedings", "conference"):
        return "proceedings"
    if entry.get("journal"):
        return "journal"
    return "proceedings"
```

### YAML Output

Escape backslashes for venue names: `venue_escaped = venue_raw.replace("\\", "\\\\")`

## Template Workflow

1. `python completer.py input.bib` → generates `*.missing_templates.yaml`
2. Fill in YAML with metadata (publisher, ISSN, venue, etc.)
3. `python yaml2templates.py <file>.yaml --update`
4. `python completer.py input.bib --output output.bib`

## Output Files

| Tool | Report Files | Log Files |
| ------ | -------------- | ----------- |
| checker.py | `.missing_fields.txt`, `.title_case.txt`, `.citation_keys.txt`, `.smart_protection.txt` | `logs/*.checker.log` |
| completer.py | `.missing_templates.yaml`, `.conflicts.txt`, `.incomplete_entries.txt` | `logs/*.completer.log` |
| librarian.py | `.missing_pdfs.txt`, `.extra_pdfs.txt`, `.rename_report.txt` | `logs/*.librarian.log` |
| scholar.py | `.title_report.txt`, `.scholar_urls.txt` | `logs/*.scholar.cite.log`, `logs/*.scholar.titles.log` |
| composer.py | (composed .bib file) | `logs/*.composer.log` |

## Testing

- No formal test suite - test manually with real bib files
- Always specify concrete `.bib` file path (no folder scanning)
- Create dummy `.bib` files for testing new features

## Dependencies

- `bibtexparser` - BibTeX parsing
- `pyyaml` - YAML handling
- Python 3.9+ (uses `Path | None` syntax)
