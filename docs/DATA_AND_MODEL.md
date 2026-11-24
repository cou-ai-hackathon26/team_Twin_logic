# Data, model and architecture: what we used, what we built, and why

This page answers three questions directly:

1. **What data did we use, and why no children's speech?**
2. **What did we train, fine-tune or tune, and what did we not?**
3. **What is the architecture, from the microphone to the teacher's screen?**

Everything here can be checked in the repository; file paths are given for each claim.

---

## 1. The data problem, stated plainly

PoraBondhu is for children aged 6-10 reading Bangla aloud. The ideal data would be **recordings of
Bangla-speaking children reading graded passages, with every word labelled correct, misread or skipped
by trained annotators, released under an open licence with parental consent**.

**We did not find such a dataset openly available.** The open Bangla speech corpora we found (for example
FLEURS) are mostly adult speech, and none we found labels children's reading errors at the word or letter level.
Recording children ourselves needs written parental consent, a safe data protocol and time we did not
have in a three-day build, and we decided not to collect children's voices without those safeguards
(see [DATA_PROTECTION.md](DATA_PROTECTION.md) and the consent-based plan in
[DATA_COLLECTION.md](DATA_COLLECTION.md)).

So we had to build and evaluate a children's reading diagnostician **without children's data**. Every
engineering choice below follows from that constraint.

### What we used instead

| Data | What it is | Licence | How we used it | Where |
|---|---|---|---|---|
| **Google FLEURS Bengali** (`bn_in`) | Native **adult** speakers reading sentences **correctly** | CC BY 4.0 | 120 *dev* recordings for tuning only; the first 100 *test* recordings for every reported result | `backend/scripts/make_public_set.py`, `results/` |
| **Simulated reading errors** | We change the *expected text* the system is given, so the real speech no longer matches it (letter swaps in কার / ফলা / যুক্তাক্ষর / রেফ, deletions, whole-word changes). Labels are exact by construction | ours | Error detection with known ground truth | `make_public_set.py`, `make_robustness_sets.py` |
| **Robustness sets** (built from the same test speakers) | Unseen error types (random consonant swaps, real-word substitutions); real skips made by **cutting word audio out**; a **child-like voice proxy** (pitch and formants raised 10-20% by resampling) | ours | Checks that we are not only finding our own perturbations, and how a higher voice affects the model | `make_robustness_sets.py`, `make_childlike_resample.py` |
| **Trust-test sets** | The same recordings mixed with classroom **babble** (three other speakers) at 20/10/5 dB and **hiss** at 10 dB; a **simulated regional accent** | ours | Measures the noise / accent / odd-word guards, guards off vs on | `scripts/eval_noise_accent.py`, `results/noise_accent.json` |
| **Graded passages** | 42 Bangla + 25 English passages, Grades 1-5; T01-T12 follow the NCTB *আমার বাংলা বই* lessons (page cited, no textbook text copied) | ours (AI-assisted writing) | What children read | `backend/app/seed/`, [CURRICULUM_ALIGNMENT.md](CURRICULUM_ALIGNMENT.md) |
| **Demo history** | Scripted errors run through the real marking engine, **no audio**, model id `demo-seed (simulated)`, labelled **DEMO · simulated** in the app | ours | Only so the dashboards are not empty | `backend/app/seed/demo.py` |
| **Children's speech** | **None.** No child has been recorded | | Planned, with consent, for testing only | [DATA_COLLECTION.md](DATA_COLLECTION.md) |

**Honest limit:** every accuracy number in this project is adult speech with simulated errors. It shows
the method works on real Bangla speech; it does **not** prove accuracy on children.

---

## 2. Engineering we did *because* there is no child data

Without child data we could not train a children's model end to end. Instead we designed a system that
(a) uses a strong public Bangla speech model without retraining it, (b) makes as few decisions as possible
that depend on child-specific acoustics, and (c) hands every doubtful decision to the teacher.

