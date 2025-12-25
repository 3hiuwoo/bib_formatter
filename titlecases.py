import argparse
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import bibtexparser


@dataclass
class TitleCaseStyle:
    name: str
    stopwords: Set[str]
    min_length_capitalize: int = 4
    capitalize_last_word: bool = False  # APA does not require last word specifically
    hyphen_capitalize_all_parts: bool = True  # APA: Self-Report, Class-Incremental
    subtitle_delimiters: Optional[Set[str]] = (
        None  # e.g., ':' or '—' introduce subtitle
    )


APA_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "from",
    "in",
    "into",
    "nor",
    "of",
    "on",
    "onto",
    "or",
    "over",
    "per",
    "the",
    "to",
    "vs",
    "via",
    "with",
    "up",
    "down",
    "off",
}


STYLES: Dict[str, TitleCaseStyle] = {
    "apa": TitleCaseStyle(
        name="apa",
        stopwords=APA_STOPWORDS,
        min_length_capitalize=4,
        capitalize_last_word=False,
        hyphen_capitalize_all_parts=True,
        subtitle_delimiters={":", "—", "–", "—"},
    ),
    # Placeholder for future styles; extend as needed.
}


def get_style(name: Optional[str]) -> TitleCaseStyle:
    if not name:
        return STYLES["apa"]
    return STYLES.get(name.lower(), STYLES["apa"])


# Backward-compat exposed default stopwords (APA)
DEFAULT_STOPWORDS = APA_STOPWORDS


def _split_tokens_preserve_space(text: str) -> List[str]:
    # Split and preserve whitespace separators
    return re.split(r"(\s+)", text)


def _titlecase_hyphenated(
    core: str,
    force_capitalize: bool,
    stopwords: Set[str],
    style: TitleCaseStyle,
) -> str:
    # Title-case each hyphen-separated segment individually
    parts = core.split("-")
    cased_parts = []
    for i, part in enumerate(parts):
        lower_part = part.lower()
        clean_part = re.sub(r"[^A-Za-z0-9]", "", part)
        part_major = force_capitalize or style.hyphen_capitalize_all_parts
        part_major = part_major or (len(clean_part) >= style.min_length_capitalize)
        part_major = part_major or (lower_part not in stopwords)

        if part.isupper():
            cased = part  # keep acronyms
        elif part_major:
            cased = part.capitalize()
        else:
            cased = lower_part
        cased_parts.append(cased)
    return "-".join(cased_parts)


def _titlecase_word(
    word: str,
    force_capitalize: bool,
    stopwords: Set[str],
    style: TitleCaseStyle,
) -> str:
    if not word:
        return word

    # Preserve leading/trailing punctuation
    match = re.match(r"(^[^A-Za-z0-9]*)(.*?)([^A-Za-z0-9]*$)", word)
    if not match:
        return word

    prefix, core, suffix = match.groups()
    if not core:
        return word

    lower_core = core.lower()
    clean_core = re.sub(r"[^A-Za-z0-9]", "", core)

    is_major = force_capitalize
    is_major = is_major or (len(clean_core) >= style.min_length_capitalize)
    is_major = is_major or (lower_core not in stopwords)

    if "-" in core:
        cased_core = _titlecase_hyphenated(core, is_major, stopwords, style)
    else:
        if core.isupper():
            cased_core = core  # keep acronyms
        elif is_major:
            cased_core = core.capitalize()
        else:
            cased_core = lower_core

    return f"{prefix}{cased_core}{suffix}"


def suggest_title_case(
    title: str,
    stopwords: Optional[Set[str]] = None,
    style_name: str = "apa",
) -> str:
    style = get_style(style_name)
    stopwords = stopwords or style.stopwords

    # Protect braced segments (keep as-is)
    parts = []
    last = 0
    for m in re.finditer(r"\{.*?\}", title):
        if m.start() > last:
            parts.append(("text", title[last : m.start()]))
        parts.append(("braced", m.group()))
        last = m.end()
    if last < len(title):
        parts.append(("text", title[last:]))

    # Flatten tokens across all text segments to know first/last word positions
    word_positions: List[Tuple[int, str]] = []  # (global_index, word)
    for kind, segment in parts:
        if kind != "text":
            continue
        tokens = [t for t in _split_tokens_preserve_space(segment) if t.strip()]
        for tok in tokens:
            if tok.isspace() or not re.search(r"[A-Za-z0-9]", tok):
                continue
            word_positions.append((len(word_positions), tok))

    total_words = len(word_positions)

    def is_first_or_last(idx: int) -> bool:
        if idx == 0:
            return True
        if style.capitalize_last_word and idx == total_words - 1:
            return True
        return False

    # Rebuild with title-cased text parts
    rebuilt_parts: List[str] = []
    word_counter = 0
    prev_token_nonspace = ""
    for kind, segment in parts:
        if kind == "braced":
            rebuilt_parts.append(segment)
            continue
        tokens = _split_tokens_preserve_space(segment)
        new_tokens = []
        for tok in tokens:
            if tok.isspace() or not tok:
                new_tokens.append(tok)
                continue

            # APA: capitalize first word and word after subtitle delimiter (e.g., colon/em dash)
            prev_delim = bool(
                prev_token_nonspace.rstrip().endswith(
                    tuple(style.subtitle_delimiters or [])
                )
            )
            force = is_first_or_last(word_counter) or prev_delim

            new_tok = _titlecase_word(tok, force, stopwords, style)
            new_tokens.append(new_tok)
            prev_token_nonspace = tok
            word_counter += 1
        rebuilt_parts.append("".join(new_tokens))

    return "".join(rebuilt_parts)


def check_title_case(
    input_path: str,
    stopwords: Optional[Set[str]] = None,
    style_name: str = "apa",
) -> None:
    style = get_style(style_name)
    stopwords = stopwords or set(style.stopwords)

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            bib_db = bibtexparser.load(f, parser=parser)
    except FileNotFoundError:
        print(f"❌ Error: File '{input_path}' not found.")
        return

    print(f"📝 Checking Title Case for {input_path}\n")
    print(f"{'ID':<40} | {'Issue':<40} | Suggestion")
    print("-" * 95)

    issues = 0
    for entry in bib_db.entries:
        title = entry.get("title")
        if not title:
            continue

        suggestion = suggest_title_case(title, stopwords, style_name)

        # Compare ignoring extra whitespace
        normalized_orig = " ".join(title.split())
        normalized_sugg = " ".join(suggestion.split())

        if normalized_orig != normalized_sugg:
            issues += 1
            print(f"{entry.get('ID', ''):<40} | {title:<40} | {suggestion}")

    print("-" * 95)
    if issues == 0:
        print(
            "✅ All titles already appear to be in Title Case (with stopword handling)."
        )
    else:
        print(f"⚠️  Found {issues} titles that could be normalized.")
