"""Build an evaluation set from REAL human Bangla speech (Google FLEURS, bn_in).

    python -m scripts.make_public_set --raw data/eval_fleurs/raw --out data/eval_fleurs \
        --tune 120 --test 300

FLEURS (CC BY 4.0, https://huggingface.co/datasets/google/fleurs) has native
speakers reading Wikipedia sentences. They read correctly, so reading errors are
created on the TEXT side (expected-text perturbation): the "passage" the system
is given differs from what the speaker actually said.

* misread  - a passage word is changed by a typical child-reading edit
             (kar swap, aspiration swap, dropped phala ...). The speaker said the
             original word, so relative to the passage they misread it.
* skipped  - a word that was never spoken is inserted into the passage.
* correct  - every other word (real human speech of exactly that word), so false
             alarms are measured on real voices.

Labels are exact by construction (no annotator is needed), but the speakers are
adults and the "errors" are simulated, so report it as "real adult speech,
simulated errors". Child speech still needs our own recordings.

The speech model (arijitx/wav2vec2-xls-r-300m-bengali) was fine-tuned on
OpenSLR-53, not on FLEURS, so this set is out-of-domain for it. FLEURS dev
speakers are used for tuning, FLEURS test speakers for testing.
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.assessment.marking import passage_words  # noqa: E402
from app.bangla.segment import segment_normalized  # noqa: E402

# Edits that change how a word SOUNDS (spelling-only pairs such as স/শ/ষ, ি/ী, ু/ূ,
# ন/ণ, জ/য are deliberately absent: PoraBondhu does not count those as errors).
EDITS = [
    ("্র", ""), ("্য", ""), ("্ব", ""), ("র্", ""),                      # dropped phala / reph
    ("ে", "া"), ("া", "ে"), ("ি", "া"), ("া", "ি"), ("ু", "া"), ("ো", "া"), ("া", "ো"), ("ে", "ি"),  # kar
    ("ধ", "দ"), ("দ", "ধ"), ("ভ", "ব"), ("ব", "ভ"), ("খ", "ক"), ("ক", "খ"), ("ঘ", "গ"), ("থ", "ত"),
    ("ত", "থ"), ("ফ", "প"), ("ট", "ত"), ("ড", "দ"), ("ছ", "চ"), ("ঝ", "জ"),       # aspiration / place
    ("ক্ষ", "ক"), ("ং", ""), ("ঁ", ""),
]
BANGLA_ONLY = re.compile(r"^[ঀ-৿\s,.;:!?।\-'\"()‘’“”]+$")
DIGITS = re.compile(r"[০-৯0-9]")


def mutate(word: str, rng: random.Random) -> tuple[str, int] | None:
    edits = EDITS[:]
    rng.shuffle(edits)
    for a, b in edits:
        hits = [m.start() for m in re.finditer(re.escape(a), word)]
        if not hits:
            continue
        pos = rng.choice(hits)
        new = word[:pos] + b + word[pos + len(a):]
        if len(new) < 2 or new == word:
            continue
        units = segment_normalized(new)
        if not units:
            continue
        p = max(pos - 1, 0) if not b else pos  # a deletion marks the unit it was removed from
        unit = next((k for k, u in enumerate(units) if u.start <= p < u.end), len(units) - 1)
        return new, unit
    return None


def read_tsv(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 7:
                continue
            rows.append({"sid": parts[0], "file": parts[1], "text": parts[2], "gender": parts[6].strip().lower()})
    return rows


def pick(rows: list[dict], n: int, rng: random.Random, per_sentence: int = 2) -> list[dict]:
    ok = [r for r in rows if BANGLA_ONLY.match(r["text"]) and not DIGITS.search(r["text"])
          and 5 <= len(passage_words(r["text"])) <= 30]
    rng.shuffle(ok)
    seen: dict[str, int] = {}
    out = []
    for r in ok:
        if seen.get(r["sid"], 0) >= per_sentence:
            continue
        seen[r["sid"]] = seen.get(r["sid"], 0) + 1
        out.append(r)
        if len(out) >= n:
            break
    return out


def build(rec: dict, split: str, audio_rel: str, filler: list[str], rng: random.Random,
          p_mis: float, p_skip: float) -> tuple[dict, list[dict]] | None:
    spoken = passage_words(rec["text"])
    passage, labels, units = [], [], {}
    for w in spoken:
        if rng.random() < p_skip:  # a never-spoken word in the passage -> skipped
            passage.append(rng.choice(filler))
            labels.append("s")
        mut = mutate(w.norm, rng) if rng.random() < p_mis else None
        if mut:
            units[len(passage)] = mut[1]
            passage.append(mut[0])
            labels.append("m")
        else:
            passage.append(w.norm)
            labels.append("c")
    text = " ".join(passage)
    pw = passage_words(text)
    if len(pw) != len(labels) or any(a.norm != b for a, b in zip(pw, passage)):
        return None  # re-tokenising changed the words; skip rather than mislabel
    rid = f"fleurs_{split}_{Path(rec['file']).stem}"
    row = {"id": rid, "audio": audio_rel, "passage": "FLEURS", "speaker": f"fleurs-{split}-{rec['gender']}",
           "group": "adult", "split": split, "condition": "clean", "human_wcpm": "",
           "human_transcript": " ".join(w.norm for w in spoken), "passage_text": text}
    # label_a/label_b stay empty: these labels are generated, not annotated by two people, so no
    # inter-annotator agreement (kappa) may be computed or reported for this set
    ann = [{"recording_id": rid, "word_index": w.index, "word": w.norm, "label_a": "", "label_b": "",
            "label": lab, "error_units": units.get(w.index, "")} for w, lab in zip(pw, labels)]
    return row, ann


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=Path("data/eval_fleurs/raw"), type=Path)
    ap.add_argument("--out", default=Path("data/eval_fleurs"), type=Path)
    ap.add_argument("--tune", type=int, default=120)
    ap.add_argument("--test", type=int, default=300)
    ap.add_argument("--p-misread", type=float, default=0.12)
    ap.add_argument("--p-skip", type=float, default=0.04)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    rec_rows, ann_rows = [], []
    for tsv_split, split, n in (("dev", "tune", args.tune), ("test", "test", args.test)):
        rows = read_tsv(args.raw / f"{tsv_split}.tsv")
        filler = sorted({w.norm for r in rows for w in passage_words(r["text"]) if len(w.norm) >= 3})
        made = 0
        for rec in pick(rows, n * 2, rng):
            wav = next((args.raw / tsv_split).rglob(rec["file"]), None)
            if wav is None:
                continue
            res = build(rec, split, str(wav.resolve()), filler, rng, args.p_misread, args.p_skip)
            if res is None:
                continue
            rec_rows.append(res[0])
            ann_rows.extend(res[1])
            made += 1
            if made >= n:
                break
        print(f"{split}: {made} recordings")
    args.out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("recordings.csv", rec_rows), ("annotations.csv", ann_rows)):
        with open(args.out / name, "w", encoding="utf-8", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wr.writeheader()
            wr.writerows(rows)
    n_lab = {k: sum(r["label"] == k for r in ann_rows) for k in "cms"}
    print(f"wrote {len(rec_rows)} recordings, word labels {n_lab} to {args.out}")


if __name__ == "__main__":
    main()