| # | Design choice | Why it follows from "no child data" |
|---|---|---|
| 1 | **No language model in decoding** (character-level CTC, greedy) | A language model "corrects" a child's slip into the expected word. With no child data to tune that away, we remove it entirely so the error survives |
| 2 | **Two independent signals per letter unit**: what was heard (free decoding confidence) and how well the passage text fits the audio (our forced-alignment *expected-text score*) | One signal from an untuned model is unreliable on new voices; an error is called only when both agree |
| 3 | **Abstention ("unsure")** built into the decision | When the signals disagree the word goes to the teacher and is never counted as an error. Wrong marks harm children more than missed ones |
| 4 | **Bangla grapheme engine** (our own normaliser, segmenter, unit diff) | Diagnosis is done in text space (which কার / ফলা / যুক্তাক্ষর differs), which does not need child acoustics at all |
| 5 | **Spelling-only differences ignored** (স/শ/ষ, ি/ী, ন/ণ, জ/য …) | They sound the same; no audio model can tell them apart, child or adult |
| 6 | **Thresholds tuned on separate speakers, tested once** with confidence intervals | With small data the risk is overfitting; we kept dev and test apart and report intervals and misses |
| 7 | **Child-like voice proxy + a control** | The closest honest test we could make. A first proxy (phase-vocoder pitch shift) looked catastrophic (13% recall) until a control (shift up and back down) showed the **tool** caused it; the valid resampling proxy loses about 3 points of recall. We report both |
| 8 | **Test-time voice normalisation** tried and **rejected** | It did not help (child-like recall 13.5% → 14.9%, adult unchanged), so it is not used (`app/speech/voicenorm.py`, `scripts/voicenorm_experiment.py`) |
| 9 | **Child-voice fine-tuning script** prepared, **not used** | `scripts/adapt_child_voice.py` can fine-tune the top transformer layers on adult speech made child-like. Without real child test data we cannot show it helps, so the app uses the public checkpoint and we do not claim a gain |
| 10 | **Learning from teacher reviews, on the device** | The teacher becomes the source of labels: a pronunciation teachers accept 3 times becomes an accepted variant; after 10 reviewed readings the decision cut-off is re-tuned to agree with teachers (false alarms kept ≤ 5%, one-click undo). No audio is kept or sent anywhere |
| 11 | **Trust guards** for noise, regional accent and odd words | Children read in noisy classrooms and with regional accents we could not record. Suspicious words become "unsure" for the teacher instead of errors (measured cost: recall 87.9% → 70.7% on clean audio, accent false alarms 86.1% → 28.7%) |
| 12 | **Replay for teacher correction** (Word / In context / Compare / slow / Quick check) | If the AI cannot be fully trusted on children yet, the teacher must be able to check any mark in seconds by ear |
| 13 | **Ready-to-run child data protocol** | Consent, roll codes only, annotation format and scripts are ready (`DATA_COLLECTION.md`, `scripts/annotation_template.py`); `scripts/benchmark.py` reports children separately as soon as recordings exist |

---

## 3. What we trained, fine-tuned and tuned, and what we did not

