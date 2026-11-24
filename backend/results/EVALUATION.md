# PoraBondhu evaluation (FLEURS Bengali, real adult speech, simulated reading errors)

Generated 2026-11-23T00:13 UTC from `fleurs_test100_20261122_173539.json`.

**What this is:** native adult speakers reading Wikipedia sentences correctly (Google FLEURS bn_in, CC BY 4.0). Reading errors are simulated by changing the expected text the system is given (`scripts/make_public_set.py`). Thresholds were tuned on FLEURS **dev** recordings only; results below are on the first 100 FLEURS **test** recordings. FLEURS has no speaker IDs, so speaker separation between dev and test cannot be verified; dev and test use different sentences.

**What this is not:** not children, not authentic misreadings, not classroom audio. Labels are generated, so there is no inter-annotator agreement.

## Main comparison (100 test recordings)

| System | Recall | Precision | False alarms | Unsure | s per 60 s |
|---|---|---|---|---|---|
| porabondhu | 82.4% (216/262; 95% CI 77-87%) | 76.1% (216/284; 95% CI 71-81%) | 4.2% (68/1608; 95% CI 3-5%) | 17.7% (331/1870; 95% CI 16-19%) | 16.21 |
| whisper_word | 100.0% (262/262; 95% CI 99-100%) | 14.6% (262/1791; 95% CI 13-16%) | 95.1% (1529/1608; 95% CI 94-96%) | 0.0% (0/1870; 95% CI 0-0%) | 264.9 |
| ctc_word | 100.0% (262/262; 95% CI 99-100%) | 27.4% (262/955; 95% CI 25-30%) | 43.1% (693/1608; 95% CI 41-46%) | 0.0% (0/1870; 95% CI 0-0%) | 15.8 |

Paired differences (bootstrap over recordings, 95% CI; percentage points):

* **porabondhu_minus_whisper_word** (n=100): recall -17.6 (-22.6 to -12.9) *; precision +61.4 (+56.3 to +66.1) *; false_alarm -90.9 (-92.3 to -89.1) *; unsure_rate +17.7 (+15.6 to +19.9) *
* **porabondhu_minus_ctc_word** (n=100): recall -17.6 (-22.6 to -12.9) *; precision +48.6 (+44.3 to +52.7) *; false_alarm -38.9 (-42.2 to -35.6) *; unsure_rate +17.7 (+15.6 to +19.9) *
* **childlike_minus_original** (n=100): recall -69.1 (-75.4 to -63.0) *; precision -56.2 (-62.7 to -49.0) *; false_alarm +4.5 (+2.6 to +6.6) *; unsure_rate +36.8 (+29.8 to +43.4) *
* **childlike_rs_minus_original** (n=100): recall -3.0 (-6.3 to +0.0); precision -1.5 (-6.4 to +3.2); false_alarm +0.2 (-0.8 to +1.2); unsure_rate +4.0 (+2.3 to +5.6) *

\* = interval excludes zero.

## Robustness (PoraBondhu only, 100 FLEURS test recordings each)

| Set | What changes | Recall | Precision | False alarms | Unsure |
|---|---|---|---|---|---|
| original | nothing (paired reference) | 82.4% (216/262; 95% CI 77-87%) | 76.1% (216/284; 95% CI 71-81%) | 4.2% (68/1608; 95% CI 3-5%) | 17.7% (331/1870; 95% CI 16-19%) |
| childlike_rs | child-like voice by resampling x1.10-1.20 (pitch + formants up, no vocoder artifacts) | 79.4% (208/262; 95% CI 74-84%) | 74.6% (208/279; 95% CI 69-79%) | 4.4% (71/1608; 95% CI 4-6%) | 21.7% (405/1870; 95% CI 20-24%) |
| unseen | error types the detector was not designed around | 90.2% (194/215; 95% CI 86-94%) | 74.3% (194/261; 95% CI 69-79%) | 4.2% (67/1594; 95% CI 3-5%) | 17.6% (319/1809; 95% CI 16-19%) |
| skipcut | real skips: word audio cut out | 76.9% (113/147; 95% CI 69-83%) | 63.5% (113/178; 95% CI 56-70%) | 3.9% (65/1662; 95% CI 3-5%) | 18.5% (335/1809; 95% CI 17-20%) |
| childlike | phase-vocoder child-like voice (confounded by processing artifacts, see notes) | 13.4% (35/262; 95% CI 10-18%) | 19.9% (35/176; 95% CI 15-26%) | 8.8% (141/1608; 95% CI 7-10%) | 54.5% (1019/1870; 95% CI 52-57%) |

Child-like sets are signal-processing proxies, **not** child speech.

