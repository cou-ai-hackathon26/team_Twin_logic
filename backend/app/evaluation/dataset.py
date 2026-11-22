"""Annotated evaluation data.

Two CSV files (easy to fill in a spreadsheet) are turned into a manifest:

recordings.csv
    id, audio, passage, speaker, group, split, condition, human_wcpm, human_transcript
    group     = adult | child
    split     = tune | test      (tuning speakers are never reported)
    condition = clean | noisy
    passage_text (optional) = the expected text, for recordings of text that is
                not in the passage bank (e.g. public speech corpora)

annotations.csv  (one row per passage word per recording)
    recording_id, word_index, word, label_a, label_b, label, error_units
    labels: c = correct, m = misread, s = skipped, n = not reached
    label        = adjudicated label after both annotators listened again
    error_units  = space separated unit indices of the misread word that
                   contain the error (0-based), e.g. "0" for প্র in প্রথম
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from ..assessment import types as T

LABEL_MAP = {"c": T.CORRECT, "m": T.MISREAD, "s": T.SKIPPED, "n": T.NOT_REACHED,
             "correct": T.CORRECT, "misread": T.MISREAD, "skipped": T.SKIPPED, "not_reached": T.NOT_REACHED}


@dataclass
class Recording:
    id: str
    audio: Path
    passage_code: str
    passage_text: str
    speaker: str
    group: str
    split: str
    condition: str
    labels: list[str]
    labels_a: list[str] = field(default_factory=list)
    labels_b: list[str] = field(default_factory=list)
    error_units: dict[int, list[int]] = field(default_factory=dict)
    human_wcpm: float | None = None
    human_transcript: str | None = None


def _label(x: str) -> str:
    x = (x or "").strip().lower()
    if x not in LABEL_MAP:
        raise ValueError(f"Unknown label {x!r} (use c, m, s or n)")
    return LABEL_MAP[x]


def load_dataset(recordings_csv: Path, annotations_csv: Path, passages: dict[str, str]) -> list[Recording]:
    base = recordings_csv.parent
    ann: dict[str, list[dict]] = {}
    with open(annotations_csv, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            ann.setdefault(row["recording_id"].strip(), []).append(row)
    out: list[Recording] = []
    with open(recordings_csv, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rid = row["id"].strip()
            code = row["passage"].strip()
            text = (row.get("passage_text") or "").strip() or passages.get(code)
            if not text:
                raise ValueError(f"{rid}: unknown passage {code}")
            rows = sorted(ann.get(rid, []), key=lambda r: int(r["word_index"]))
            if not rows:
                raise ValueError(f"{rid}: no annotations")
            la = [_label(r["label_a"]) for r in rows if r.get("label_a")]
            lb = [_label(r["label_b"]) for r in rows if r.get("label_b")]
            final = [_label(r.get("label") or r["label_a"]) for r in rows]
            units = {int(r["word_index"]): [int(x) for x in (r.get("error_units") or "").split()]
                     for r in rows if (r.get("error_units") or "").strip()}
            wcpm = row.get("human_wcpm", "").strip()
            audio = Path(row["audio"].strip())
            out.append(Recording(
                id=rid, audio=audio if audio.is_absolute() else base / audio, passage_code=code,
                passage_text=text, speaker=row.get("speaker", "").strip(),
                group=(row.get("group") or "adult").strip(), split=(row.get("split") or "test").strip(),
                condition=(row.get("condition") or "clean").strip(), labels=final,
                labels_a=la if len(la) == len(rows) else [], labels_b=lb if len(lb) == len(rows) else [],
                error_units=units, human_wcpm=float(wcpm) if wcpm else None,
                human_transcript=(row.get("human_transcript") or "").strip() or None,
            ))
    return out


def load_seed_passages() -> dict[str, str]:
    seed_dir = Path(__file__).resolve().parent.parent / "seed"
    out: dict[str, str] = {}
    for name in ("passages.json", "textbook_passages.json"):
        f = seed_dir / name
        if f.exists():
            out.update({p["code"]: p["text"] for p in json.loads(f.read_text(encoding="utf-8"))})
    return out