| Component | Status | Details | Evidence |
|---|---|---|---|
| Speech model (wav2vec2 XLS-R 300M, Bangla CTC) | **Not fine-tuned.** Public checkpoint `arijitx/wav2vec2-xls-r-300m-bengali` (Apache-2.0) | No consented child data, CPU only. Fine-tuning on adult data would not address the child gap | README "Tech stack" |
| ONNX export + **int8 quantisation** | **Built by us** | Exported to ONNX and quantised to int8 MatMul weights: about 2× faster on CPU, no PyTorch on the server. Published as `safu58/porabondhu-wav2vec2-bn-onnx-int8` | `scripts/export_onnx.py` |
| **Word-error classifier** | **Trained by us** | Logistic regression on **18 evidence features** per flagged word (free-decoding confidence of the differing units, unit-level expected-text scores, number and share of differing units, deletions, insertions, repeats, duration …). Trained on the 120 FLEURS **tuning** recordings only (896 flagged words, 315 real errors); cut-off chosen by 5-fold cross-validation (false alarms ≤ 5%, best F1). Tested **once** on the 100 held-out test recordings: precision 76.1% → **80.8%** (+4.7, 95% CI +0.9 to +8.2), false alarms 4.2% → **3.2%**, recall unchanged within noise. Used by the app | `scripts/word_classifier.py`, `results/word_classifier.json` |
| **Decision thresholds + temperature** | **Calibrated by us** | Wide grid search with 3-fold cross-validation on dev speakers: free-decoding confidence 0.3, expected-text high 0.1 / low −3.0, logit temperature 2.0. CV: precision 81% ± 2, recall 82% ± 6, false alarms 3.3% ± 0.4 | `scripts/calibrate_wide.py`, `results/thresholds.json`, `results/calibration_wide.json` |
| **Expected-text score** (goodness-of-pronunciation style) | **Designed by us** | See section 4.3 | `app/speech/ctc.py` |
| **Bangla grapheme engine** | **Built by us** | Normaliser, akshara-level segmenter (conjuncts, ফলা, রেফ, কার, signs), weighted word/unit alignment, unit diff with Bangla diagnosis | `app/bangla/`, `app/alignment/` |
| **Trust guards** | **Built and measured by us** | Accent, noise (per-word level above local noise + spectral flatness), odd words | `app/assessment/robust.py`, `results/noise_accent.json` |
| **On-device learning from reviews** | **Built by us** | Accepted variants and threshold / cut-off re-tuning from teacher corrections | `app/services/learning.py` |
| Whisper `small` | Used as an **unmodified baseline** (and for English passages) | Not tuned; on this Bengali data about 80% character errors, so it is not a strong baseline, and we say so | `results/EVALUATION.md` |
| Child-voice adaptation | **Prepared, not used** | See section 2, row 9 | `scripts/adapt_child_voice.py` |

---

## 4. Architecture

### 4.1 System overview

```
 ┌─────────────────────────── Browser (React + TypeScript) ───────────────────────────┐
 │ Teacher: classes · assess · review (replay, compare, quick check) · patterns ·      │
 │          practice · benchmark · settings          Student: read · AI result ·       │
 │ Admin: schools, accounts                          practice · progress               │
 │ District officer: counts per school only                                            │
 └───────────────▲────────────────────────────────────────────────┬────────────────────┘
                 │ HTTPS (Caddy, Let's Encrypt) · cookie session   │ 16 kHz WAV upload
 ┌───────────────┴────────────────────── FastAPI backend ──────────▼────────────────────┐
 │ auth + roles · classes/students · readings API · review/finalise · learning ·         │
 │ district summary (groups < 5 hidden) · metrics (local only)                          │
 │                                                                                      │
 │ background marking workers (queue; 1 worker by default) ──► MARKING PIPELINE (4.2)  │
 │                                                                                      │
 │ SQLite / PostgreSQL: readings, word marks (AI decision + teacher decision kept side  │
 │ by side), accepted variants, tricky words, assignments. Audio: deleted on finalise   │
 │ or after 14 days.                                                                    │
 └──────────────────────────────────────────────────────────────────────────────────────┘
 Runs fully offline on a laptop CPU; the hosted demo is the same Docker image on a 2-core VPS.
```

### 4.2 The marking pipeline (one recording)