* The first child-like set ('childlike') used phase-vocoder pitch shifting. Control on 20 dev recordings: shifting pitch +4 then -4 semitones (no net change) already dropped recall from 87.5% to 22.9%, so that set mostly measures processing artifacts. 'childlike_rs' (plain resampling, pitch and formants x1.10-1.20, 10-20% faster) is the better proxy. Neither is child speech.
* Test-time voice normalisation by inverse phase-vocoder warps (app/speech/voicenorm.py, tuned on dev only, scripts/voicenorm_experiment.py) did not help (child-like recall 13.5% -> 14.9%, adult unchanged) and is not used by the app.

## Threshold tuning (dev recordings only)

* Wide search best: {'free_high': 0.3, 'gop_high': 0.1, 'gop_low': -3.0, 'temperature': 2.0, 'hesitation_sec': 3.0, 'not_reached_min_run': 3} (precision 0.805, recall 0.848, false alarms 0.036, unsure 0.161).
* Parameters at the edge of the searched grid: ['gop_high'].
* 3-fold cross-validation (tune on 2/3, test on 1/3): precision 0.810 ± 0.017, recall 0.823 ± 0.057, false alarms 0.033 ± 0.004, unsure 0.172 ± 0.043.

## Trained word classifier (added 23 Nov 2026; used by the app)

Logistic regression on 18 evidence features per flagged word (`app/assessment/learned.py`), trained on
the 120 FLEURS tuning recordings only (896 flagged words, 315 real errors); cut-off chosen by 5-fold
cross-validation on tuning data (false alarms ≤5%, then best F1, then fewest unsure). Run once on the
same first 100 test recordings as the main table (`scripts/word_classifier.py`,
`results/word_classifier.json`).

| | Recall | Precision | False alarms | Unsure |
|---|---|---|---|---|
| Rules (thresholds above) | 82.4% (216/262) | 76.1% (216/284) | 4.2% (68/1608) | 17.7% |
| Trained classifier | 81.7% (214/262) | 80.8% (214/265) | 3.2% (51/1608) | 0.0% |
| Paired difference (bootstrap, 95% CI, pp) | -0.8 (-4.3 to +2.6) | +4.7 (+0.9 to +8.2) * | -1.1 (-1.8 to -0.2) * | -17.7 * |

Cross-validated on tuning data: precision 84.4%, recall 83.9%, false alarms 2.7%. Same limits as above:
adult speech, simulated errors, no child speech.

## Speed (23 Nov 2026)

`scripts/speed_test.py`, one 60 s reading, 4-core / 8-thread laptop: 15.5 s median with
`PB_TORCH_THREADS=4` on repeated readings of the same passage (first reading ~16.8 s; default threads 18.4 s). The speech model alone ~15.2 s. Target ≤15 s: missed by
~0.5 s.

## Trust guards: background noise and regional accent (added 24 Nov)

Generated by `scripts/eval_noise_accent.py` (`results/noise_accent.json`) on the first 60 recordings of the robustness set (FLEURS test speakers; real adult speech, simulated reading errors). Each recording is decoded once per condition and the guards (`app/assessment/robust.py`) are applied to a copy of the same marks, so "off" and "on" are paired. Noise: three other test speakers mixed in at once (babble) or white noise (hiss) at the stated signal-to-noise ratio. Accent: in about a quarter of the words containing one of ব/ভ গ/ঘ দ/ধ ত/থ ক/খ প/ফ জ/ঝ চ/ছ ট/ঠ ড/ঢ র/ড় স/চ, the passage letter is changed so the speaker's real pronunciation is the regional form; those words count as correctly read.

| Condition (60 FLEURS test recordings) | False alarms, guards off → on | Recall, guards off → on | Unsure, off → on |
|---|---|---|---|
| No added noise | 3.8% → 3.2% (37 → 31 of 971) | 87.9% → 70.7% (138 → 111 of 157) | 0% → 2.9% |
| Classroom babble, 20 dB | 3.3% → 2.7% | 85.4% → 71.3% | 0% → 2.5% |
| Classroom babble, 10 dB | 3.9% → 3.4% | 75.2% → 64.3% | 0% → 2.0% |
| Classroom babble, 5 dB | 4.6% → 4.1% | 59.2% → 46.5% | 0% → 2.2% |
| Fan / rain hiss, 10 dB | 5.1% → 4.6% | 57.3% → 54.8% | 0% → 0.8% |
| Simulated regional accent (216 words read the regional way) | **86.1% → 28.7%** (186 → 62) | n/a | |

* Accent false alarms fall by 57 points; false alarms on other correct words fall by about 0.5 points in every condition.
* Recall falls by 2.5-17 points (17.2 on clean audio): guarded words become "unsure" (shown to the teacher, never counted), and many simulated
  errors are aspiration swaps that the accent guard cannot tell apart from a regional accent.
* The headline results above predate the guards. With guards, on these 60 recordings: recall 70.7%, false alarms 3.2%.
* Not children, not real dialect speech, not real classroom audio.
