"""Trust test: background noise and regional accent, with the trust guards off vs on.

    python -m scripts.eval_noise_accent --n 60

Uses the FLEURS *test* speakers of the robustness set (data/eval_robust/original: real adult speech,
simulated reading errors with exact labels). Nothing here was used to tune the guards.

* noise   - the same recordings mixed with (a) classroom-like babble: three other test speakers talking
            at once, at 20, 10 and 5 dB signal-to-noise, and (b) broadband hiss (fan / rain) at 10 dB.
            Labels unchanged. Reports recall, false alarms (correct words flagged as errors) and unsure.
* accent  - simulated regional pronunciation: in about a quarter of the words that contain one of the
            sounds below, the *passage* letter is changed so that what the speaker actually said is the
            regional form (passage ভাত, speaker said বাত). These words were read correctly in that
            accent, so any error flag on them is a false alarm. Swaps: ব/ভ গ/ঘ দ/ধ ত/থ ক/খ প/ফ জ/ঝ
            চ/ছ ট/ঠ ড/ঢ (dropped aspiration), র/ড় (merger), স/চ (Sylhet, Noakhali).

Each recording is decoded once per condition; the guards are applied to a copy of the same marks, so
"off" and "on" are a paired comparison. Writes results/noise_accent.json (shown on the Benchmark page).
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from app.assessment import types as T  # noqa: E402
from app.assessment.marking import passage_words  # noqa: E402
from app.assessment.robust import GuardOptions, apply_guards  # noqa: E402
from app.config import RESULTS_DIR, load_thresholds  # noqa: E402
from app.evaluation.dataset import load_dataset, load_seed_passages  # noqa: E402
from app.evaluation.scoring import SystemRun, Tally, summarise, tally_run  # noqa: E402
from app.evaluation.stats import proportion  # noqa: E402
from app.pipeline import run_porabondhu  # noqa: E402
from app.speech.audio import load_audio_file  # noqa: E402
from app.speech.registry import get_ctc  # noqa: E402

OFF = GuardOptions(accent=False, noise=False, odd_words=False)
# what the speaker said -> the standard letter written in the passage
ACCENT_SWAPS = {"ব": "ভ", "গ": "ঘ", "দ": "ধ", "ত": "থ", "ক": "খ", "প": "ফ", "জ": "ঝ", "চ": "ছ", "ট": "ঠ",
                "ড": "ঢ", "র": "ড়", "স": "চ"}
HASANTA = "্"


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x ** 2) + 1e-12))


def mix(x: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    if len(noise) < len(x):
        noise = np.tile(noise, int(np.ceil(len(x) / len(noise))))
    noise = noise[: len(x)]
    gain = rms(x) / (rms(noise) * 10 ** (snr_db / 20))
    y = x + gain * noise
    return np.clip(y / max(1.0, float(np.max(np.abs(y)))) , -1, 1).astype(np.float32)


def babble(others: list[np.ndarray], n: int) -> np.ndarray:
    out = np.zeros(n, dtype=np.float32)
    for o in others:
        o = np.tile(o, int(np.ceil(n / len(o))))[:n]
        out += o / rms(o)
    return out


def accent_passage(words: list[str], rng: random.Random) -> tuple[list[str], set[int]]:
    """Change one letter in ~25% of eligible words so the spoken form is the regional one."""
    out, swapped = [], set()
    for i, w in enumerate(words):
        pos = [k for k, ch in enumerate(w) if ch in ACCENT_SWAPS and (k == 0 or w[k - 1] != HASANTA)
               and (k + 1 >= len(w) or w[k + 1] != HASANTA)]
        if pos and rng.random() < 0.25:
            k = rng.choice(pos)
            out.append(w[:k] + ACCENT_SWAPS[w[k]] + w[k + 1:])
            swapped.add(i)
        else:
            out.append(w)
    return out, swapped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default=Path("data/eval_robust/original"), type=Path)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=31)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    nrng = np.random.default_rng(args.seed)

    every = load_dataset(args.set / "recordings.csv", args.set / "annotations.csv", load_seed_passages())
    data = every[: args.n]
    th = load_thresholds()
    ctc = get_ctc()
    audios = {r.id: load_audio_file(str(r.audio)) for r in every}  # babble talkers come from the whole set
    ids = [r.id for r in every]

    conds = {"clean": None, "babble_20db": ("babble", 20), "babble_10db": ("babble", 10),
             "babble_5db": ("babble", 5), "hiss_10db": ("hiss", 10)}
    tallies = {c: {"off": Tally(), "on": Tally()} for c in conds}
    guard_counts = {c: {"accent": 0, "noisy": 0, "odd_word": 0} for c in conds}
    acc = {"off": [0, 0, 0], "on": [0, 0, 0]}  # flagged, unsure, words  (on the accent-swapped words)
    acc_other = {"off": [0, 0], "on": [0, 0]}  # flagged, words (the other, unchanged correct words)
    acc_counts = {"accent": 0, "noisy": 0, "odd_word": 0}
    t0 = time.perf_counter()

    def run(rec, audio, text, labels):
        res = run_porabondhu(audio, text, ctc, th, skip_quality=True, guards=OFF)
        off = res.marks
        on = copy.deepcopy(off)
        counts = apply_guards(on, audio, passage_words(text), GuardOptions())
        return off, on, counts, res

    for k, rec in enumerate(data, 1):
        x = audios[rec.id]
        for c, spec in conds.items():
            if spec is None:
                y = x
            elif spec[0] == "babble":
                others = [audios[o] for o in rng.sample([i for i in ids if i != rec.id], 3)]
                y = mix(x, babble(others, len(x)), spec[1])
            else:
                y = mix(x, nrng.normal(0, 1, len(x)).astype(np.float32), spec[1])
            off, on, counts, res = run(rec, y, rec.passage_text, rec.labels)
            for key in counts:
                guard_counts[c][key] += counts[key]
            for mode, marks in (("off", off), ("on", on)):
                md = [m.to_dict() for m in marks]
                tally_run(tallies[c][mode], SystemRun(rec, "porabondhu", md, None, res.transcript, 0, len(y) / 16000))
        # simulated accent on the words the speaker actually said
        spoken = [w.norm for w in passage_words(rec.human_transcript or "")]
        if spoken:
            words, swapped = accent_passage(spoken, rng)
            text = " ".join(words)
            pw = passage_words(text)
            if len(pw) == len(words) and swapped:
                off, on, counts, _ = run(rec, x, text, None)
                for key in counts:
                    acc_counts[key] += counts[key]
                for mode, marks in (("off", off), ("on", on)):
                    for m in marks:
                        flagged = m.status in T.ERROR_STATUSES
                        if m.index in swapped:
                            acc[mode][0] += flagged
                            acc[mode][1] += m.status == T.UNSURE
                            acc[mode][2] += 1
                        elif m.status != T.NOT_REACHED:
                            acc_other[mode][0] += flagged
                            acc_other[mode][1] += 1
        print(f"[{k}/{len(data)}] {rec.id} done ({time.perf_counter() - t0:.0f}s)", flush=True)

    def brief(s: dict) -> dict:
        return {k: s[k] for k in ("recordings", "words", "recall", "precision", "false_alarm", "unsure_rate",
                                  "confusion")}

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "label": f"Trust test: FLEURS bn test speakers, first {len(data)} recordings of the robustness set "
                 "(real adult speech, simulated reading errors and simulated accent; not children)",
        "recordings": len(data),
        "noise": {c: {"label": {"clean": "No added noise", "babble_20db": "Classroom babble, 20 dB",
                                "babble_10db": "Classroom babble, 10 dB", "babble_5db": "Classroom babble, 5 dB",
                                "hiss_10db": "Fan / rain hiss, 10 dB"}[c],
                      "guards_off": brief(summarise(tallies[c]["off"])),
                      "guards_on": brief(summarise(tallies[c]["on"])),
                      "guard_changes": guard_counts[c]} for c in conds},
        "accent": {
            "label": "Simulated regional pronunciation (dropped aspiration, র/ড়, স for চ)",
            "accent_words": acc["off"][2],
            "guards_off": {"false_alarm": proportion(acc["off"][0], acc["off"][2]),
                           "unsure_rate": proportion(acc["off"][1], acc["off"][2])},
            "guards_on": {"false_alarm": proportion(acc["on"][0], acc["on"][2]),
                          "unsure_rate": proportion(acc["on"][1], acc["on"][2])},
            "other_words_false_alarm": {"guards_off": proportion(acc_other["off"][0], acc_other["off"][1]),
                                        "guards_on": proportion(acc_other["on"][0], acc_other["on"][1])},
            "guard_changes": acc_counts,
        },
        "seconds": round(time.perf_counter() - t0, 1),
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / "noise_accent.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", path)
    for c in conds:
        a, b = out["noise"][c]["guards_off"], out["noise"][c]["guards_on"]
        print(f"{c:12s} recall {a['recall']['value']:.3f}->{b['recall']['value']:.3f}  "
              f"false alarm {a['false_alarm']['value']:.3f}->{b['false_alarm']['value']:.3f}  "
              f"unsure {a['unsure_rate']['value']:.3f}->{b['unsure_rate']['value']:.3f}")
    print("accent false alarm", out["accent"]["guards_off"]["false_alarm"], "->", out["accent"]["guards_on"]["false_alarm"])


if __name__ == "__main__":
    main()
