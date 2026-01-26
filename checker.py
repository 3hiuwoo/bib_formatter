"""
BibTeX Quality Checker.

This module provides quality checking for BibTeX files:
- Missing field detection (e.g., month, publisher)
- Title case validation with APA-style rules
- Smart protection suggestions for technical terms and acronyms
- Template completeness checking

Usage:
    # Check for missing fields
    python checker.py input.bib --fields month,publisher

    # Check title case
    python checker.py input.bib --title-case

    # Suggest brace protection for terms
    python checker.py input.bib --quote --quote-terms Gaussian,BERT

    # Check template completeness
    python checker.py --check-templates
"""

import argparse
import re
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import bibtexparser

from logging_utils import Logger, get_repo_dir
from titlecases import DEFAULT_STOPWORDS, check_title_case, get_style


def _write_report(path: Path, header: str, rows: List[str]) -> None:
    """Write a simple report file with header and rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = [header]
    content.extend(rows if rows else ["(none)"])
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


# ---------- Bib file checking ----------
DEFAULT_ENTRY_TYPES = ["inproceedings", "article", "proceedings", "conference"]
# DEFAULT_REQUIRED_FIELDS = ["month"]

DEFAULT_VOCAB = {
    "gaussian",
    "bayesian",
    "markov",
    "poisson",
    "fourier",
    "laplace",
    "euler",
    "kalman",
    "kolmogorov",
    "newton",
    "hamilton",
    "lagrange",
    "riemann",
    "hilbert",
    "bessel",
    "hadamard",
    "chernoff",
    "hoeffding",
    "chebyshev",
    "bernoulli",
    "dirichlet",
    "fisher",
    "neyman",
    "cauchy",
    "boltzmann",
    "gibbs",
    "wiener",
    "ito",
    "lévy",
    "levy",
    "gram",
    "schmidt",
    "heaviside",
    "noether",
    "poincaré",
    "weibull",
    "rayleigh",
    "shannon",
    "huffman",
    "turing",
    "Kronecker",
    "arnold",
}


def parse_list_arg(raw: str) -> List[str]:
    """Parse a comma-separated string into a list of stripped items."""
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_vocab_file(path: Path) -> Set[str]:
    """Load vocabulary terms from a newline-delimited file."""
    vocab: Set[str] = set()
    if not path.exists():
        print(f"⚠️  Vocab file '{path}' not found; skipping.")
        return vocab
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            term = line.strip()
            if term:
                vocab.add(term.lower())
    return vocab


def parse_terms(raw: str) -> List[str]:
    """Parse a comma-separated string of terms into a list."""
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def check_missing_fields(
    input_path: str,
    required_fields: Sequence[str],
    target_types: Sequence[str],
    log: Optional[Callable[[str], None]] = None,
) -> List[Tuple[str, str, str, List[str]]]:
    """Check for missing fields and return the results."""
    log = log or print
    required_fields = [f.strip() for f in required_fields if f.strip()]
    if not required_fields:
        log("ℹ️  No required fields specified, skipping missing-field check.")
        return []

    log(f"🔍 Scanning {input_path} for missing fields: {', '.join(required_fields)}\n")

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            bib_db = bibtexparser.load(f, parser=parser)
    except FileNotFoundError:
        log(f"❌ Error: File '{input_path}' not found.")
        return []

    missing_rows: List[Tuple[str, str, str, List[str]]] = []

    log(f"{'ID':<40} | {'Type':<15} | {'Year':<6} | Missing")
    log("-" * 95)

    for entry in bib_db.entries:
        entry_type = entry.get("ENTRYTYPE", "").lower()
        if entry_type not in target_types:
            continue

        missing = [
            field for field in required_fields if not entry.get(field, "").strip()
        ]
        if missing:
            missing_rows.append(
                (entry.get("ID", ""), entry_type, entry.get("year", "N/A"), missing)
            )

    for row in missing_rows:
        rid, rtype, ryear, rmiss = row
        log(f"{rid:<40} | {rtype:<15} | {ryear:<6} | {', '.join(rmiss)}")

    log("-" * 95)
    if not missing_rows:
        log("✅ Perfect! All target entries contain the required fields.")
    else:
        field_counts = {f: 0 for f in required_fields}
        for _, _, _, miss in missing_rows:
            for f in miss:
                field_counts[f] += 1
        summary = "; ".join([f"{k}: {v}" for k, v in field_counts.items()])
        log(
            f"⚠️  Found {len(missing_rows)} entries missing fields. Breakdown -> {summary}"
        )

    return missing_rows


def check_smart_protection(
    input_path: str,
    extra_vocab: Iterable[str],
    use_default_vocab: bool = True,
    log: Optional[Callable[[str], None]] = None,
) -> List[Tuple[str, str, str]]:
    """Check for unprotected terms and return the results."""
    log = log or print
    log(f"🧠 Smart-Scanning {input_path} for unprotected terms...\n")

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            bib_db = bibtexparser.load(f, parser=parser)
    except FileNotFoundError:
        log(f"❌ Error: File '{input_path}' not found.")
        return []

    protection_rows: List[Tuple[str, str, str]] = []  # (entry_id, word, reason)

    regex_mixed = r"\b(?:[a-z]+[A-Z][a-zA-Z]*)|(?:[A-Z][a-z]*[A-Z][a-zA-Z]*)\b"
    regex_allcaps = r"\b[A-Z]{2,}\b"
    regex_numeric = r"\b[A-Za-z]*\d+[A-Za-z0-9\-]*\b"

    log(f"{'ID':<30} | {'Suspicious Word':<20} | {'Reason'}")
    log("-" * 75)

    vocab_terms = set(DEFAULT_VOCAB) if use_default_vocab else set()
    vocab_terms.update([t.lower() for t in extra_vocab])

    for entry in bib_db.entries:
        title = entry.get("title")
        if not title:
            continue

        clean_title = re.sub(r"\{.*?\}", lambda x: " " * len(x.group()), title)

        if sum(1 for c in clean_title if c.isupper()) / max(len(clean_title), 1) > 0.7:
            continue

        found_issues = []

        for match in re.finditer(regex_mixed, clean_title):
            found_issues.append((match.group(), "Mixed Case"))

        for match in re.finditer(regex_allcaps, clean_title):
            found_issues.append((match.group(), "Acronym"))

        for match in re.finditer(regex_numeric, clean_title):
            found_issues.append((match.group(), "Contains Number"))

        for term in vocab_terms:
            pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)
            for match in pattern.finditer(clean_title):
                found_issues.append((match.group(), "Vocabulary"))

        unique_issues = {}
        for word, reason in found_issues:
            is_substring = False
            for existing in list(unique_issues.keys()):
                if word in existing and word != existing:
                    is_substring = True
                elif existing in word and existing != word:
                    del unique_issues[existing]

            if not is_substring:
                unique_issues[word] = reason

        for word, reason in unique_issues.items():
            log(f"{entry['ID']:<30} | {word:<20} | {reason}")
            protection_rows.append((entry["ID"], word, reason))

    log("-" * 75)
    if protection_rows:
        log(f"⚠️  Found {len(protection_rows)} terms to protect.")

    return protection_rows


# ------------- Template checking ----------
# Default required fields for template checking
DEFAULT_JOURNAL_FIELDS = ["publisher", "issn"]
DEFAULT_PROCEEDINGS_FIELDS = ["venue", "publisher", "month"]


def check_template_fields(
    templates_path: Path,
    journal_fields: Sequence[str],
    proceedings_fields: Sequence[str],
    log: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Check templates for missing fields.

    This helps maintain consistency across templates by identifying
    which templates are missing certain expected fields.
    """
    log = log or print
    import importlib.util

    # Load templates module
    spec = importlib.util.spec_from_file_location("templates", templates_path)
    if spec is None or spec.loader is None:
        log(f"❌ Error: Cannot load templates from {templates_path}")
        return

    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        log(f"❌ Error loading templates: {e}")
        return

    journal_templates: Dict[str, Dict] = getattr(mod, "JOURNAL_TEMPLATES", {})
    proceedings_templates: Dict[Tuple[str, str], Dict] = getattr(
        mod, "PROCEEDINGS_TEMPLATES", {}
    )

    log(f"🔍 Checking templates in {templates_path}")
    log(f"   Journal fields to check: {', '.join(journal_fields)}")
    log(f"   Proceedings fields to check: {', '.join(proceedings_fields)}")
    log("")

    # Check journals
    journal_issues = []
    if journal_fields:
        log(f"{'Journal Name':<60} | Missing Fields")
        log("-" * 90)

        for name, fields in sorted(journal_templates.items()):
            missing = [f for f in journal_fields if f not in fields or not fields[f]]
            if missing:
                journal_issues.append((name, missing))
                log(f"{name[:60]:<60} | {', '.join(missing)}")

        log("-" * 90)
        if journal_issues:
            log(
                f"⚠️  {len(journal_issues)}/{len(journal_templates)} journals have missing fields"
            )
        else:
            log(f"✅ All {len(journal_templates)} journals have required fields")

    log("")

    # Check proceedings
    proceedings_issues = []
    if proceedings_fields:
        log(f"{'Proceedings (Venue, Year)':<70} | Missing Fields")
        log("-" * 100)

        # Sort by year descending
        sorted_procs = sorted(
            proceedings_templates.items(),
            key=lambda x: (-int(x[0][1]) if x[0][1].isdigit() else 0, x[0][0]),
        )

        for (venue, year), fields in sorted_procs:
            missing = [
                f for f in proceedings_fields if f not in fields or not fields[f]
            ]
            if missing:
                proceedings_issues.append(((venue, year), missing))
                display = f"({venue[:50]}, {year})"
                log(f"{display:<70} | {', '.join(missing)}")

        log("-" * 100)
        if proceedings_issues:
            log(
                f"⚠️  {len(proceedings_issues)}/{len(proceedings_templates)} proceedings have missing fields"
            )
        else:
            log(f"✅ All {len(proceedings_templates)} proceedings have required fields")

    # Summary by field
    log("\n📊 Summary by field:")

    if journal_fields:
        log("\n  Journals:")
        for field in journal_fields:
            count = sum(
                1
                for _, fields in journal_templates.items()
                if field not in fields or not fields[field]
            )
            log(f"    {field}: {count} missing")

    if proceedings_fields:
        log("\n  Proceedings:")
        for field in proceedings_fields:
            count = sum(
                1
                for _, fields in proceedings_templates.items()
                if field not in fields or not fields[field]
            )
            log(f"    {field}: {count} missing")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Unified checker for BibTeX: missing fields, title case, and smart protection."
    )
    parser.add_argument(
        "input",
        type=str,
        nargs="?",  # Make optional for --check-templates mode
        default="",
        help="Path to the input BibTeX (.bib) file",
    )
    parser.add_argument(
        "--fields",
        type=str,
        default="",
        help="Comma-separated required fields to enforce (default: month).",
    )
    parser.add_argument(
        "--entry-types",
        type=str,
        default=",".join(DEFAULT_ENTRY_TYPES),
        help="Comma-separated ENTRYTYPEs to check (default: inproceedings,article,proceedings,conference).",
    )
    parser.add_argument(
        "--title-case",
        action="store_true",
        help="Check that titles are in Title Case (APA by default).",
    )
    parser.add_argument(
        "--title-apply",
        action="store_true",
        help="Apply Title Case suggestions in-place (implies --title-case).",
    )
    parser.add_argument(
        "--title-style",
        type=str,
        default="apa",
        help="Title case style to apply (default: apa).",
    )
    parser.add_argument(
        "--extra-stopwords",
        type=str,
        default="",
        help="Comma-separated additional stopwords to keep lowercase in title-case suggestions.",
    )
    parser.add_argument(
        "--quote",
        action="store_true",
        help="Run smart protection to suggest curly braces for technical terms (merged quoter).",
    )
    parser.add_argument(
        "--quote-terms",
        type=str,
        default="",
        help="Comma-separated extra terms to protect (in addition to default vocab).",
    )
    parser.add_argument(
        "--quote-vocab-file",
        type=str,
        default=None,
        help="Optional path to newline-delimited vocabulary file of technical terms to protect.",
    )
    parser.add_argument(
        "--quote-no-default",
        action="store_true",
        help="Do not include built-in technical vocabulary when running smart protection.",
    )
    parser.add_argument(
        "--check-templates",
        action="store_true",
        help="Check templates.py for missing fields instead of a bib file.",
    )
    parser.add_argument(
        "--templates-path",
        type=str,
        default="templates.py",
        help="Path to templates.py file (default: templates.py).",
    )
    parser.add_argument(
        "--journal-fields",
        type=str,
        default=",".join(DEFAULT_JOURNAL_FIELDS),
        help=f"Comma-separated fields to check in journal templates (default: {','.join(DEFAULT_JOURNAL_FIELDS)}).",
    )
    parser.add_argument(
        "--proceedings-fields",
        type=str,
        default=",".join(DEFAULT_PROCEEDINGS_FIELDS),
        help=f"Comma-separated fields to check in proceedings templates (default: {','.join(DEFAULT_PROCEEDINGS_FIELDS)}).",
    )

    args = parser.parse_args()

    # All outputs go to repo directory
    repo_dir = get_repo_dir()
    base_name = Path(args.input).name if args.input else "templates.py"

    # Template checking mode
    if args.check_templates:
        # Create logger for template checking
        with Logger("checker", input_file=args.templates_path) as logger:
            journal_fields = parse_list_arg(args.journal_fields)
            proceedings_fields = parse_list_arg(args.proceedings_fields)
            check_template_fields(
                Path(args.templates_path),
                journal_fields,
                proceedings_fields,
                log=logger.log,
            )
        exit(0)

    # Create logger for bib file checking
    with Logger("checker", input_file=args.input) as logger:
        required_fields = parse_list_arg(args.fields)  # or DEFAULT_REQUIRED_FIELDS
        entry_types = [
            t.lower() for t in parse_list_arg(args.entry_types) or DEFAULT_ENTRY_TYPES
        ]

        # Missing fields
        missing_rows = []
        if required_fields:
            missing_rows = check_missing_fields(
                args.input, required_fields, entry_types, log=logger.log
            )
            # Write missing fields report
            if missing_rows:
                report_path = repo_dir / f"{base_name}.missing_fields.txt"
                rows = [
                    f"{rid}\t{rtype}\t{ryear}\t{', '.join(rmiss)}"
                    for rid, rtype, ryear, rmiss in missing_rows
                ]
                _write_report(
                    report_path,
                    "missing fields: entry_id\ttype\tyear\tfields",
                    rows,
                )
                logger.log(f"\n📄 Missing fields report: {report_path}")

        # Title case
        titlecase_rows = []
        if args.title_case or args.title_apply:
            logger.log("\n")
            style = get_style(args.title_style)
            stopwords = set(style.stopwords)
            stopwords.update([s.lower() for s in parse_list_arg(args.extra_stopwords)])
            titlecase_rows = check_title_case(
                args.input,
                stopwords,
                style.name,
                apply=args.title_apply,
                log=logger.log,
            )
            # Write title case report
            if titlecase_rows and not args.title_apply:
                report_path = repo_dir / f"{base_name}.title_case.txt"
                rows = [
                    f"{eid}\t{current}\t{suggested}"
                    for eid, current, suggested in titlecase_rows
                ]
                _write_report(
                    report_path,
                    "title case: entry_id\tcurrent\tsuggested",
                    rows,
                )
                logger.log(f"\n📄 Title case report: {report_path}")

        # Smart protection
        protection_rows = []
        if args.quote:
            logger.log("\n")
            extra_vocab: List[str] = []
            if args.quote_vocab_file:
                extra_vocab.extend(load_vocab_file(Path(args.quote_vocab_file)))
            extra_vocab.extend(parse_terms(args.quote_terms))
            protection_rows = check_smart_protection(
                args.input,
                extra_vocab,
                use_default_vocab=not args.quote_no_default,
                log=logger.log,
            )
            # Write smart protection report
            if protection_rows:
                report_path = repo_dir / f"{base_name}.smart_protection.txt"
                rows = [
                    f"{eid}\t{word}\t{reason}" for eid, word, reason in protection_rows
                ]
                _write_report(
                    report_path,
                    "smart protection: entry_id\tword\treason",
                    rows,
                )
                logger.log(f"\n📄 Smart protection report: {report_path}")
