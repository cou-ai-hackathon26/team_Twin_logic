# PoraBondhu AI (পড়াবন্ধু AI)

A Bangla reading diagnostician for primary teachers. A child reads a short passage
aloud; PoraBondhu marks every word (correct, misread, skipped, unsure), traces each
error to the Bangla written unit behind it (যুক্তাক্ষর, কার, ফলা, রেফ, চন্দ্রবিন্দু),
and tells the teacher which patterns each child needs next. The teacher can
correct any mark with one tap.

**Everything runs on a CPU, with no language-model API.** Run locally, no audio
leaves the computer. In the hosted demo, audio goes only to our own server
(the Hugging Face Space) and is never sent to a third party.

| | |
|---|---|
| **Event** | CoU AI Hackathon 2026, Comilla University |
| **Team** | Twin logic (duo) |
| **Members** | [MEMBER 1 NAME] (speech models, benchmark, deployment) · [MEMBER 2 NAME] (grapheme and alignment engines, backend, interface) |
| **Domain** | Education (primary), Accessibility (secondary) |
| **Live demo** | **https://safu58-porabondhu.hf.space** (open it directly so the microphone works; the [Space page](https://huggingface.co/spaces/safu58/porabondhu) shows the build) |
| **Demo video** | [ADD LINK, 3 minutes max] |
| **Repository** | https://github.com/mohammadyaksafu/porabondhu-ai |

### Test logins for the live demo

| Role | Username | Password |
|---|---|---|
| Teacher | `teacher` | `teacher123` |
| Student (class 3, roll 01) | `c3r01` | `student123` |

Any student `c1r01` … `c5r05` works with `student123`. The free Space keeps no
data between restarts: every restart brings back the clean demo accounts. The
first reading after a restart takes longer while the models load.

## Problem

About half of Grade 3 and Grade 5 students in Bangladesh do not read Bangla at
grade level (National Student Assessment 2022, DPE), and the World Bank (2024)
estimates that 51% of late-primary children cannot read and understand a simple
text. A teacher with 50 to 60 students cannot listen to each child read, weak
readers stay hidden, and a teacher who knows a child reads poorly still does not
know *why*: the difficulty is usually specific conjuncts, vowel signs or sounds.

## Solution

