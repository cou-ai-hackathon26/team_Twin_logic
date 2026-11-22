"""Check the textbook-aligned passages and write the evidence table.

    python -m scripts.curriculum_evidence            # validate + write docs/CURRICULUM_ALIGNMENT.md
    python -m scripts.curriculum_evidence --check    # validate only (exit 1 on a problem)

For every passage in app/seed/textbook_passages.json it verifies, with our own
grapheme segmenter, that each target word really occurs in the text and that
each target unit (কার, ফলা, রেফ, যুক্তাক্ষর, ৎ, ঁ) occurs at least once, then
lists the NCTB lesson and page it was aligned to.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.assessment.marking import passage_words  # noqa: E402
from app.bangla.normalize import normalize_word  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "app" / "seed" / "textbook_passages.json"
DOC = ROOT.parent / "docs" / "CURRICULUM_ALIGNMENT.md"
HASANTA = "্"
KARS = set("ািীুূৃেৈোৌ")
SIGNS = set("ঁংঃ")
BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
PDF_OFFSET = 9  # PDF page = printed page + 9 in all three supplied PDFs (checked on each book)


def kind(t: str) -> str:
    if t in KARS:
        return "কার"
    if t in SIGNS:
        return "চিহ্ন"
    if t == "ৎ":
        return "খণ্ড-ত"
    if t.startswith("র" + HASANTA):
        return "রেফ"
    cons = t.split(HASANTA)
    if len(cons) == 2 and cons[1] in ("ব", "ম", "য", "র", "ল", "ন"):
        return f"{cons[1]}-ফলা"
    return "যুক্তাক্ষর"


def count_unit(units, t: str) -> int:
    n = 0
    for u in units:
        if t in KARS:
            n += u.kar == t
        elif t in SIGNS:
            n += t in u.signs
        elif t == "ৎ":
            n += "ৎ" in u.consonants
        elif t.startswith("র" + HASANTA):
            n += u.reph and u.consonants[:1] == (t[2],)
        else:
            n += u.consonants == tuple(t.split(HASANTA))
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    data = json.loads(SEED.read_text(encoding="utf-8"))
    problems, rows, totals = [], [], Counter()
    for p in data:
        pw = passage_words(p["text"])
        words = [w.norm for w in pw]
        units = [u for w in pw for u in w.units]
        missing = [w for w in p["targets"]["words"] if normalize_word(w) not in words]
        counts = {t: count_unit(units, t) for t in p["targets"]["units"]}
        zero = [t for t, c in counts.items() if c == 0]
        if missing:
            problems.append(f"{p['code']}: target words not in text: {missing}")
        if zero:
            problems.append(f"{p['code']}: target units not in text: {zero}")
        for t, c in counts.items():
            totals[kind(t)] += c
        rows.append((p, len(words), counts))
    for msg in problems:
        print("PROBLEM", msg)
    print(f"{len(data)} passages checked, {len(problems)} problems")
    if args.check or problems:
        sys.exit(1 if problems else 0)

    md = [
        "# Curriculum alignment: passages and NCTB textbooks",
        "",
        "PoraBondhu's error categories (কার, ফলা, রেফ, যুক্তাক্ষর) are the same units the national",
        "Bangla textbooks teach, in the same order. The passages `T01`-`T12` were **written by the team**",
        "(with AI help, see the README) to practise exactly the units and words of specific lessons in",
        "*আমার বাংলা বই* (NCTB, Grades 1-3, 2025 reprint). The textbook text itself is **not copied**;",
        "only the lesson, its target letters and its single practice words are used, and each passage",
        "cites the printed page so a teacher can open the book next to it.",
        "",
        "Generated and checked by `python -m scripts.curriculum_evidence` (every target word and unit",
        "is verified with our own grapheme segmenter).",
        "",
        "## Where the textbooks teach each unit",
        "",
        "| Grade | Lesson (printed page) | What it teaches | PoraBondhu error category |",
        "|---|---|---|---|",
        "| 1 | পাঠ ২১-৩১ (pp. 30-44) | আ-কার … ঔ-কার, one per lesson | কার |",
        "| 2 | পাঠ ৭ কারচিহ্ন দিয়ে শব্দ বানাই (p. 16) | joining কার to letters | কার |",
        "| 2 | পাঠ ১০ যুক্তবর্ণ শিখি (p. 21) | ল্গ, স্ক, ন্ধ, ন্দ, ণ্ট, স্ত, ন্ন, ষ্ক | যুক্তাক্ষর |",
        "| 2 | পাঠ ১২ ফলাচিহ্ন শিখি (pp. 23-26) | ব-ফলা, ম-ফলা, য-ফলা, র-ফলা | ফলা |",
        "| 2 | পাঠ ১৩ রেফ চিনি (p. 27) | র্চ, র্ণ, র্য | রেফ |",
        "| 3 | পাঠ ৪ আবার পড়ি কারচিহ্ন (pp. 12-14) | ৃ, ে, ৈ, ো, ৌ review | কার |",
        "| 3 | পাঠ ৫ আবার পড়ি ফলাচিহ্ন (pp. 15-18) | দ্ব, স্ব, শ্ব, স্ম, দ্ম, ত্ম review | ফলা |",
        "",
        "## Passages",
        "",
        "| Code | Grade | Title | Words | Aligned lesson | Printed page (PDF page) | Target units (count in text) | Target words |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for p, n_words, counts in rows:
        s = p["source"]
        pages = ", ".join(f"{str(pg).translate(BN_DIGITS)} ({pg + PDF_OFFSET})" for pg in s["pages"])
        units = ", ".join(f"{t} ×{c}" for t, c in counts.items())
        md.append(f"| {p['code']} | {p['grade']} | {p['title']} | {n_words} | {'; '.join(s['lessons'])} | "
                  f"{pages} | {units} | {', '.join(p['targets']['words'])} |")
    md += [
        "",
        "## Totals across T01-T12",
        "",
        "| Category | Occurrences of target units |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in sorted(totals.items(), key=lambda kv: -kv[1])],
        "",
        "## Sources",
        "",
        "* *আমার বাংলা বই, প্রথম শ্রেণি*, জাতীয় শিক্ষাক্রম ও পাঠ্যপুস্তক বোর্ড (NCTB), পরিমার্জিত সংস্করণ অক্টোবর ২০২৪, পুনর্মুদ্রণ সেপ্টেম্বর ২০২৫.",
        "* *আমার বাংলা বই, দ্বিতীয় শ্রেণি*, NCTB, পরিমার্জিত সংস্করণ অক্টোবর ২০২৪, পুনর্মুদ্রণ সেপ্টেম্বর ২০২৫.",
        "* *আমার বাংলা বই, তৃতীয় শ্রেণি*, NCTB, পরিমার্জিত সংস্করণ অক্টোবর ২০২৪, পুনর্মুদ্রণ সেপ্টেম্বর ২০২৫.",
        "",
        "The books are distributed free by the Government of Bangladesh; all rights are reserved by NCTB,",
        "which is why only lesson references and single practice words are used here.",
        "",
    ]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(md), encoding="utf-8")
    print("wrote", DOC)


if __name__ == "__main__":
    main()
