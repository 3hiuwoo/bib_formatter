# BibCC - Copilot Instructions

## Project Overview
BibTeX utility toolkit for auto-completing missing fields, checking formatting quality, and managing reusable templates. All tools are standalone Python CLI scripts using `bibtexparser` + `pyyaml`.

## Architecture

### Two-Category Template System
Templates in [templates.py](../templates.py) are split by design:
- **`JOURNAL_TEMPLATES`**: Keyed by journal name only (year-agnostic) - journals have consistent metadata
- **`PROCEEDINGS_TEMPLATES`**: Keyed by `(venue_name, year)` tuple - conferences vary by year

This eliminates redundancy and reflects that journal metadata (publisher, ISSN) stays constant while conference metadata (venue city, ISBN) changes annually.

### Core Tools
| Script | Purpose |
|--------|---------|
| `completer.py` | Auto-fills missing BibTeX fields from templates |
| `checker.py` | Quality checks: missing fields, title case, term protection |
| `yaml2templates.py` | Updates `templates.py` from user-filled YAML |
| `titlecases.py` | APA-style title case transformation logic |

### Utilities (`utils/`)
- `missingfinder.py` - Cross-references bib entries with PDF library
- `pdfrenamer.py` - Renames PDFs to match bib keys by download order
- `titleretriever.py` - Fetches original titles from CrossRef/DBLP/arXiv/Semantic Scholar

## Template Workflow
The intended three-step workflow for adding new templates:
1. Run `python completer.py input.bib` → generates `*.missing_templates.yaml`
2. User fills in the YAML with metadata (publisher, ISSN, venue, etc.)
3. Run `python yaml2templates.py <file>.yaml --update` → merges into `templates.py`

## Key Patterns

### Unified Logging
All tools use `Logger` from [logging_utils.py](../logging_utils.py):
```python
from logging_utils import Logger
with Logger("checker", input_file="my.bib") as logger:
    logger.log("Processing...")  # Writes to stdout + logs/my.bib.checker.log
```
Logs auto-generate in `logs/` directory with naming: `<input>.<tool>.log`

### Text Normalization
For matching venues/titles, use `normalize_text()`:
```python
def normalize_text(text: str) -> str:
    return text.replace("{", "").replace("}", "").strip().lower()
```

### Entry Type Detection
`_detect_entry_type()` in completer.py determines journal vs proceedings by:
1. BibTeX `ENTRYTYPE` (article → journal, inproceedings → proceedings)
2. Field presence fallback (has `journal` field → journal)

## Code Conventions
- Type hints required for function signatures
- Use `Optional[Callable[[str], None]]` for optional log callbacks
- Path handling: always use `pathlib.Path`
- YAML output: escape backslashes for venue names containing `\&`

## Testing & Development
This toolkit is developed separately from target LaTeX projects. When testing:
- Target papers may have a `bib/` folder with subfolders or individual `.bib` files, or a single `.bib` file at project root
- Always specify a concrete `.bib` file path when running tools (no folder scanning)
- Create a dummy `.bib` file for testing new features if needed

### Python Environment
This project uses a mamba environment named `pmq`. Before running any commands:
```bash
mamba activate pmq
```

## Commands Reference
```bash
# Install dependencies
pip install bibtexparser pyyaml

# Complete missing fields (preview only)
python completer.py input.bib

# Write completed output
python completer.py input.bib --output output.bib

# Check for missing fields
python checker.py input.bib --fields month,publisher

# Title case suggestions (APA style)
python checker.py input.bib --title-case --title-style apa

# Suggest brace protection for technical terms
python checker.py input.bib --quote --quote-terms Gaussian,Kalman

# Check templates for completeness
python checker.py --check-templates
```
