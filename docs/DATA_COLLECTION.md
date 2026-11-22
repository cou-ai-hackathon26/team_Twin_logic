# Data collection and annotation

The benchmark is only as honest as its ground truth. This is the procedure
from Proposal section 5.

## 1. Recordings

| Group | Speakers | Passages | Files | Purpose |
|---|---|---|---|---|
| Adult, correct reading | 6 | 12 | 72 | false alarms, CER/WER |
| Adult, planned errors (~5 per reading) | same 6 | 12 | 72 | error detection (~360 known errors) |
| Children 6-10 (parent consent) | 8 | 3 each | 24 | target-user validation |
| Noisy (classroom-like) | any | any | 20 | robustness and abstention |

* **Speaker split, fixed before running anything:** 2 adult speakers are
  `tune` (used only by `scripts/calibrate.py`), the other 4 and all children
  are `test`. Recordings we collect are never used for training.
* Planned errors must cover every unit type: কার, যুক্তাক্ষর, রেফ, র-ফলা,
  য-ফলা, ব-ফলা, চন্দ্রবিন্দু and whole-word skips. Write the planned errors
  down before recording, but annotate what was *actually* said.
* Children: written parent consent, no names or faces, roll code only,
  used for testing only. Record with the app (it stores a 16 kHz WAV) or any
  recorder; WAV, MP3 and M4A all work.

## 2. recordings.csv

```
id,audio,passage,speaker,group,split,condition,human_wcpm,human_transcript
s1_P04_ok,audio/s1_P04_ok.wav,P04,s1,adult,tune,clean,,
s3_P04_err,audio/s3_P04_err.wav,P04,s3,adult,test,clean,61.5,আজ আমার স্কুলের পথম দিন ...
c2_P01,audio/c2_P01.wav,P01,c2,child,test,clean,38.0,
```

`passage` is the code from `backend/app/seed/passages.json`. `human_wcpm` is
the words-correct-per-minute counted by a human with a stopwatch (optional,
needed for WCPM error and rank agreement). `human_transcript` is optional and
enables CER/WER.

## 3. annotations.csv

Generate the empty sheet, then fill it in a spreadsheet:

```
python -m scripts.annotation_template eval/recordings.csv eval/annotations.csv
```

| column | meaning |
|---|---|
| label_a, label_b | each annotator alone: `c` correct, `m` misread, `s` skipped, `n` not reached |
| label | final label after both listen again together |
| error_units | for `m` words: which units were wrong, using the indices in the `units` column (e.g. `0` for প্র in প্রথম) |
| heard | optional: what was said |

Rules: a self-correction within 3 seconds is `c`; a hesitation alone is `c`;
a repeated word is `c`; a spelling-only difference that sounds the same
(স/শ/ষ, ি/ী, ন/ণ, জ/য) is `c`; a regional pronunciation the school accepts
is `c` (add it in Settings -> Accepted variants).

## 4. Run

```
cd backend
python -m scripts.calibrate --recordings eval/recordings.csv --annotations eval/annotations.csv
python -m scripts.benchmark --recordings eval/recordings.csv --annotations eval/annotations.csv
```

The report lands in `data/reports/` and in the app's Benchmark page.
Report every percentage with its counts and 95% interval, adults and
children separately, whichever system wins. Inter-annotator agreement
(Cohen's kappa) is computed from label_a/label_b automatically.
