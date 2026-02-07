# 📚 BibTeX Check & Complete (BibCC)

Small BibTeX utility toolkit to auto-complete missing fields, check formatting quality, and maintain reusable templates.

## 🚀 Quick start

```bash
pip install bibtexparser pyyaml
```

## 🧩 Core Tools

### Complete missing fields — `completer.py`

- **Preview only** (no write-back, generates logs and YAML for missing templates):

  ```bash
  python completer.py input.bib
  ```

- **Write completed output** (overwrites the given output path):

  ```bash
  python completer.py input.bib --output output.bib
  ```

- **Choose a log directory**: `--log-dir logs/`

### Quality checks — `checker.py`

- **Missing-field check** (default entry types: inproceedings, article, proceedings, conference):

  ```bash
  python checker.py input.bib --fields month,publisher
  ```

- **Title Case suggestions** (APA style by default):

  ```bash
  python checker.py input.bib --title-case --title-style apa
  # Add --title-apply to modify titles in the original file
  ```

- **Smart protection** for technical terms (suggest braces):

  ```bash
  python checker.py input.bib --quote --quote-terms Gaussian,Kalman
  ```

- **Template field check** (check templates.py for missing fields):

  ```bash
  # Check with default fields (publisher, issn for journals; venue, publisher, month for proceedings)
  python checker.py --check-templates

  # Check with custom fields
  python checker.py --check-templates --journal-fields publisher,issn --proceedings-fields venue,month,isbn
  ```

## 🗂️ Template Management

### Template Structure

Templates are separated into two categories in `templates.py`:

1. **`JOURNAL_TEMPLATES`** — Year-agnostic (journals have consistent metadata)
2. **`PROCEEDINGS_TEMPLATES`** — Year-specific (conferences vary by year)

This eliminates redundancy where the same journal was repeated for each year.

### Workflow for Adding Templates

1. Run `completer.py` → generates `*.missing_templates.yaml`
2. Fill in the YAML file directly with required fields
3. Run `yaml2templates.py` to update templates

### Step-by-step

1. **Identify missing templates**:

   ```bash
   python completer.py input.bib
   # Creates: input.bib.missing_templates.yaml
   ```

2. **Fill in the YAML file** with required metadata:

   ```yaml
   templates:
     - venue: "IEEE Transactions on Example"
       year: "2025"
       type: journal
       fields:
         publisher: "IEEE"
         issn: "1234-5678"

     - venue: "2025 Example Conference"
       year: "2025"
       type: proceedings
       fields:
         venue: "City, Country"
         publisher: "IEEE"
         month: "June"
         isbn: "978-..."
   ```

3. **Update templates**:

   ```bash
   # Preview changes
   python yaml2templates.py input.bib.missing_templates.yaml

   # Apply changes
   python yaml2templates.py input.bib.missing_templates.yaml --update
   ```

4. **Re-run completer** to complete entries:

   ```bash
   python completer.py input.bib --output output.bib
   ```

### Incomplete Entries

Entries missing year or venue (e.g., arxiv preprints, misc entries) are automatically detected and reported separately in `*.incomplete_entries.txt`. These do not contribute to the YAML file since they cannot be matched to templates.

## 📁 File Structure

```text
bibcc/
├── completer.py          # Main completion tool
├── checker.py            # Quality checking tool
├── yaml2templates.py     # YAML → templates converter
├── templates.py          # Templates (journals + proceedings)
├── titlecases.py         # Title case utilities
├── logging_utils.py      # Unified logging utilities
├── logs/                 # Execution logs (auto-generated)
│   └── *.log
└── utils/
    ├── citer.py            # Import citation counts from Google Scholar
    ├── librarian.py        # PDF library ↔ bib alignment (missing, extra, rename)
    └── titleretriever.py   # Retrieve titles from external sources
```

## 📝 Unified Logging

All tools now use a unified logging strategy that:

1. **Automatically generates output files** - No need to manually specify `--output`
2. **Logs to both stdout and file** - See output in terminal and have a permanent record
3. **Report files in repo root** - Primary outputs (`.txt`, `.yaml`) are saved to repo directory
4. **Log files in `logs/` folder** - Execution logs are organized in `logs/` subdirectory
5. **Consistent naming convention** - Files are named `<input_file>.<tool_name>.<type>`

