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
└── titlecases.py         # Title case utilities
```

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

- Add NER to `checker.py` for advacned brackets quotation need detection for names over static vocab.
- Improve the robustness of title case formatting.
