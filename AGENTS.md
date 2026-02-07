# AGENTS.md - BibCC

> BibTeX Check & Complete toolkit - Python CLI tools for auto-completing missing fields, checking formatting quality, and managing reusable templates.

## Quick Reference

```bash
mamba activate pmq                               # Required environment
pip install bibtexparser pyyaml                  # Dependencies

python completer.py input.bib                    # Preview completion
python completer.py input.bib --output out.bib   # Write output
python checker.py input.bib --fields month       # Check missing fields
python checker.py input.bib --title-case         # Title case check (APA style)
python checker.py input.bib --quote --quote-terms Gaussian,Kalman  # Term protection
python checker.py --check-templates              # Validate templates

python utils/librarian.py missing  input.bib papers.txt           # Bib entries missing from PDF library
python utils/librarian.py extra    input.bib papers.txt           # Library PDFs not in bib
python utils/librarian.py rename   input.bib ~/Desktop/papers2 --dry-run  # Preview title-based rename
python utils/librarian.py rename   input.bib ~/Desktop/papers2           # Apply rename
```

## Architecture

```text
bibcc/
├── completer.py       # Auto-fills missing BibTeX fields from templates
├── checker.py         # Quality checks: missing fields, title case, term protection
├── yaml2templates.py  # Updates templates.py from user-filled YAML
├── templates.py       # Template database (journals + proceedings)
├── titlecases.py      # APA-style title case transformation
├── logging_utils.py   # Unified logging (stdout + file)
├── logs/              # Auto-generated log files
└── utils/
    ├── citer.py             # Import citation counts from Google Scholar
    ├── librarian.py         # Unified PDF library ↔ bib alignment (title-based)
    └── titleretriever.py    # Fetch titles from CrossRef/DBLP/arXiv
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

### Logging

```python
from logging_utils import Logger

with Logger("checker", input_file="my.bib") as logger:
    logger.log("Processing...")
    logger.log("Found 10 entries", prefix="✅")
# Auto-saves to: logs/my.bib.checker.log
```

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

```python
parser = argparse.ArgumentParser(description="BibTeX Quality Checker")
parser.add_argument("input", help="Input .bib file")
parser.add_argument("--output", "-o", help="Output file path")
parser.add_argument("--dry-run", action="store_true")
```

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
| checker.py | `.missing_fields.txt`, `.title_case.txt` | `logs/*.checker.log` |
| completer.py | `.missing_templates.yaml`, `.conflicts.txt` | `logs/*.completer.log` |
| librarian.py | `.missing_pdfs.txt`, `.extra_pdfs.txt`, `.rename_report.txt` | `logs/*.librarian.log` |
| titleretriever.py | `.title_report.txt` | `logs/*.titleretriever.log` |

## Testing

- No formal test suite - test manually with real bib files
- Always specify concrete `.bib` file path (no folder scanning)
- Create dummy `.bib` files for testing new features

## Dependencies

- `bibtexparser` - BibTeX parsing
- `pyyaml` - YAML handling
- Python 3.9+ (uses `Path | None` syntax)