### Output Files by Tool

| Tool | Report Files (repo root) | Log Files (`logs/`) |
| ------ | --------------- | --------------- |
| `checker.py` | `.missing_fields.txt`, `.title_case.txt`, `.smart_protection.txt` | `.checker.log` |
| `completer.py` | `.conflicts.txt`, `.missing_templates.txt`, `.missing_templates.yaml`, `.incomplete_entries.txt` | `.completer.log` |
| `citer.py` | `.scholar_urls.txt` | `.citer.log` |
| `librarian.py` | `.missing_pdfs.txt`, `.extra_pdfs.txt`, `.rename_report.txt` | `.librarian.log` |
| `titleretriever.py` | `.title_report.txt` | `.titleretriever.log` |

### Using logging_utils.py

```python
from logging_utils import Logger, get_repo_dir

with Logger("my_tool", input_file="data.bib") as logger:
    logger.log("Processing...")       # Goes to stdout and file
    logger.log("Done!", prefix="✅")  # With prefix
# Log file auto-saved to: logs/data.bib.my_tool.log
```

## 🛠️ Utilities

### Import citation counts — `utils/citer.py`

Manually import citation counts from Google Scholar with browser automation:

```bash
# Preview mode - show entries needing citations
python utils/citer.py input.bib

# Interactive mode - open URLs one by one and prompt for citation count
python utils/citer.py input.bib --interactive

# Batch mode - open URLs in browser tabs (5 at a time)
python utils/citer.py input.bib --open

# Include entries that already have citations (for updating)
python utils/citer.py input.bib -i --include-filled
```

**Interactive mode workflow**:

1. For each entry, a Google Scholar search opens in your browser
2. You read the citation count from the page
3. Enter the count when prompted (or skip/quit)
4. Changes are saved when you quit or finish

**Options**:

- `--interactive`, `-i`: Interactive fill mode (recommended)
- `--open`: Batch open URLs in browser tabs
- `--batch-size N`: Number of URLs per batch (default: 5)
- `--include-filled`: Include entries that already have citation values
- `--output FILE`: Specify output file (default: overwrite input)

**Note**: Entries with existing non-empty citation values are automatically skipped unless `--include-filled` is used.

### PDF library alignment — `utils/librarian.py`

Unified tool for aligning your PDF library with your bibliography. Supports three modes:

```bash
# Find bib entries missing from your PDF library
python utils/librarian.py missing input.bib papers.txt

# Find library PDFs not referenced in bib
python utils/librarian.py extra input.bib papers.txt

# Rename new PDFs to bib keys via title matching (preview)
python utils/librarian.py rename input.bib ~/Downloads/papers --dry-run

# Apply renames
python utils/librarian.py rename input.bib ~/Downloads/papers
```

**Subcommands**:

- `missing` — Lists bib entries whose citation keys are absent from the library listing
- `extra` — Lists PDFs in the library that have no corresponding bib entry
- `rename` — Matches PDFs to bib entries by normalised title and renames to `<citation_key>.pdf`

**Rename workflow**: Export PDFs from Zotero (or similar) with full titles in the filename (e.g., `Author 等 - 2025 - Full Paper Title.pdf`). The tool extracts the title from the filename, normalises it, and matches it against bib entry titles for exact renaming — no manual ordering required.

**Output files** (automatically generated):

- `<bib_file>.missing_pdfs.txt` — Full bib entries for missing PDFs
- `<bib_file>.extra_pdfs.txt` — Library PDFs not in bib
- `<bib_file>.rename_report.txt` — Rename mapping (matched and unmatched)
- `logs/<bib_file>.librarian.log` — Execution log

### Retrieve titles — `utils/titleretriever.py`

Check paper titles against external sources (CrossRef, DBLP, Semantic Scholar, arXiv):

```bash
python utils/titleretriever.py input.bib
```

**Output files** (automatlically generated):

- `<bib_file>.title_report.txt` - Title verification report
- `<bib_file>.titleretriever.log` - Execution log

