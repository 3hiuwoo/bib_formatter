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
    ├── citationimporter.py # Import citation counts from Google Scholar
    ├── missingfinder.py    # Find PDFs missing from library
    ├── pdfrenamer.py       # Batch rename PDFs to match bib keys
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
| `citationimporter.py` | `.scholar_urls.txt` | `.citationimporter.log` |
| `missingfinder.py` | `.missing_pdfs.txt`, `.extras_in_library.txt`, `.dups_in_library.txt` | `.missingfinder.log` |
| `pdfrenamer.py` | — | `.pdfrenamer.log` |
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

### Import citation counts — `utils/citationimporter.py`

Manually import citation counts from Google Scholar with browser automation:

```bash
# Preview mode - show entries needing citations
python utils/citationimporter.py input.bib

# Interactive mode - open URLs one by one and prompt for citation count
python utils/citationimporter.py input.bib --interactive

# Batch mode - open URLs in browser tabs (5 at a time)
python utils/citationimporter.py input.bib --open

# Include entries that already have citations (for updating)
python utils/citationimporter.py input.bib -i --include-filled
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

### Find missing PDFs — `utils/missingfinder.py`

Compare bib entries with your PDF library to find papers you need to download:

```bash
python utils/missingfinder.py input.bib papers.txt
```

- `bib_file`: Path to your .bib file
- `papers_file`: Directory listing of your PDF library (e.g., output of `ls` or `dir`)

**Output files** (automatically generated):

- `<bib_file>.missing_pdfs.txt` - Bib entries without PDFs
- `<bib_file>.extras_in_library.txt` - PDFs not in bib
- `<bib_file>.dups_in_library.txt` - Duplicate PDF groups
- `<bib_file>.missingfinder.log` - Execution log

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

### Batch rename PDFs — `utils/pdfrenamer.py`

Rename downloaded PDFs to match bib keys based on temporal download order:

```bash
# Preview renames (no changes)
python utils/pdfrenamer.py missing_pdfs.txt ~/Downloads/papers --dry-run

# Apply renames
python utils/pdfrenamer.py missing_pdfs.txt ~/Downloads/papers
```

- `report`: Path to the missing PDFs report (from `missingfinder.py`)
- `pdf_folder`: Folder containing downloaded PDFs
- `--dry-run`: Preview renames without applying

**Workflow**: Download PDFs in the same order as listed in the report, then run the renamer to batch rename them to match bib keys.

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

- [ ] Add NER to `checker.py` for advacned brackets quotation need detection for names over static vocab.
- [ ] Improve the robustness of title case formatting.