```
 child's audio (16 kHz)
   │
   ├─ 1. Quality check ── too quiet / clipped / too noisy (SNR < 8 dB) → "read again" (no marks)
   │
   ├─ 2. Acoustic model: wav2vec2 XLS-R 300M Bangla CTC (ONNX int8, CPU)
   │        raw waveform → CNN feature encoder (20 ms frames) → 24 transformer layers
   │        → linear CTC head over Bangla characters + blank → log-probabilities per frame
   │        (long audio in 15 s chunks with 1 s context; temperature 2.0)
   │
   ├─ 3a. Free decoding (no language model)     3b. CTC forced alignment of the passage text
   │      greedy best path → what was SAID,           → start/end time of every passage word,
   │      per-character confidence and times          even skipped ones; expected-text score
   │                                                  per letter unit (4.3)
   │
   ├─ 4. Bangla grapheme engine
   │        normalise both texts → segment into units (প্র = প + র-ফলা, র্য = রেফ …)
   │        weighted word alignment (merges/splits) → unit alignment → unit diff:
   │        which কার / ফলা / যুক্তাক্ষর / রেফ / sign differs; spelling-only swaps ignored;
   │        accepted variants count as correct
   │
   ├─ 5. Decision per word
   │        rules: error only if the heard unit is confident AND the passage fits badly;
   │               correct if the passage fits well; otherwise UNSURE
   │        trained classifier (18 features) re-decides the flagged words (used: it beat the rules)
   │
   ├─ 6. Trust guards: possible regional accent → unsure ♪ · noisy word → unsure 〰 ·
   │        odd word without strong evidence → unsure ⚑ · per-word level above noise stored
   │
   └─ 7. Reading measures: words correct per minute, accuracy, hesitations (≥ 3 s), repeats,
            not-reached words, mark out of 10; weak patterns = the same unit wrong ≥ 3 times
            across ≥ 2 readings → class pattern map → practice linked to the NCTB lesson
```

Then the **teacher review loop**: every word keeps the AI decision and the teacher decision side by
side; the teacher replays and corrects; corrections feed the on-device learning (variants, cut-off).

### 4.3 The expected-text score (our "goodness of pronunciation")

For each letter unit of the passage, forced alignment gives the frames where it should be. At the frame
**t\*** where the expected character is most likely:

```
score = min( log p(expected) − log p(best competing character),
             log p(expected) − log 0.05 )            clipped to [−10, 10]
```

* clearly said → large positive; substituted → another letter dominates → negative;
  skipped → the expected character is nearly absent → negative.
* **Blank is not a competitor**: CTC emits blank on most frames even when the sound is present, so
  comparing with blank would measure timing, not which letter was said.
* **Temperature 2.0** softens the very peaky CTC posteriors so the score is not saturated.

### 4.4 Why these pieces, in one sentence each

* **wav2vec2 + CTC:** character-level output keeps the child's actual letters; it runs on a CPU.
* **No language model:** so the system hears the mistake instead of the expected word.
* **Forced alignment:** gives word times for replay and a second, independent piece of evidence.
* **Grapheme engine:** turns "wrong word" into "which written unit to teach".
* **Abstention + teacher review:** the honest answer to having no child data.
* **Small trained classifier, not a big model:** 896 training words; logistic regression does not
  overfit and every weight can be inspected.

---

## 5. Results in one table (adult speech, simulated errors; not children)

| Measure (100 FLEURS test recordings unless stated) | Value |
|---|---|
| Plain CTC + word compare (same speech model, no PoraBondhu layer) | precision 27.4%, false alarms 43.1% |
| PoraBondhu, hand-set rules | recall 82.4%, precision 76.1%, false alarms 4.2%, unsure 17.7% |
| PoraBondhu, trained classifier (used) | recall 81.7%, precision **80.8%**, false alarms **3.2%** |
| Child-like voice proxy (resampling) | recall about 3 points lower |
| Trust guards on (60 recordings) | accent false alarms 86.1% → 28.7%; recall 87.9% → 70.7% (cost reported) |
| Speed (4-core laptop, 60 s reading) | 15.5 s (target 15 s, missed by about 0.5 s) |

Full tables with counts and 95% intervals: [`backend/results/EVALUATION.md`](../backend/results/EVALUATION.md).

## 6. What changes when child data exists

1. Record children with written parental consent using [DATA_COLLECTION.md](DATA_COLLECTION.md)
   (roll codes only; testing only).
2. Report children separately with `scripts/benchmark.py` (the format is ready).
3. Only then try child-voice fine-tuning (`scripts/adapt_child_voice.py`) and keep it **only if** it
   beats the public checkpoint on held-out children.
4. Re-tune thresholds, the classifier cut-off and the trust guards on child data; keep the teacher's
   final word.
