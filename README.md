# BibCompletion (Under Development)

## File Explain

- **`main.py`**: The core tool. It reads a source `.bib` file, matches entries against predefined templates in `templates.py`, and fills in missing fields (e.g., address, month, publisher) into a new output file.
  - Usage: `python main.py input.bib output.bib`

- **`checker.py`**: Unified validation tool. Checks missing fields, Title Case, and smart protection for technical terms.
  - Missing fields: `python checker.py input.bib --fields month,publisher --entry-types inproceedings,article`
  - Title Case (APA default): `python checker.py input.bib --title-case --title-style apa`
  - Smart protection (quoting): `python checker.py input.bib --quote --quote-terms Gaussian,Kalman --quote-vocab-file my_terms.txt`

- **`titlecase_checker.py`**: Standalone Title Case checker (shares logic with checker). Default style: **APA** (first word, words ≥4 letters, major words, and all parts of hyphenated major words like `Class-Incremental`). Usage: `python titlecase_checker.py input.bib --style apa`

- **`quoter.py`**: Thin wrapper to run only the smart-protection scan (uses the unified checker logic).
  - Usage: `python quoter.py input.bib --terms Gaussian,Kalman` or `--vocab-file my_terms.txt`

- **`calculator.py`**: A helper tool to analyze a `.bib` file and list all unique (Venue, Year) combinations. It helps identify which venues are missing from your `templates.py`.
  - Usage: `python calculator.py input.bib`

- **`bib2py.py`**: A utility script to convert raw BibTeX entries into the Python dictionary format required for `templates.py`. Useful for bulk-adding new templates.
  - Usage: `python bib2py.py input.bib`

## TODO

1. Complete Readme
2. Refine Project Structure
3. Add more annotations
4. Support commandline arg. parsing
5. Support more general functionality
6. Refine the code including unifying variable names, unifying string formatting, etc.
7. Pack all things up
8. Support web claw or LLM assisting template completion
