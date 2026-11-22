"""Robustness test sets built from the FLEURS *test* speakers (never used for tuning).

    python -m scripts.make_robustness_sets --n 100

Answers three judge questions about the main FLEURS benchmark:

* unseen     - Are we only finding our own perturbations? Errors here come from families the
               detector was NOT designed around: a random consonant replaced by any other
               consonant, and a whole word replaced by a different real word.
* skipcut    - Real skips: the speaker's audio for 1-2 words is cut out (word times from
               forced alignment of the true transcript), the passage keeps the word.
* childlike  - Child-like voice: the same recordings with formant scaling (VTLP 1.08-1.20) and
               a 2-6 semitone pitch rise, labels as in the clean set (inference only, no training).
* original   - The same recordings and labels as childlike, unchanged, for a paired comparison.

Writes data/eval_robust/<family>/{recordings.csv, annotations.csv, audio/}. Labels are exact by
construction; label_a/label_b stay empty (no inter-annotator agreement exists for generated labels).
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from app.assessment.marking import passage_words  # noqa: E402
from app.bangla.segment import segment_normalized  # noqa: E402
from app.speech.audio import SR, load_audio_file, save_wav  # noqa: E402
from scripts.adapt_child_voice import pitch_shift, vtlp  # noqa: E402

CONSONANTS = list("কখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহড়ঢ়য়")
# sound-alike pairs PoraBondhu deliberately ignores; replacing one by the other is not a reading error
SAME_SOUND = [set("সশষ"), set("নণ"), set("জয"), set("তৎ"), set("ড়ঢ়")]


def same_sound(a: str, b: str) -> bool:
    return any(a in g and b in g for g in SAME_SOUND)


def random_consonant_swap(word: str, rng: random.Random) -> tuple[str, int] | None:
    pos = [i for i, ch in enumerate(word) if ch in CONSONANTS and (i == 0 or word[i - 1] != "্")]
    if not pos:
        return None
    i = rng.choice(pos)
    new_c = rng.choice([c for c in CONSONANTS if c != word[i] and not same_sound(c, word[i])])
    new = word[:i] + new_c + word[i + 1:]
    units = segment_normalized(new)
    unit = next((k for k, u in enumerate(units) if u.start <= i < u.end), 0)
    return new, unit


def write(out: Path, rec_rows: list[dict], ann_rows: list[dict]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("recordings.csv", rec_rows), ("annotations.csv", ann_rows)):
        with open(out / name, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"{out.name}: {len(rec_rows)} recordings, labels",
          {k: sum(r["label"] == k for r in ann_rows) for k in "cms"})


def ann(rid: str, pw, labels: list[str], units: dict[int, int]) -> list[dict]:
    return [{"recording_id": rid, "word_index": w.index, "word": w.norm, "label_a": "", "label_b": "",
             "label": lab, "error_units": units.get(w.index, "")} for w, lab in zip(pw, labels)]


def rec(rid: str, audio: str, transcript: str, passage_text: str) -> dict:
    return {"id": rid, "audio": audio, "passage": "FLEURS", "speaker": "fleurs-test", "group": "adult",
            "split": "test", "condition": "clean", "human_wcpm": "", "human_transcript": transcript,
            "passage_text": passage_text}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=Path("data/eval_fleurs"), type=Path)
    ap.add_argument("--out", default=Path("data/eval_robust"), type=Path)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=23)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    with open(args.src / "recordings.csv", encoding="utf-8") as f:
        src = [r for r in csv.DictReader(f) if r["split"] == "test"][: args.n]
    with open(args.src / "annotations.csv", encoding="utf-8") as f:
        src_ann: dict[str, list[dict]] = {}
        for r in csv.DictReader(f):
            src_ann.setdefault(r["recording_id"], []).append(r)
    vocab = sorted({w.norm for r in src for w in passage_words(r["human_transcript"]) if len(w.norm) >= 3})

    # ---- unseen error families (text side, real audio)
    rows, anns = [], []
    for r in src:
        spoken = passage_words(r["human_transcript"])
        passage, labels, units = [], [], {}
        for w in spoken:
            x = rng.random()
            if x < 0.07:
                m = random_consonant_swap(w.norm, rng)
                if m:
                    units[len(passage)] = m[1]
                    passage.append(m[0])
                    labels.append("m")
                    continue
            elif x < 0.12:
                other = rng.choice([v for v in vocab if v != w.norm])
                passage.append(other)  # a different real word: the speaker "misread" it as w
                labels.append("m")
                continue
            passage.append(w.norm)
            labels.append("c")
        pw = passage_words(" ".join(passage))
        if len(pw) != len(labels) or any(a.norm != b for a, b in zip(pw, passage)):
            continue
        rid = r["id"].replace("fleurs_test", "unseen")
        rows.append(rec(rid, r["audio"], r["human_transcript"], " ".join(passage)))
        anns += ann(rid, pw, labels, units)
    write(args.out / "unseen", rows, anns)

    # ---- real skips: cut the audio of 1-2 words
    from app.speech.registry import get_ctc

    ctc = get_ctc()
    out = args.out / "skipcut"
    (out / "audio").mkdir(parents=True, exist_ok=True)
    rows, anns = [], []
    for r in src:
        x = load_audio_file(r["audio"])
        pw = passage_words(r["human_transcript"])
        if len(pw) < 6:
            continue
        ev = ctc.expected_evidence(ctc.log_probs(ctc.logits(x)), pw)
        if ev is None:
            continue
        cand = [i for i in range(1, len(pw) - 1) if ev[i].start is not None and ev[i].end is not None]
        cut = sorted(rng.sample(cand, min(len(cand), rng.choice([1, 2]))))
        if not cut:
            continue
        keep, last = [], 0
        for i in cut:
            a, b = int(ev[i].start * SR), int(ev[i].end * SR)
            keep.append(x[last:a])
            keep.append(np.zeros(int(0.15 * SR), dtype=np.float32))  # a short natural pause
            last = b
        keep.append(x[last:])
        rid = r["id"].replace("fleurs_test", "skipcut")
        save_wav(str(out / "audio" / f"{rid}.wav"), np.concatenate(keep))
        labels = ["s" if i in cut else "c" for i in range(len(pw))]
        rows.append(rec(rid, f"audio/{rid}.wav", " ".join(w.norm for k, w in enumerate(pw) if k not in cut),
                        r["human_transcript"]))
        anns += ann(rid, pw, labels, {})
    write(out, rows, anns)

    # ---- child-like voice and the paired original
    out_c, out_o = args.out / "childlike", args.out / "original"
    (out_c / "audio").mkdir(parents=True, exist_ok=True)
    rows_c, rows_o, anns_c, anns_o = [], [], [], []
    for r in src:
        x = load_audio_file(r["audio"])
        y = pitch_shift(vtlp(x, rng.uniform(1.08, 1.20)), rng.uniform(2.0, 6.0))
        y = np.clip(y / (np.max(np.abs(y)) + 1e-9) * min(0.9, float(np.max(np.abs(x)))), -1, 1)
        rid_c, rid_o = r["id"].replace("fleurs_test", "childlike"), r["id"].replace("fleurs_test", "original")
        save_wav(str(out_c / "audio" / f"{rid_c}.wav"), y.astype(np.float32))
        rows_c.append(rec(rid_c, f"audio/{rid_c}.wav", r["human_transcript"], r["passage_text"]))
        rows_o.append(rec(rid_o, r["audio"], r["human_transcript"], r["passage_text"]))
        for a in sorted(src_ann[r["id"]], key=lambda a: int(a["word_index"])):
            anns_c.append({**a, "recording_id": rid_c})
            anns_o.append({**a, "recording_id": rid_o})
    write(out_c, rows_c, anns_c)
    write(out_o, rows_o, anns_o)


if __name__ == "__main__":
    main()