1. **Listen.** The child reads a short graded passage aloud in the browser.
2. **Mark.** A character-level Bangla speech model (no language model, so it does
   not "fix" the child's mistakes) transcribes the reading, and our alignment
   engine marks every word: correct, misread, skipped, repeated, hesitated or unsure.
3. **Diagnose.** Each error is traced to the written unit behind it (যুক্তাক্ষর,
   কার, র-ফলা, য-ফলা, রেফ, চন্দ্রবিন্দু). Repeated errors become candidate weak patterns.
4. **Inform the teacher.** Speed (WCPM), accuracy, a mark out of 10, weak
   patterns, practice words and a class pattern map. The teacher confirms or
   corrects any mark with one tap and has the final word.

## Features

* Teacher and student logins; classes and students by roll code (no names stored)
* In-browser recording (16 kHz WAV) with an audio quality check
* Marked passage with a per-word inspector: heard vs expected unit by unit,
  Bangla diagnosis, both confidence signals, and playback of just that word
* Student progress (WCPM and accuracy over time), weak patterns, practice suggestions
* Class pattern map: which units most children misread
* "Listen first" model reading for students (neural TTS, word highlighting)
* Side-by-side comparison with Whisper and plain CTC on the same audio
* Live grapheme engine page (normaliser, segmenter, unit diff)
* English passages (marked by Whisper) next to Bangla
* Evaluation scripts: calibration on tuning speakers, benchmark with 95% CIs

## Tech stack, models and data

| Part | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, TanStack Query, Recharts |
| Backend | Python 3.10, FastAPI, SQLAlchemy (SQLite, or PostgreSQL) |
| Speech model | [arijitx/wav2vec2-xls-r-300m-bengali](https://huggingface.co/arijitx/wav2vec2-xls-r-300m-bengali) (Apache-2.0), exported by us to ONNX int8: [safu58/porabondhu-wav2vec2-bn-onnx-int8](https://huggingface.co/safu58/porabondhu-wav2vec2-bn-onnx-int8) |
| Baseline and English | OpenAI Whisper `small` via faster-whisper (CTranslate2, int8) |
| Model reading (TTS) | Microsoft Edge neural voices via edge-tts (passage text only) |
| Team-built AI parts | Bangla normaliser and grapheme segmenter, weighted word/unit alignment, CTC forced alignment and expected-text score, two-signal marking, weak-pattern tracking |
| Passages | 30 Bangla and 25 English graded passages, Grades 1-5 (`backend/app/seed/passages.json`) [ADD SOURCE: written by the team, or which textbook/source] |
| Evaluation data | So far only a TTS-generated test set that checks the scripts run; human-recorded results are listed under [Evaluation](#evaluation) once measured |
| Hosting | Hugging Face Spaces (Docker, free CPU), built from this repository's `Dockerfile` |

## AI tools used

| Tool | What we used it for |
|---|---|
| Claude (Anthropic), through Claude Code | Helping write and review code, tests, scripts and documentation, and helping with deployment setup. We designed the system and can explain every part |

No language-model API is called by the app itself.

---

## Quick start (Windows)

Requirements: Python 3.10+, Node 20+, ~3 GB free disk, 8 GB+ RAM. ffmpeg is
optional (only for uploading mp3/m4a/webm files; in-app recording does not need it).

```powershell
.\setup.ps1      # venv, CPU PyTorch, model download + ONNX int8 export, tests, frontend build
.\start.ps1      # http://localhost:8000
.\start.ps1 -Dev # backend with reload + Vite dev server on http://localhost:5173
```

Manual steps (any OS):

```bash
cd backend
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python -m scripts.export_onnx                      # optional but ~2x faster on CPU
python -m pytest -q
uvicorn app.main:app --port 8000

cd ../frontend && npm install && npm run build      # served by the backend at :8000
```

Docker (the same image as the live demo, no PyTorch needed):

```bash
docker build -t porabondhu .
docker run -p 7860:7860 porabondhu   # http://localhost:7860
```

Deploy the committed code to the Hugging Face Space (needs `huggingface-cli login`):
`backend/.venv/Scripts/python deploy/push_space.py`

PostgreSQL instead of SQLite: `docker compose up -d db` and set
`PB_DATABASE_URL` in `backend/.env` (see `.env.example`).

## Using it

1. **Classes** → create a class, add students by roll number (no names stored).
2. **New assessment** → choose child and passage → **Start reading**. The child
   sees only the passage, a big record button and encouragement afterwards.
3. **Review** → the marked passage. Click any word (or use ← → and keys 1-4)
   to see heard vs expected unit by unit, the diagnosis in Bangla, both
   confidence signals, and to listen to just that word. Finalise; audio is
   deleted unless you keep it.
4. **Student page** → WCPM/accuracy over time, grapheme pattern counts,
   candidate weak patterns and practice words/passages from the bank.
5. **Class page** → class pattern map: which units most children misread.
6. **Baseline comparison** on any reading with kept audio runs Whisper and
   plain CTC on the same audio, side by side.
7. **Grapheme engine** page shows the normaliser/segmenter/diff live.

## How the AI works

```
audio ─► quality check ─► wav2vec2 CTC (Bangla, CPU, ONNX int8)
                              │ frame log-probabilities (20 ms)
              ┌───────────────┴────────────────┐
     greedy decoding, no LM            CTC forced alignment of the passage
     (what was actually said,          (expected-text score per unit,
      char confidence, times)           covers skipped units, word times)
              └───────────────┬────────────────┘
        Bangla grapheme engine: normalise → segment into units
        weighted alignment: words (with merge/split) → units
        diagnosis: which reph / phala / conjunct / kar / sign differs
        decision: error | correct | unsure (two signals must agree)
              │
        WCPM, accuracy, hesitation (≥3 s), repetitions, not-reached
        weak patterns = repeated confirmed errors across readings
```

* **Error-preserving recognition.** Character-level CTC with greedy decoding
  has no language model to "fix" the child's mistake into the expected word.
  This is a hypothesis we test against Whisper, not a claim.
* **Two confidence signals.** Free-decoding confidence (mean posterior of each
  emitted character) and an expected-text score (at the frame where the
  passage character is most likely: its log-probability minus the best
  competing character, capped by an absence floor). An error is marked only
  when the decoder confidently heard something else *and* the passage text
  fits the audio poorly; if the passage fits well it is correct; otherwise
  **unsure**, which is shown to the teacher and never counted as an error.
* **Spelling-only differences are not errors.** স/শ/ষ, ি/ী, ু/ূ, ন/ণ, জ/য, ত/ৎ
  sound the same in reading, so a difference only between them is ignored.
  Phonetic similarity is used only to pick the right alignment, never to
  excuse a real substitution.
* **Thresholds** are tuned on tuning speakers only (`scripts/calibrate.py`)
  and saved to `data/thresholds.json`; test speakers are never used for tuning.

## Evaluation

```bash
cd backend
python -m scripts.annotation_template eval/recordings.csv eval/annotations.csv
python -m scripts.calibrate  --recordings eval/recordings.csv --annotations eval/annotations.csv
python -m scripts.benchmark  --recordings eval/recordings.csv --annotations eval/annotations.csv
```

Three systems on the same recordings: Whisper + word compare, Bangla CTC + word
compare, PoraBondhu. Reports recall, precision, false alarms, unsure rate,
grapheme error accuracy, WCPM MAE and Spearman, uncertainty coverage,
CER/WER, Cohen's kappa and processing time, each percentage with counts and a
95% Wilson interval, adults and children separately, plus a pass/fail table
against the success criteria fixed in the proposal. See
[docs/DATA_COLLECTION.md](docs/DATA_COLLECTION.md).

`scripts/make_synthetic_set.py` builds a TTS-generated set **only to check that
the scripts run**. Its numbers are not results and must not be reported.

**Results:** _not measured yet. Fill in after running the benchmark on the
human-annotated recordings._

Measured on the development laptop (Intel i5-10310U, 4 cores, no GPU):
ONNX int8 CTC processes ~14 s of audio in ~4.5 s, i.e. roughly 18-20 s per
60 s reading (target ≤ 15 s; use `PB_TORCH_THREADS` and close other apps).
The PyTorch fp32 path is ~2x slower.

## Child-voice adaptation (optional)

`scripts/adapt_child_voice.py` fine-tunes the top transformer layers on public
adult Bangla speech transformed to sound child-like (pitch shift + vocal tract
length perturbation). `--preview-dir` writes before/after samples to listen to.
Then set `PB_CTC_MODEL_ID` to the output folder and re-run
`scripts/export_onnx.py --model <folder>`. If it does not help on the tuning
speakers, keep the public checkpoint and say so.

## Project layout

```
backend/
  app/
    bangla/        normaliser, segmenter, phonetics + unit diff, pattern labels
    alignment/     weighted edit distance, word (merge/split) and unit alignment
    assessment/    marking rules, metrics (WCPM), weak patterns, word-compare baseline
    speech/        audio I/O + quality check, CTC recogniser (torch/ONNX), Whisper, model registry
    evaluation/    dataset loader, scoring, statistics (Wilson CI, kappa, Spearman)
    services/      reading lifecycle (background worker), analytics/recommendations
    api/           FastAPI routes and serializers
    pipeline.py    one function per system, shared by the app and the benchmark
    models.py      SQLAlchemy tables (SQLite or PostgreSQL)
    seed/          30 Bangla + 25 English graded passages (Grades 1-5)
  scripts/         export_onnx, calibrate, benchmark, annotation_template,
                   adapt_child_voice, make_synthetic_set, smoke_test
  tests/           engine unit tests
frontend/          React 19 + TypeScript + Tailwind 4 + TanStack Query + Recharts
  src/api/         typed client, types, query hooks
  src/lib/         WAV recorder (AudioWorklet, 16 kHz), formatting
  src/components/  UI primitives, layout, domain chips
  src/features/    classes, students, assess (+ child view), review, passages,
                   engine, benchmark, settings
```

## Privacy and safety

* Students are a roll code and optional nickname; no names, faces or dates of birth.
* Audio is kept only until the teacher finalises the review, unless they keep it.
* The child sees encouragement only, never marks, scores or rankings.
* The teacher has the final word on every mark. PoraBondhu is a teacher's aid,
  not a validated assessment instrument.

## Limitations

* The CTC model can still miss or invent errors; uncertain cases are shown as unsure.
* Public Bangla speech is mostly adult; child results come from a small sample.
* Regional accents may appear as errors until added as accepted variants.
* Whisper `small` often writes Bangla in Devanagari; the baseline maps it back
  to Bengali script by Unicode block offset before comparing.

## Credits and third-party components

* Speech model: [arijitx/wav2vec2-xls-r-300m-bengali](https://huggingface.co/arijitx/wav2vec2-xls-r-300m-bengali) (check the model card for its licence), built on Meta XLS-R.
* Baseline: OpenAI Whisper via [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
* Libraries: PyTorch, Hugging Face Transformers, ONNX Runtime, FastAPI, SQLAlchemy,
  librosa, SciPy, React, Vite, Tailwind CSS, TanStack Query, Recharts, lucide-react,
  Noto Sans Bengali and Inter fonts (Fontsource).
* Synthetic smoke-test audio (not results): Microsoft Edge neural TTS via edge-tts.
* AI coding assistant: Claude (Anthropic) was used to help write code and docs.

## Logins, English reading and marks

**Two roles.** Every page needs a login. On the first start (while the users table is empty) the app seeds demo accounts:

| Role | Username | Password | Can do |
|---|---|---|---|
| Teacher | `teacher` | `teacher123` | everything: classes, students, passages, assessments, review |
| Student | `c1r01` … `c5r05` (class N, roll NN) | `student123` | take reading tests for their own grade, see their own marks |

It also creates `Class 1` … `Class 5` (one per grade) with five students each. A teacher can create, change or remove a student's login on that student's page. Change the demo passwords before real use, or set `PB_SEED_DEMO=false`.

**English.** Each grade has Bangla passages (`P01`–`P30`) and English passages (`E01`–`E25`). English readings are marked by Whisper in English (greedy decoding, no carried-over context) plus a letter-distance word alignment. The grapheme engine, weak-pattern analysis and system comparison stay Bangla-only.

**Marks.** Every reading test gets a mark out of 10: words read correctly ÷ words in the passage × 10, to one decimal. Skipped, misread and not-reached words earn nothing, and unsure words count as correct (same as accuracy, see `PB_COUNT_UNSURE_AS_CORRECT`). The mark updates when the teacher corrects a word.
