"""Child-voice adaptation (Proposal 3.3): fine-tune the Bangla CTC model on adult
speech that has been transformed to sound more like children.

    python -m scripts.adapt_child_voice --data train.csv --out data/models/adapted --epochs 1
    python -m scripts.adapt_child_voice --data train.csv --preview-dir data/aug_preview   # listen first

train.csv: columns ``audio,text`` (public adult Bangla speech such as OpenSLR 53
or Common Voice Bangla; NEVER the evaluation recordings - testing must stay
speaker-independent).

Augmentation, applied on the fly with random strength per utterance:
  * pitch shift up 2-6 semitones (children have higher F0),
  * vocal-tract-length perturbation: formants scaled up 8-20% by resampling and
    then restoring the original duration (children have shorter vocal tracts).

Training: feature encoder frozen, by default only the top 4 transformer layers
and the output head are updated (fits in laptop RAM), AdamW, small learning rate; runs on CPU
(slow: plan hours, or run it on a free GPU notebook and copy the folder back).
Afterwards set PB_CTC_MODEL_ID=<out> and re-run scripts/export_onnx.py --model <out>.
If it does not improve the tuning-set results, keep the public checkpoint and
report that (Proposal fallback).
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from app.bangla.normalize import normalize_text  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.speech.audio import SR, load_audio_file, save_wav  # noqa: E402


def pitch_shift(x: np.ndarray, semitones: float) -> np.ndarray:
    import librosa

    return librosa.effects.pitch_shift(x, sr=SR, n_steps=semitones).astype(np.float32)


def vtlp(x: np.ndarray, alpha: float) -> np.ndarray:
    """Scale formants by ``alpha`` (>1 = shorter vocal tract) keeping duration."""
    import librosa

    # play faster by alpha (raises pitch and formants), then stretch back
    y = librosa.resample(x, orig_sr=SR, target_sr=int(SR / alpha))
    y = librosa.effects.time_stretch(y, rate=len(y) / len(x))
    # undo the pitch part so only the formant shift remains
    y = librosa.effects.pitch_shift(y, sr=SR, n_steps=-12 * np.log2(alpha))
    n = len(x)
    return (y[:n] if len(y) >= n else np.pad(y, (0, n - len(y)))).astype(np.float32)


def childlike(x: np.ndarray, rng: random.Random) -> np.ndarray:
    y = vtlp(x, rng.uniform(1.08, 1.20))
    y = pitch_shift(y, rng.uniform(2.0, 6.0))
    peak = float(np.abs(y).max()) or 1.0
    return y / peak * min(0.95, float(np.abs(x).max()) or 0.95)


def read_rows(path: Path) -> list[tuple[Path, str]]:
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            p = Path(r["audio"])
            rows.append((p if p.is_absolute() else path.parent / p, normalize_text(r["text"])))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=get_settings().data_dir / "models" / "adapted")
    ap.add_argument("--model", default=get_settings().ctc_model_id)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--max-steps", type=int, default=0, help="stop early (0 = no limit)")
    ap.add_argument("--train-layers", type=int, default=4,
                    help="train only the top N transformer layers + output head (0 = all; needs much more RAM)")
    ap.add_argument("--aug-prob", type=float, default=0.8)
    ap.add_argument("--preview-dir", type=Path, help="only write a few augmented examples and exit")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    rows = read_rows(args.data)
    if not rows:
        sys.exit("no training rows")

    if args.preview_dir:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
        for k, (p, _t) in enumerate(rows[:5]):
            x = load_audio_file(str(p))
            save_wav(str(args.preview_dir / f"{k}_orig.wav"), x)
            save_wav(str(args.preview_dir / f"{k}_child.wav"), childlike(x, rng))
        print("wrote previews to", args.preview_dir)
        return

    import torch
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

    torch.manual_seed(args.seed)
    proc = Wav2Vec2Processor.from_pretrained(args.model)
    model = Wav2Vec2ForCTC.from_pretrained(args.model, ctc_loss_reduction="mean")
    model.freeze_feature_encoder()
    if args.train_layers:
        for prm in model.wav2vec2.parameters():
            prm.requires_grad = False
        for layer in model.wav2vec2.encoder.layers[-args.train_layers:]:
            for prm in layer.parameters():
                prm.requires_grad = True
    n_train = sum(prm.numel() for prm in model.parameters() if prm.requires_grad)
    print(f"training {n_train / 1e6:.1f}M parameters")
    model.train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr)
    vocab = proc.tokenizer.get_vocab()
    delim = proc.tokenizer.word_delimiter_token or "|"

    def encode(text: str) -> list[int]:
        ids = []
        for ch in text:
            if ch == " ":
                ids.append(vocab[delim])
            elif ch in vocab:
                ids.append(vocab[ch])
        return ids

    step, t0 = 0, time.perf_counter()
    for epoch in range(args.epochs):
        rng.shuffle(rows)
        for p, text in rows:
            x = load_audio_file(str(p))
            if len(x) > SR * 20:  # keep memory bounded on CPU
                continue
            if rng.random() < args.aug_prob:
                x = childlike(x, rng)
            labels = encode(text)
            if not labels:
                continue
            inp = proc(x, sampling_rate=SR, return_tensors="pt").input_values
            out = model(inp, labels=torch.tensor([labels]))
            if not torch.isfinite(out.loss):
                continue
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            opt.zero_grad()
            step += 1
            if step % 10 == 0 or step == 1:
                print(f"epoch {epoch} step {step} loss {out.loss.item():.3f} ({time.perf_counter() - t0:.0f}s)")
            if args.max_steps and step >= args.max_steps:
                break
        if args.max_steps and step >= args.max_steps:
            break
    args.out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.out)
    proc.save_pretrained(args.out)
    print(f"saved adapted model to {args.out} after {step} steps")


if __name__ == "__main__":
    main()
