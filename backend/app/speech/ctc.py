"""Character-level CTC recognition with language-model-free decoding.

Pipeline Step 2:
  * greedy decoding (argmax per 20 ms frame, merge repeats, drop blanks),
  * per-character time stamps and free-decoding confidence,
  * CTC forced alignment of the passage text and a goodness-of-pronunciation
    style *expected-text score* for every passage unit (covers skipped units).

Runs on CPU. Long recordings are processed in overlapping chunks.
"""

from __future__ import annotations

import logging
import threading
import unicodedata
from dataclasses import dataclass

import numpy as np

from ..assessment import types as T
from ..bangla.normalize import normalize_word
from ..bangla.segment import segment_normalized
from .audio import SR

log = logging.getLogger(__name__)


@dataclass
class DecodedChar:
    char: str
    start_frame: int
    end_frame: int  # exclusive
    confidence: float


def _log_softmax(x: np.ndarray) -> np.ndarray:
    m = x.max(axis=-1, keepdims=True)
    y = x - m
    return y - np.log(np.exp(y).sum(axis=-1, keepdims=True))


class CTCRecognizer:
    """Thin wrapper around a Hugging Face wav2vec2 CTC checkpoint."""

    def __init__(self, model_id: str, threads: int | None = None, chunk_sec: float = 15.0,
                 context_sec: float = 1.0, backend: str = "torch", onnx_dir: str | None = None) -> None:
        """``backend``: "torch" (PyTorch fp32), "onnx" (ONNX Runtime fp32) or
        "onnx-int8" (ONNX Runtime, int8 MatMul weights; about 2x faster on CPU).
        ONNX files are produced by ``scripts/export_onnx.py``.
        """
        from transformers import AutoConfig, Wav2Vec2Processor

        self.model_id = model_id
        self.backend = backend
        src = onnx_dir if backend.startswith("onnx") and onnx_dir else model_id
        self.processor = Wav2Vec2Processor.from_pretrained(src)
        config = AutoConfig.from_pretrained(src)
        if backend.startswith("onnx"):
            import onnxruntime as ort

            assert onnx_dir is not None
            fname = "model.int8.onnx" if backend == "onnx-int8" else "model.onnx"
            so = ort.SessionOptions()
            so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            if threads:
                so.intra_op_num_threads = threads
            self._session = ort.InferenceSession(f"{onnx_dir}/{fname}", so, providers=["CPUExecutionProvider"])
            self._torch = None
            self.model = None
        else:
            import torch
            from transformers import Wav2Vec2ForCTC

            if threads:
                torch.set_num_threads(threads)
            self._torch = torch
            self.model = Wav2Vec2ForCTC.from_pretrained(model_id).eval()
        tok = self.processor.tokenizer
        vocab = tok.get_vocab()
        self.id_to_token: dict[int, str] = {i: t for t, i in vocab.items()}
        self.vocab_size = config.vocab_size
        self.blank_id: int = tok.pad_token_id
        self.delim_id: int | None = vocab.get(tok.word_delimiter_token or "|")
        self.char_to_id: dict[str, int] = {t: i for t, i in vocab.items() if len(t) == 1}
        stride = int(np.prod(config.conv_stride))
        self.samples_per_frame = stride
        self.frame_sec = stride / SR
        self.chunk = int(chunk_sec * SR)
        self.context = int(context_sec * SR)
        self._lock = threading.Lock()
        # tokens that never belong to Bangla reading output
        self._ignored = {i for t, i in vocab.items()
                         if not t or t.startswith(("[", "<")) or (len(t) == 1 and t.isascii() and t != "|")}

    # ------------------------------------------------------------------ logits
    def _forward(self, x: np.ndarray) -> np.ndarray:
        if self._torch is None:
            v = self.processor(x, sampling_rate=SR, return_tensors="np").input_values.astype(np.float32)
            return self._session.run(["logits"], {"input_values": v})[0][0]
        torch = self._torch
        inputs = self.processor(x, sampling_rate=SR, return_tensors="pt")
        with torch.inference_mode():
            out = self.model(inputs.input_values).logits[0]
        return out.float().numpy()

    def logits(self, audio: np.ndarray) -> np.ndarray:
        """Frame logits (T, V) for the whole recording."""
        with self._lock:
            if len(audio) <= self.chunk + self.context:
                return self._forward(audio)
            pieces: list[np.ndarray] = []
            spf = self.samples_per_frame
            for s in range(0, len(audio), self.chunk):
                e = min(len(audio), s + self.chunk)
                ws, we = max(0, s - self.context), min(len(audio), e + self.context)
                lg = self._forward(audio[ws:we])
                f0 = (s - ws) // spf
                f1 = f0 + int(np.ceil((e - s) / spf))
                pieces.append(lg[f0:min(f1, len(lg))])
            return np.concatenate(pieces, axis=0)

    def log_probs(self, logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
        return _log_softmax(logits / max(temperature, 1e-3))

    # ------------------------------------------------------------ free decoding
    def greedy_decode(self, lp: np.ndarray) -> list[T.RecognizedWord]:
        best = lp.argmax(axis=1)
        probs = np.exp(lp)
        words: list[list[DecodedChar]] = [[]]
        t, n = 0, len(best)
        while t < n:
            tok = int(best[t])
            s = t
            while t < n and best[t] == tok:
                t += 1
            if tok == self.blank_id or tok in self._ignored and tok != self.delim_id:
                continue
            if tok == self.delim_id:
                if words[-1]:
                    words.append([])
                continue
            ch = self.id_to_token.get(tok, "")
            if ch == "।":  # danda: sentence end, acts like a boundary
                if words[-1]:
                    words.append([])
                continue
            conf = float(probs[s:t, tok].mean())
            words[-1].append(DecodedChar(ch, s, t, conf))
        out: list[T.RecognizedWord] = []
        for chars in words:
            if not chars:
                continue
            raw = "".join(c.char for c in chars)
            norm = normalize_word(raw)
            if not norm:
                continue
            units = segment_normalized(norm)
            if len(norm) == len(raw):
                unit_conf = [min(c.confidence for c in chars[u.start:u.end]) for u in units]
            else:
                unit_conf = [min(c.confidence for c in chars)] * len(units)
            out.append(T.RecognizedWord(
                text=norm, units=units, unit_conf=unit_conf,
                start=chars[0].start_frame * self.frame_sec, end=chars[-1].end_frame * self.frame_sec))
        return out

    # --------------------------------------------------------- forced alignment
    def _char_ids(self, ch: str) -> list[int]:
        if ch in self.char_to_id:
            return [self.char_to_id[ch]]
        dec = unicodedata.normalize("NFD", ch)
        if dec != ch and all(c in self.char_to_id for c in dec):
            return [self.char_to_id[c] for c in dec]
        return []

    def expected_evidence(self, lp: np.ndarray, words: list[T.PassageWord]) -> list[T.ExpectedEvidence] | None:
        """Force-align the passage and score every expected unit.

        Returns None if the recording is too short to fit the passage.
        """
        targets: list[int] = []
        owner: list[tuple[int, int]] = []  # (word, unit) per target token; (-1,-1) for delimiters
        for wi, w in enumerate(words):
            if wi > 0 and self.delim_id is not None:
                targets.append(self.delim_id)
                owner.append((-1, -1))
            for ui, u in enumerate(w.units):
                for ch in u.text:
                    for tid in self._char_ids(ch):
                        targets.append(tid)
                        owner.append((wi, ui))
        if not targets:
            return None
        path = ctc_forced_align(lp, np.asarray(targets), self.blank_id)
        if path is None:
            return None
        ev = [T.ExpectedEvidence(unit_gop=[None] * len(w.units)) for w in words]
        n_frames = lp.shape[0]
        competitor_mask = np.ones(lp.shape[1], dtype=bool)
        competitor_mask[self.blank_id] = False
        for i in self._ignored:
            competitor_mask[i] = False
        if self.delim_id is not None:
            competitor_mask[self.delim_id] = False
        for k, frames in enumerate(path):
            wi, ui = owner[k]
            if wi < 0 or not frames:
                continue
            tok = targets[k]
            lo = max(0, frames[0] - GOP_WINDOW)
            hi = min(n_frames, frames[-1] + 1 + GOP_WINDOW)
            gop = expected_text_score(lp[lo:hi], tok, competitor_mask)
            cur = ev[wi].unit_gop[ui]
            ev[wi].unit_gop[ui] = gop if cur is None else min(cur, gop)
            st, en = frames[0] * self.frame_sec, (frames[-1] + 1) * self.frame_sec
            if ev[wi].start is None or st < ev[wi].start:
                ev[wi].start = round(st, 3)
            if ev[wi].end is None or en > ev[wi].end:
                ev[wi].end = round(en, 3)
        return ev


GOP_WINDOW = 2  # frames of tolerance around the forced-aligned span
PRESENCE_FLOOR = float(np.log(0.05))  # target posterior below 5% counts as absent


def expected_text_score(seg: np.ndarray, tok: int, competitor_mask: np.ndarray) -> float:
    """Goodness-of-pronunciation style score for one expected token.

    ``seg`` holds log-probabilities for the frames the passage token was
    force-aligned to (plus a small window). The score is

        at the frame t* where the target is most likely:
        min( log p(target) - log p(best competing character),
             log p(target) - log 0.05 )

    * clearly said:   target dominates the competitors      -> large positive
    * said, but CTC chose blank: target still beats letters -> positive
    * substituted:    another letter dominates               -> negative
    * skipped:        target posterior is tiny               -> negative

    Blank is not a competitor, because CTC emits blank on most frames even
    when the sound is present.
    """
    t_star = int(np.argmax(seg[:, tok]))  # frame where the target is most likely
    row = seg[t_star]
    target = float(row[tok])
    mask = competitor_mask.copy()
    mask[tok] = False
    comp = float(row[mask].max()) if mask.any() else -1e9
    return float(np.clip(min(target - comp, target - PRESENCE_FLOOR), -10.0, 10.0))


def ctc_forced_align(lp: np.ndarray, targets: np.ndarray, blank: int) -> list[list[int]] | None:
    """Viterbi CTC alignment. Returns, for each target token, the frames assigned to it."""
    T_, L = lp.shape[0], len(targets)
    S = 2 * L + 1
    repeats = int(np.sum(targets[1:] == targets[:-1])) if L > 1 else 0
    if T_ < L + repeats:
        return None
    labels = np.full(S, blank, dtype=np.int64)
    labels[1::2] = targets
    # skip transition s-2 -> s allowed for token states whose label differs from s-2
    can_skip = np.zeros(S, dtype=bool)
    can_skip[3::2] = targets[1:] != targets[:-1]
    NEG = -1e30
    alpha = np.full(S, NEG)
    alpha[0] = lp[0, labels[0]]
    alpha[1] = lp[0, labels[1]]
    back = np.zeros((T_, S), dtype=np.int8)
    for t in range(1, T_):
        stay = alpha
        prev1 = np.concatenate(([NEG], alpha[:-1]))
        prev2 = np.concatenate(([NEG, NEG], alpha[:-2]))
        prev2 = np.where(can_skip, prev2, NEG)
        stacked = np.stack([stay, prev1, prev2])
        arg = stacked.argmax(axis=0)
        alpha = stacked[arg, np.arange(S)] + lp[t, labels]
        back[t] = arg
    end = S - 1 if alpha[S - 1] >= alpha[S - 2] else S - 2
    if alpha[end] <= NEG / 2:
        return None
    frames: list[list[int]] = [[] for _ in range(L)]
    s = end
    for t in range(T_ - 1, -1, -1):
        if s % 2 == 1:
            frames[(s - 1) // 2].append(t)
        s -= int(back[t, s])
    for f in frames:
        f.reverse()
    return frames