**Options**:

- `--delay 0.5`: Delay between API requests (default: 0.5s)
- `--quiet`: Suppress progress output
- `--retry-errors <report>`: Re-check only failed entries from previous report
- `--ids ID1,ID2`: Check specific entries only

## 🧾 Template Types

### Journal Templates (year-agnostic)

```python
JOURNAL_TEMPLATES = {
    "IEEE Transactions on Image Processing": {
        "publisher": "IEEE",
        "issn": "1941-0042",
    },
}
```

Journals have consistent metadata across all years, so they're keyed by name only.

### Proceedings Templates (year-specific)

```python
PROCEEDINGS_TEMPLATES = {
    ("2024 IEEE/CVF CVPR", "2024"): {
        "venue": "Seattle, WA, USA",
        "publisher": "IEEE",
        "month": "June",
        "isbn": "...",
    },
}
```

Proceedings/conferences have year-specific details (venue location, ISBN, editors).

## 🔧 Common Fields Reference

| Field       | Journals   | Proceedings   |
| ----------- | ---------- | ------------- |
| `publisher` | ✅         | ✅            |
| `issn`      | ✅         | Sometimes     |
| `address`   | Optional   | Optional      |
| `venue`     | ❌         | ✅ (location) |
| `month`     | ❌         | ✅            |
| `isbn`      | ❌         | ✅            |
| `editor`    | ❌         | Sometimes     |
| `series`    | ❌         | Sometimes     |

## 🔗 Additional Resources

The modified `.bib` file is not guaranteed to be well formatted. Use:

- [**BibTex Tidy**](https://flamingtempura.github.io/bibtex-tidy/) for final formatting
- VS Code's LaTeX Workshop extension

## 📋 TODO

- `Completer.py` & `yaml2templates.py`:
  - [ ] Integrate `Completer.py` with `yaml2templates.py` for unified template management workflow.
  - [ ] Add auto guessing for fields able to be inferred from journal/conference names or existing templates (e.g., publisher, issn) when creating new templates.
  - [ ] Improve the `.yaml` generation by initializing fields from existing bibliographies in the same journal/conference to avoid manual filling for each field.
- `checker.py` & `templates.py` & `titlecases.py`:
  - [ ] Add citation key legibility check (METHOD_AUTHOR_VENUEWITHYEAR).
  - [ ] Add template-specific missing fields check (e.g., parts for ECCV, editor for some conferences, etc.)
  - [ ] Improve the robustness of brackets quotation checking (e.g., skip single numbers, NER for names, etc.)
  - [ ] Improve the robustness of title case checking (e.g., hyphenated words, some other cases, etc.)
  - [ ] Enable interactive application of title case suggestions and fine-grained control over which patterns to apply title case to (e.g., only the hyphenated words and ignore the rest like conjunctions, prepositions, etc.)
  - [ ] Optimizing the code structure: encapsulate each checking into sub-checker and let the `checker.py` call each of them for better modularity and maintainability.
- `utils`:
  - [x] ~~Integrate `pdfrenamer.py` with `missingfinder.py` to support unified alignment between PDF library and bibliography, and refactor to `librarian.py`.~~ Done — `librarian.py` supports: missing, extra, and title-based rename.
  - [ ] Intergrate `citer.py` with `titleretriever.py` to support unified web searching and adapt it to `scholar.py`, which can search both the citation numbers and the original titles of bibliographies by fetching from API or openning web search result pages.
  - [ ] To support bibliographies organized in folders, for simplicity, add `composer.py` to extract bibliographies recursively from the folder into a single `.bib` file for the tools to process, where comments specifying the source file path are inserted as separators between bibliographies from different files *and the `composer.py` can also be used to split the composed `.bib` file back into multiple files by the source file path comments after processing.* All original comments in each `.bib` file must be preserved during the composition and decomposition. **Note that the decomposition implementation can be skipped for now since the composition is important for deduplication while the decomposition can be easily done manually.**
- Further improvements:
  - [ ] Package all stuffs into a CLI tool for distribution.
  - [ ] Unify the output's formatting and storage (both logs and report files.)
