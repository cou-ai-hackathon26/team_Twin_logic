"""Tune the test-time voice normalisation on DEV recordings only (adult + child-like copies).

    python -m scripts.voicenorm_experiment --n 40

For each dev recording we make a child-like copy with the same transform as the robustness set
(formant x1.08-1.20, pitch +2..6 semitones, different random draws), decode the original and the
child-like copy with every candidate inverse warp, and score each policy:

* none           - current system
* fixed warp     - always apply one inverse warp
* auto(gate)     - keep the original unless its free-decoding confidence < gate, else take the most
                   confident candidate (app/speech/voicenorm.py)

A policy is acceptable only if it does not raise false alarms on the adult originals. The chosen
gate/candidates are written to data/reports/voicenorm_dev.json; test recordings are not touched.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.assessment import types as T  # noqa: E402
from app.assessment.marking import assess, passage_words  # noqa: E402
from app.config import get_settings, load_thresholds  # noqa: E402
from app.evaluation.dataset import load_dataset, load_seed_passages  # noqa: E402
from app.speech.audio import load_audio_file  # noqa: E402
from app.speech.registry import get_ctc  # noqa: E402
from app.speech.voicenorm import decode_confidence, warp  # noqa: E402
from scripts.adapt_child_voice import pitch_shift, vtlp  # noqa: E402

CANDS = [(1.0, 0.0), (0.92, -2.0), (0.88, -3.0), (0.84, -4.0), (0.80, -5.0), (0.88, 0.0)]
GATES = [0.0, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 1.01]  # 0 = never warp, 1.01 = always pick the best


def score(items, choice) -> dict:
    tp = fp = fn = hc = un = w = 0
    for it, c in zip(items, choice):
        rw, ev = it["dec"][c]
        for m, h in zip(assess(it["pw"], rw, ev, it["th"]), it["labels"]):
            if h == T.NOT_REACHED:
                continue
            w += 1
            he, pe = h in (T.MISREAD, T.SKIPPED), m.status in (T.MISREAD, T.SKIPPED)
            tp += he and pe
            fp += pe and not he
            fn += he and not pe
            hc += not he
            un += m.status == T.UNSURE
    return {"recall": round(tp / max(tp + fn, 1), 4), "precision": round(tp / max(tp + fp, 1), 4),
            "false_alarm": round(fp / max(hc, 1), 4), "unsure_rate": round(un / max(w, 1), 4), "words": w}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    args = ap.parse_args()
    rng = random.Random(41)
    th = load_thresholds()
    ctc = get_ctc()
    data = [r for r in load_dataset(Path("data/eval_fleurs/recordings.csv"), Path("data/eval_fleurs/annotations.csv"),
                                     load_seed_passages()) if r.split == "tune"][: args.n]
    sets = {"adult": [], "childlike": []}
    for k, rec in enumerate(data, 1):
        x = load_audio_file(str(rec.audio))
        child = pitch_shift(vtlp(x, rng.uniform(1.08, 1.20)), rng.uniform(2.0, 6.0))
        pw = passage_words(rec.passage_text)
        for name, audio in (("adult", x), ("childlike", child)):
            dec, conf = {}, {}
            for c in CANDS:
                lg = ctc.logits(audio if c == (1.0, 0.0) else warp(audio, *c))
                lp = ctc.log_probs(lg, th.temperature)
                dec[c] = (ctc.greedy_decode(lp), ctc.expected_evidence(lp, pw))
                conf[c] = decode_confidence(ctc, lg, th.temperature)
            sets[name].append({"pw": pw, "labels": rec.labels, "th": th, "dec": dec, "conf": conf})
        print(f"[{k}/{len(data)}] {rec.id}", flush=True)

    report = {"recordings": len(data), "candidates": CANDS, "policies": {}}
    for name, items in sets.items():
        pol = {"none": score(items, [(1.0, 0.0)] * len(items))}
        for c in CANDS[1:]:
            pol[f"fixed {c}"] = score(items, [c] * len(items))
        for g in GATES[1:]:
            choice = []
            for it in items:
                if it["conf"][(1.0, 0.0)] >= g:
                    choice.append((1.0, 0.0))
                else:
                    choice.append(max(CANDS, key=lambda c: it["conf"][c]))
            pol[f"auto gate {g}"] = {**score(items, choice),
                                     "warped": sum(c != (1.0, 0.0) for c in choice)}
        report["policies"][name] = pol
        report[f"{name}_original_conf"] = sorted(round(it["conf"][(1.0, 0.0)], 3) for it in items)
    # choose: best child-like F1 among auto gates that keep adult false alarms within +0.5 points
    base_fa = report["policies"]["adult"]["none"]["false_alarm"]

    def f1(s):
        return 2 * s["precision"] * s["recall"] / max(s["precision"] + s["recall"], 1e-9)

    ok = [g for g in GATES[1:] if report["policies"]["adult"][f"auto gate {g}"]["false_alarm"] <= base_fa + 0.005]
    best = max(ok, key=lambda g: f1(report["policies"]["childlike"][f"auto gate {g}"]), default=None)
    report["chosen_gate"] = best
    out = get_settings().reports_dir / "voicenorm_dev.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), "utf-8")
    for name in sets:
        print(f"\n== {name}")
        for k, v in report["policies"][name].items():
            print(f"  {k:<22} {v}")
    print("\nchosen gate:", best, "\nreport:", out)


if __name__ == "__main__":
    main()
