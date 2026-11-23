"""A trained word-level error classifier on top of the speech model (replaces two hand-set thresholds).

    python -m scripts.word_classifier cache    # run the speech model once, cache every word (~15 min)
    python -m scripts.word_classifier train    # train on the TUNING split, test ONCE on held-out test

Why: the rule-based decision uses two thresholds (free-decoding confidence, expected-text GOP). A small
logistic-regression model can combine more evidence per word (both signals, how many units differ,
unit-level GOP, whether only the spelling differs, word length, duration, repeats...). It is trained only
on the FLEURS tuning split (120 recordings, different speakers from test); its decision thresholds are
chosen by 5-fold cross-validation on tuning data under the same rule as before (false alarms <= 5%,
then best F1, then fewest "unsure"). The test split (first 100 recordings, the same as the published
benchmark) is used once, for the final comparison with the rule-based system, with paired bootstrap CIs.

Only words the decoder already flags (raw status misread or skipped) are re-decided; words the decoder
heard exactly stay correct, and "not reached" stays as it is. Output: results/word_classifier.json
(weights + report). The app uses it only if that file exists and its test result beat the rules.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.assessment import types as T  # noqa: E402
from app.assessment.learned import FEATURES, features  # noqa: E402
from app.config import BACKEND_DIR, RESULTS_DIR, load_thresholds  # noqa: E402

CACHE = BACKEND_DIR / "data" / "eval_fleurs" / "word_cache.json"
REC = BACKEND_DIR / "data" / "eval_fleurs" / "recordings.csv"
ANN = BACKEND_DIR / "data" / "eval_fleurs" / "annotations.csv"
MAX_FALSE_ALARM = 0.05
TEST_LIMIT = 100


def cache() -> None:
    from app.evaluation.dataset import load_dataset, load_seed_passages
    from app.pipeline import run_porabondhu
    from app.speech.audio import load_audio_file
    from app.speech.registry import get_ctc

    data = load_dataset(REC, ANN, load_seed_passages())
    tune = [r for r in data if r.split == "tune"]
    test = [r for r in data if r.split == "test"][:TEST_LIMIT]
    th = load_thresholds()
    ctc = get_ctc()
    out = {"thresholds": th.to_dict(), "model": ctc.model_id, "recordings": []}
    t0 = time.perf_counter()
    for k, rec in enumerate(tune + test, 1):
        res = run_porabondhu(load_audio_file(str(rec.audio)), rec.passage_text, ctc, th, skip_quality=True,
                             use_word_model=False)  # the rules alone: what the classifier learns from
        marks = [m.to_dict() for m in res.marks]
        assert len(marks) == len(rec.labels), rec.id
        out["recordings"].append({"id": rec.id, "split": rec.split, "labels": rec.labels, "marks": marks})
        print(f"[{k}/{len(tune) + len(test)}] {rec.id} {time.perf_counter() - t0:.0f}s", flush=True)
    CACHE.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print("cached", CACHE)


# ------------------------------------------------------------------ model
def fit_logreg(X: np.ndarray, y: np.ndarray, l2: float = 1.0, iters: int = 3000, lr: float = 0.1):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    w, b = np.zeros(Z.shape[1]), 0.0
    n = len(y)
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(Z @ w + b)))
        g = p - y
        w -= lr * (Z.T @ g / n + l2 * w / n)
        b -= lr * g.mean()
    return {"mean": mu.tolist(), "std": sd.tolist(), "weights": w.tolist(), "bias": float(b)}


def predict(model: dict, X: np.ndarray) -> np.ndarray:
    Z = (X - np.array(model["mean"])) / np.array(model["std"])
    return 1 / (1 + np.exp(-(Z @ np.array(model["weights"]) + model["bias"])))


# ------------------------------------------------------------------ evaluation
def candidates(rec: dict):
    """(word index, features, human error?) for words the decoder flagged."""
    for i, (m, h) in enumerate(zip(rec["marks"], rec["labels"])):
        if h == T.NOT_REACHED or m["status"] == T.NOT_REACHED or m["raw_status"] == T.CORRECT:
            continue
        yield i, features(m), h in (T.MISREAD, T.SKIPPED)


def decide(rec: dict, probs: dict[int, float] | None, lo: float, hi: float) -> list[str]:
    """Statuses after the classifier (probs=None -> the rule-based statuses as cached)."""
    out = []
    for i, m in enumerate(rec["marks"]):
        st = m["status"]
        if probs is not None and i in probs:
            p = probs[i]
            st = m["raw_status"] if p >= hi else (T.CORRECT if p <= lo else T.UNSURE)
        out.append(st)
    return out


def tally(recs: list[dict], statuses: list[list[str]]) -> dict:
    tp = fp = fn = correct = unsure = words = 0
    for rec, sts in zip(recs, statuses):
        for st, h in zip(sts, rec["labels"]):
            if h == T.NOT_REACHED:
                continue
            words += 1
            he, pe = h in (T.MISREAD, T.SKIPPED), st in (T.MISREAD, T.SKIPPED)
            unsure += st == T.UNSURE
            correct += not he
            tp += he and pe
            fp += pe and not he
            fn += he and not pe
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec_ = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": prec, "recall": rec_, "f1": 2 * prec * rec_ / (prec + rec_) if prec + rec_ else 0.0,
            "false_alarm": fp / correct if correct else 0.0, "unsure_rate": unsure / max(words, 1),
            "tp": tp, "fp": fp, "fn": fn, "words": words, "errors": tp + fn, "correct_words": correct}


def key(s: dict) -> tuple:
    ok = s["false_alarm"] <= MAX_FALSE_ALARM
    return (ok, s["f1"] if ok else -s["false_alarm"], -s["unsure_rate"])


def choose_thresholds(recs: list[dict], probs: list[dict[int, float]]) -> tuple[float, float, dict]:
    grid = [x / 100 for x in range(2, 99, 2)]
    best = None
    for hi in grid:
        for lo in [g for g in grid if g <= hi]:
            s = tally(recs, [decide(r, p, lo, hi) for r, p in zip(recs, probs)])
            if best is None or key(s) > key(best[2]):
                best = (lo, hi, s)
    return best


def matrix(recs: list[dict]):
    rows, ys, owners = [], [], []
    for r_i, rec in enumerate(recs):
        for i, f, y in candidates(rec):
            rows.append(f)
            ys.append(1.0 if y else 0.0)
            owners.append((r_i, i))
    return np.array(rows, dtype=float), np.array(ys), owners


def probs_by_rec(recs, owners, p) -> list[dict[int, float]]:
    out: list[dict[int, float]] = [{} for _ in recs]
    for (r_i, i), v in zip(owners, p):
        out[r_i][i] = float(v)
    return out


def bootstrap_diff(recs, a_sts, b_sts, metric: str, n: int = 2000, seed: int = 7) -> dict:
    rng = random.Random(seed)
    idx = list(range(len(recs)))
    diffs = []
    for _ in range(n):
        s = [rng.choice(idx) for _ in idx]
        ra = tally([recs[k] for k in s], [a_sts[k] for k in s])[metric]
        rb = tally([recs[k] for k in s], [b_sts[k] for k in s])[metric]
        diffs.append(rb - ra)
    diffs.sort()
    return {"diff": round(tally(recs, b_sts)[metric] - tally(recs, a_sts)[metric], 4),
            "ci95": [round(diffs[int(0.025 * n)], 4), round(diffs[int(0.975 * n)], 4)]}


def train() -> None:
    data = json.loads(CACHE.read_text(encoding="utf-8"))
    tune = [r for r in data["recordings"] if r["split"] == "tune"]
    test = [r for r in data["recordings"] if r["split"] == "test"]

    # 1) out-of-fold probabilities on tuning data -> decision thresholds (5-fold by recording)
    rng = random.Random(0)
    order = list(range(len(tune)))
    rng.shuffle(order)
    folds = [order[k::5] for k in range(5)]
    oof: list[dict[int, float]] = [{} for _ in tune]
    for k in range(5):
        held = set(folds[k])
        tr = [tune[i] for i in range(len(tune)) if i not in held]
        Xtr, ytr, _ = matrix(tr)
        m = fit_logreg(Xtr, ytr)
        hr = [tune[i] for i in sorted(held)]
        Xh, _, own = matrix(hr)
        ph = predict(m, Xh) if len(Xh) else []
        for (r_i, i), v in zip(own, ph):
            oof[sorted(held)[r_i]][i] = float(v)
    lo, hi, cv = choose_thresholds(tune, oof)
    rules_tune = tally(tune, [decide(r, None, 0, 1) for r in tune])

    # 2) final model on all tuning data
    X, y, _ = matrix(tune)
    model = fit_logreg(X, y)

    # 3) one evaluation on the held-out test recordings
    Xt, _, own_t = matrix(test)
    pt = probs_by_rec(test, own_t, predict(model, Xt))
    rules_sts = [decide(r, None, 0, 1) for r in test]
    learned_sts = [decide(r, p, lo, hi) for r, p in zip(test, pt)]
    rules_test, learned_test = tally(test, rules_sts), tally(test, learned_sts)
    diffs = {m: bootstrap_diff(test, rules_sts, learned_sts, m) for m in ("precision", "recall", "false_alarm", "unsure_rate", "f1")}
    better = learned_test["false_alarm"] <= MAX_FALSE_ALARM and diffs["f1"]["ci95"][0] > 0 or (
        learned_test["false_alarm"] <= rules_test["false_alarm"] and learned_test["f1"] > rules_test["f1"])

    def r4(d):
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}

    coef = sorted(zip(FEATURES, model["weights"]), key=lambda t: -abs(t[1]))
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "what": "Logistic-regression word error classifier on top of the CTC model; trained on FLEURS tuning split only",
        "train": {"recordings": len(tune), "candidate_words": int(len(y)), "positives": int(y.sum())},
        "test": {"recordings": len(test), "candidate_words": int(len(Xt)), "note": "same first 100 test recordings as the published benchmark; used once"},
        "features": FEATURES,
        "model": model,
        "decision": {"lo": lo, "hi": hi, "rule": "p >= hi -> error; p <= lo -> correct; else unsure",
                     "chosen_by": "5-fold CV on tuning data: false alarms <= 5%, best F1, fewest unsure"},
        "cv_tune": r4(cv), "rules_tune": r4(rules_tune),
        "rules_test": r4(rules_test), "learned_test": r4(learned_test),
        "difference_learned_minus_rules_test": diffs,
        "use_in_app": bool(better),
        "strongest_features": [{"feature": f, "weight": round(w, 3)} for f, w in coef[:8]],
        "thresholds_of_rule_system": data["thresholds"],
    }
    out = RESULTS_DIR / "word_classifier.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("train", "decision", "cv_tune", "rules_tune", "rules_test", "learned_test",
                                              "difference_learned_minus_rules_test", "use_in_app", "strongest_features")},
                     ensure_ascii=False, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["cache", "train"])
    a = ap.parse_args()
    cache() if a.cmd == "cache" else train()
