"""Build a *synthetic* smoke-test set with neural TTS (needs internet once).

    python -m scripts.make_synthetic_set --out eval_synthetic --passages P01 P04 P06

This only checks that calibration and benchmark code run end to end. TTS
voices are adult and may "correct" planned errors while speaking, so the
labels are approximate. NEVER report results from this set; real results come
from the human-annotated recordings described in docs/DATA_COLLECTION.md.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from app.assessment.marking import passage_words  # noqa: E402
from app.bangla.segment import segment_normalized  # noqa: E402
from app.evaluation.dataset import load_seed_passages  # noqa: E402
from app.speech.audio import load_audio_file, save_wav  # noqa: E402

VOICES = ["bn-BD-NabanitaNeural", "bn-BD-PradeepNeural", "bn-IN-TanishaaNeural", "bn-IN-BashkarNeural"]
EDITS = [("্র", ""), ("্য", ""), ("্ব", ""), ("ে", "া"), ("া", "ে"), ("ি", "া"), ("ধ", "দ"), ("ভ", "ব"), ("ক্ষ", "ক"),
         ("ু", "া"), ("ো", "া")]


def mutate(word: str, rng: random.Random) -> tuple[str, int] | None:
    edits = EDITS[:]
    rng.shuffle(edits)
    for a, b in edits:
        pos = word.find(a)
        if pos >= 0:
            new = word[:pos] + b + word[pos + len(a):]
            if new and new != word:
                old_u = segment_normalized(word)
                unit = next((k for k, u in enumerate(old_u) if u.start <= pos < u.end), 0)
                return new, unit
    return None


async def tts(text: str, voice: str, path: Path, tries: int = 4) -> None:
    import edge_tts

    for k in range(tries):
        try:
            await edge_tts.Communicate(text, voice).save(str(path))
            return
        except edge_tts.exceptions.NoAudioReceived:
            if k == tries - 1:
                raise
            await asyncio.sleep(2 + 2 * k)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="eval_synthetic", type=Path)
    ap.add_argument("--passages", nargs="+", default=["P01", "P04", "P06"])
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    passages = load_seed_passages()
    out: Path = args.out
    (out / "audio").mkdir(parents=True, exist_ok=True)
    rec_rows, ann_rows = [], []
    for vi, voice in enumerate(VOICES):
        split = "tune" if vi < 2 else "test"
        for code in args.passages:
            pw = passage_words(passages[code])
            for kind in ("ok", "err"):
                spoken, labels, units = [], [], {}
                for w in pw:
                    r = rng.random()
                    if kind == "err" and r < 0.08:
                        labels.append("s")
                        continue
                    if kind == "err" and r < 0.25:
                        mut = mutate(w.norm, rng)
                        if mut:
                            spoken.append(mut[0])
                            labels.append("m")
                            units[w.index] = mut[1]
                            continue
                    spoken.append(w.norm)
                    labels.append("c")
                rid = f"{voice.split('-')[2][:4].lower()}_{code}_{kind}"
                mp3 = out / "audio" / f"{rid}.mp3"
                asyncio.run(tts(" ".join(spoken), voice, mp3))
                audio = load_audio_file(str(mp3))
                wav = out / "audio" / f"{rid}.wav"
                save_wav(str(wav), audio)
                mp3.unlink()
                rec_rows.append({"id": rid, "audio": f"audio/{rid}.wav", "passage": code, "speaker": voice,
                                 "group": "adult", "split": split, "condition": "clean", "human_wcpm": "",
                                 "human_transcript": " ".join(spoken)})
                for w, lab in zip(pw, labels):
                    ann_rows.append({"recording_id": rid, "word_index": w.index, "word": w.norm, "label_a": lab,
                                     "label_b": lab, "label": lab, "error_units": units.get(w.index, "")})
                # a noisy copy for test voices (classroom-like babble approximated by noise)
                if split == "test":
                    noise = np.random.default_rng(vi).normal(0, 1, len(audio)).astype(np.float32)
                    sig_p = float(np.mean(audio ** 2)) + 1e-9
                    noise *= np.sqrt(sig_p / (10 ** (12 / 10)) / float(np.mean(noise ** 2)))
                    nid = rid + "_noisy"
                    save_wav(str(out / "audio" / f"{nid}.wav"), np.clip(audio + noise, -1, 1))
                    rec_rows.append({**rec_rows[-1], "id": nid, "audio": f"audio/{nid}.wav", "condition": "noisy"})
                    for w, lab in zip(pw, labels):
                        ann_rows.append({"recording_id": nid, "word_index": w.index, "word": w.norm,
                                         "label_a": lab, "label_b": lab, "label": lab,
                                         "error_units": units.get(w.index, "")})
                print("made", rid)
    with open(out / "recordings.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rec_rows[0].keys()))
        wr.writeheader()
        wr.writerows(rec_rows)
    with open(out / "annotations.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(ann_rows[0].keys()))
        wr.writeheader()
        wr.writerows(ann_rows)
    print(f"wrote {len(rec_rows)} recordings to {out}")


if __name__ == "__main__":
    main()
