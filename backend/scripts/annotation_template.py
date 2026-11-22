"""Create an empty annotations.csv for the recordings listed in recordings.csv.

    python -m scripts.annotation_template eval/recordings.csv eval/annotations.csv

One row per passage word per recording, with the word and its units, ready
for two annotators to fill label_a / label_b independently (c, m, s, n).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.assessment.marking import passage_words  # noqa: E402
from app.evaluation.dataset import load_seed_passages  # noqa: E402


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    rec_csv, out_csv = Path(sys.argv[1]), Path(sys.argv[2])
    if out_csv.exists():
        sys.exit(f"{out_csv} already exists; not overwriting annotations")
    passages = load_seed_passages()
    rows = []
    with open(rec_csv, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            for w in passage_words(passages[r["passage"].strip()]):
                rows.append({"recording_id": r["id"].strip(), "word_index": w.index, "word": w.norm,
                             "units": " ".join(f"{k}:{u.text}" for k, u in enumerate(w.units)),
                             "label_a": "", "label_b": "", "label": "", "error_units": "", "heard": ""})
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print(f"wrote {len(rows)} rows to {out_csv}")


if __name__ == "__main__":
    main()
