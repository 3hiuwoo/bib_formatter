# Bib Formatter

Small BibTeX utility toolkit to auto-complete missing fields, check formatting quality, and maintain reusable templates.

## Quick start

```bash
pip install bibtexparser
```

### 1. Complete missing fields — `completer.py`

- Preview only (no write-back, logs are still generated):

  ```bash
  python completer.py input.bib
  ```

- Write completed output (overwrites the given output path) and generate logs:

  ```bash
  python completer.py input.bib --output output.bib
  ```

- Choose a log directory: `--log-dir logs/` (default current directory, outputs `*.conflicts.txt` and `*.missing_templates.txt`).

### 2. Quality checks — `checker.py`

- Missing-field check (default entry types: inproceedings, article, proceedings, conference):

  ```bash
  python checker.py input.bib --fields month,publisher
  ```

- Title Case suggestions (APA style by default, change with `--title-style apa`):

  ```bash
  python checker.py input.bib --title-case --title-style apa
  ```

- Smart protection for technical terms (suggest braces), with optional custom vocab:

  ```bash
  python checker.py input.bib --quote --quote-terms Gaussian,Kalman --quote-vocab-file my_terms.txt
  # To skip built-in vocab, add --quote-no-default
  ```

### 3. Maintain the template library — `bib2py.py`

- Generate template snippets from a `.bib` file (print only, do not write):

  ```bash
  python bib2py.py new_confs.bib
  ```

- Merge into `templates.py` directly (sorted by year descending, auto-creates a `.bak` backup):

  ```bash
  python bib2py.py new_confs.bib --update --templates-path templates.py
  ```

## Suggested workflow

1. Run `completer.py input.bib --output completed.bib` to fill missing fields using existing templates and inspect conflict/missing-template logs.
2. Run `checker.py` to:
   - `--fields` find required-field gaps;
   - `--title-case` get Title Case suggestions;
   - `--quote` spot technical terms needing braces.
3. When you encounter new venue/year combos, gather them into a separate `.bib` and run `bib2py.py --update` to refresh `templates.py` for future reuse.

## Templates

- Main templates live in `templates.py`, keyed by `(venue, year)` with a dict of fields to fill.
- The `templates/` folder holds historical/backup `.bib` files for reference.

Feel free to extend templates and vocab to match your bibliography!
