#!/usr/bin/env python3
"""
BibCC — BibTeX Check & Complete CLI.

Unified command-line interface for the BibCC toolkit.  Every tool is exposed
as a subcommand so that the entire workflow can be driven from one entry point.

Subcommands:
    check      Quality checks (missing fields, title case, term protection, …)
    complete   Auto-fill missing BibTeX fields from templates
    librarian  Align a PDF library with a .bib file (missing / extra / rename)
    scholar    Citation counts and title verification via external APIs
    compose    Merge per-folder .bib files into a single bibliography

Usage:
    python bibcc.py check input.bib --fields month --title-case
    python bibcc.py complete input.bib --output out.bib
    python bibcc.py librarian missing input.bib papers.txt
    python bibcc.py scholar cite input.bib
    python bibcc.py scholar titles input.bib
    python bibcc.py compose compose ./bibs combined.bib
"""

from __future__ import annotations

import sys


TOOLS = {
    "check": "Quality checks: missing fields, title case, term protection, keys",
    "complete": "Auto-fill missing BibTeX fields from templates",
    "librarian": "Align PDF library with .bib: missing / extra / rename",
    "scholar": "Citation counts and title verification via external APIs",
    "compose": "Merge per-folder .bib files into a single bibliography",
}


def _print_usage() -> None:
    """Print top-level usage information."""
    print("usage: bibcc <tool> [args ...]\n")
    print("BibCC — BibTeX Check & Complete toolkit.\n")
    print("Available tools:")
    for name, desc in TOOLS.items():
        print(f"  {name:<12} {desc}")
    print(f"\nRun 'bibcc <tool> -h' for tool-specific help.")


def _cli() -> None:
    """Parse the first positional arg as a tool name and delegate."""
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        _print_usage()
        sys.exit(0)

    tool = sys.argv[1]

    if tool not in TOOLS:
        print(f"bibcc: unknown tool '{tool}'")
        _print_usage()
        sys.exit(1)

    # Strip 'bibcc <tool>' so the delegated parser sees its own argv
    sys.argv = [f"bibcc {tool}"] + sys.argv[2:]

    if tool == "check":
        from checker import build_parser, run

        parser = build_parser()
        args = parser.parse_args()
        run(args)

    elif tool == "complete":
        from completer import build_parser, run

        parser = build_parser()
        args = parser.parse_args()
        run(args)

    elif tool == "librarian":
        from utils.librarian import main as librarian_main

        librarian_main()

    elif tool == "scholar":
        from utils.scholar import main as scholar_main

        scholar_main()

    elif tool == "compose":
        from utils.composer import main as composer_main

        composer_main()


if __name__ == "__main__":
    _cli()
