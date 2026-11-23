# Technical defence: what every team member must be able to explain

Rehearse out loud. Each answer should fit in about 30 seconds, without slides. Point to the code if asked.

## 1. The pipeline in one breath

Audio (16 kHz) → quality check → wav2vec2 CTC model (Bangla, ONNX int8, CPU) gives a probability for
every character every 20 ms → two readings of those probabilities: **greedy decoding** (what was said)
and **forced alignment** (how well the passage text fits) → our grapheme engine splits both into
Bangla written units → weighted alignment → per-word decision (correct / misread / skipped / unsure)
→ metrics and weak patterns. Code: `backend/app/pipeline.py:run_porabondhu`.

## 2. Questions judges are likely to ask

**What is CTC greedy decoding, and why no language model?**
The model outputs, for each 20 ms frame, a probability over characters plus a "blank". Greedy decoding
takes the most likely symbol per frame, merges repeats and drops blanks. We deliberately use no language
model: an LM "corrects" a child's প্রথম→পথম back into a real word, which hides exactly the error a
teacher needs to see. (`app/speech/ctc.py`, `greedy_decode`)

**What is forced alignment / the expected-text score?**
We ask the same probabilities a different question: if the child read the passage exactly, where would
each passage character be and how likely is it there? For each unit we take its log-probability at its
best frame minus the best competing character (capped by an absence floor). High = the passage fits the
audio; low = it does not. It also gives word timings and catches skipped words. (`expected_evidence`)

**What are the two confidence signals and what is abstention?**
1) Free-decoding confidence: how sure the decoder was about what it heard.
2) Expected-text score: how well the passage text fits.
A word is **misread** only if the decoder confidently heard something else *and* the passage fits
poorly. If the passage fits well it is **correct** even if the decoder disagreed. Otherwise it is
**unsure**: shown to the teacher, never counted as an error. That is abstention: the system prefers
"I don't know" to a false accusation. (`app/assessment/marking.py`, thresholds `free_high`, `gop_high`,
`gop_low`, tuned on tuning speakers only by `scripts/calibrate.py`)

**What does the grapheme segmenter do?**
It turns a Bangla word into written units the way a teacher sees them: consonant clusters
(যুক্তাক্ষর), ফলা, রেফ, কার and signs (ং ঃ ঁ). প্রথম → প্র + থ + ম. Comparing heard and expected
unit by unit tells us *which* unit was misread: "র-ফলা dropped in প্র", not just "word wrong".
Spelling-only pairs that sound the same (স/শ/ষ, ি/ী, ু/ূ, ন/ণ, জ/য, ত/ৎ) are not counted as
errors. (`app/bangla/segment.py`, `phonetics.py`)

**How does one wrong word become a recommendation?**
Each confirmed misread records its unit pattern (e.g. `phala:র`). Across readings, a pattern becomes a
**candidate weak pattern** when there are at least 3 errors in at least 2 readings (`PB_WEAK_MIN_ERRORS`,
`PB_WEAK_MIN_READINGS`). The student page then suggests practice words and passages that contain that
unit, and the class map shows how many children share it. Teacher corrections change the counts.

**Where can it falsely accuse a child?**
Regional pronunciation that differs from standard spelling, a noisy room, a quiet or very young voice,
and words the model is weak on. Mitigations: the quality check rejects bad audio, the two-signal rule
and "unsure", accepted regional variants, and above all **the teacher has the final word**: one tap
changes any mark, and marks shown to the child are only encouragement.

**How good is it really?**
On 100 held-out FLEURS test recordings (real adults, simulated errors): recall 82%, precision 76%,
false alarms 4.2%, 18% unsure. The same speech model with plain word comparison: precision 27%, false
alarms 43%. So our layer cuts false alarms by about 39 points and costs about 18 points of recall.
Misses: precision target (80%) and speed target (15 s per 60 s). It is **not child validation**. On a
child-like proxy (same recordings resampled so pitch and formants rise 10-20%) recall drops only about
3 points. Our first proxy looked catastrophic (13%) until a control showed that the pitch-shifting tool
itself caused it; we report both and say which one is valid.

**Why not just use Whisper or ChatGPT?**
We compared Whisper small on the same audio: on this Bengali data it produced mostly unusable text
(about 80% character errors), so it is not a fair strong baseline, and we say so. In general, Whisper's
language model tends to write the word that *should* be there. It also does not say which written unit was wrong, and a cloud
LLM would send children's voices off the device. Our system runs offline on a school laptop.

**Did you train a model?**
The speech model is a public checkpoint (arijitx/wav2vec2-xls-r-300m-bengali, Apache-2.0) that we
exported to ONNX int8 for CPU speed. What we built and tuned: the grapheme engine, the alignment, the
two-signal decision and its thresholds (calibrated on held-out tuning speakers). A child-voice
fine-tuning script exists (`scripts/adapt_child_voice.py`) but we only claim it if it measurably helps.

**What is simulated in the demo?**
Dashboard history labelled **DEMO · simulated** was generated from scripted errors run through the real
marking engine, with no audio. Every reading recorded during the demo is marked live by the models.

## 2b. The five hardest judge questions (model answers; rehearse them in your own words)

1. **Why is blank left out of the competitor in the expected-text score?** In CTC most frames are
   "blank", so comparing against blank would mostly measure timing, not which letter was said. We take
   the frame where the expected character is most likely and compare it with the best *other
   character*; a temperature (2.0, tuned) softens the very peaky CTC posteriors so the score is not
   saturated at 0 or minus infinity.
2. **Your thresholds were at the edge of the grid; why trust them?** We re-ran a wider search with
   3-fold cross-validation on the dev recordings: precision 81% ± 2, recall 82% ± 6, false alarms 3.3%
   ± 0.4, and on held-out test recordings 76% / 82% / 4.2%. One threshold is still at the edge. On a
   resampled child-like proxy they still give 79% recall and 4.4% false alarms; real children are untested.
3. **Aren't you just finding your own perturbations?** We tested error types the detector was not
   built around (random consonant swaps, whole-word substitutions): recall 90%, precision 74%, false
   alarms 4.2%, about the same as the main set.
4. **Inserted words are not real skips.** We also cut real word audio out of recordings: recall 77%,
   precision 64%. Real skips are harder; we report that.
5. **18% unsure means one word in five goes to the teacher. Usable?** The teacher only listens to the
   amber words, never all of them, and "unsure" is never counted against the child. The trade-off is
   tunable (see `calibration_wide.json`); fewer unsure words cost precision. Whether teachers accept
   this has not been tested with teachers yet.

## 3. Live demo script (3 minutes)

1. Log in as teacher. Point out the DEMO banner and badges on the dashboard: "this history is simulated".
2. New assessment → choose a child and T06 (Grade 2, ফলা lesson, textbook page shown in the evidence
   table) → read it aloud, making two deliberate mistakes (e.g. স্মরণ → সরণ, দ্বিতীয় → দিতীয়).
3. Show the progress bar (real pipeline stages) while it marks.
4. Review: click the misread word, show heard vs expected unit by unit, play just that word. Correct one
   mark with a tap ("the teacher has the final word"). Finalise; audio is deleted.
5. Student page → weak patterns and practice words → Report button.
6. Benchmark page: the honest numbers and what they do not prove.

Backup if the network fails: the local copy (`start.ps1`) and the demo video.
