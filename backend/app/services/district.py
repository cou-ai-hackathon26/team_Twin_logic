"""District summary: which written units children struggle with, school by school. Counts only.

Privacy rules (also in docs/DATA_PROTECTION.md):
* only readings a teacher has reviewed are counted (the teacher has the final word);
* no child, class roll, nickname, recording or single reading ever leaves this module;
* a school with fewer than MIN_GROUP assessed children shows no results ("too few to show");
* a unit cell is shown only when at least MIN_GROUP children had a chance to read that unit;
* a trend week is shown only when at least MIN_GROUP children read in that week.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..bangla.patterns import CATEGORY_LABELS, pattern_category, pattern_label
from ..models import SIMULATED_MODEL_ID, Classroom, Passage, School
from .analytics import passage_pattern_counts, student_patterns

MIN_GROUP = 5
MIN_OPPORTUNITIES = 20  # a unit must have been read at least this often before its error rate is ranked
CATEGORIES = ["conj", "kar", "phala", "reph", "letter", "vowel", "sign", "hasanta"]
TREND_WEEKS = 8


def _reviewed_bn(st):
    return [r for r in st.readings
            if r.reviewed and r.status == "done" and not (r.passage is not None and r.passage.language == "en")]


class _Agg:
    """Errors / opportunities per unit key and per category, plus how many children each covers."""

    def __init__(self) -> None:
        self.units: dict[str, dict] = defaultdict(lambda: {"errors": 0, "opportunities": 0, "children": 0,
                                                           "children_with_errors": 0})
        self.cats: dict[str, dict] = defaultdict(lambda: {"errors": 0, "opportunities": 0, "children": 0,
                                                          "children_with_errors": 0})

    def add_child(self, pats: list[dict]) -> None:
        cat_seen: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for p in pats:
            if p["key"] == "skip" or not p["opportunities"]:
                continue
            u = self.units[p["key"]]
            u["errors"] += p["errors"]
            u["opportunities"] += p["opportunities"]
            u["children"] += 1
            u["children_with_errors"] += 1 if p["errors"] else 0
            c = cat_seen[pattern_category(p["key"])]
            c[0] += p["errors"]
            c[1] += p["opportunities"]
        for cat, (e, o) in cat_seen.items():
            a = self.cats[cat]
            a["errors"] += e
            a["opportunities"] += o
            a["children"] += 1
            a["children_with_errors"] += 1 if e else 0

    def merge(self, other: "_Agg") -> None:
        for src, dst in ((other.units, self.units), (other.cats, self.cats)):
            for k, v in src.items():
                for f, x in v.items():
                    dst[k][f] += x


def _cell(a: dict | None) -> dict:
    if not a or a["children"] < MIN_GROUP:
        return {"hidden": True, "children": a["children"] if a else 0}
    return {"hidden": False, "children": a["children"], "children_with_errors": a["children_with_errors"],
            "errors": a["errors"], "opportunities": a["opportunities"],
            "error_rate": round(a["errors"] / a["opportunities"], 3) if a["opportunities"] else None}


def _practice_passages(passages: list[tuple[Passage, dict[str, int]]], key: str, n: int = 3) -> list[dict]:
    ranked = sorted(((counts.get(key, 0), p) for p, counts in passages if counts.get(key, 0)),
                    key=lambda t: (-t[0], 0 if (t[1].code or "").startswith("T") else 1, t[1].grade))
    return [{"id": p.id, "code": p.code, "title": p.title, "grade": p.grade, "occurrences": c} for c, p in ranked[:n]]


def _weakest(agg: _Agg, passages, n: int = 5) -> list[dict]:
    rows = []
    for key, a in agg.units.items():
        if a["children"] < MIN_GROUP or a["opportunities"] < MIN_OPPORTUNITIES or not a["errors"]:
            continue
        rows.append({**pattern_label(key), **_cell(a)})
    rows.sort(key=lambda r: (-(r["error_rate"] or 0), -r["children_with_errors"]))
    for r in rows[:n]:
        r["practice"] = _practice_passages(passages, r["key"])
    return rows[:n]


def _week_start(dt: datetime) -> datetime:
    dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    d = dt.date() - timedelta(days=dt.weekday())
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def summary(db: Session, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    passages = [(p, passage_pattern_counts(p.text)) for p in
                db.scalars(select(Passage).where(Passage.active.is_(True), Passage.language == "bn"))]
    schools = db.scalars(select(School).order_by(School.district, School.upazila, School.name)).all()
    total = _Agg()
    total_wcpm: list[float] = []
    total_children = total_assessed = total_readings = simulated = 0
    weeks: dict[datetime, dict] = defaultdict(lambda: {"children": set(), "wcpm": []})
    out_schools = []
    for s in schools:
        classes = db.scalars(select(Classroom).where(Classroom.school_id == s.id)).all()
        agg = _Agg()
        wcpm: list[float] = []
        children = assessed = n_read = 0
        for c in classes:
            for st in c.students:
                if not st.active:
                    continue
                children += 1
                rs = _reviewed_bn(st)
                if not rs:
                    continue
                assessed += 1
                n_read += len(rs)
                simulated += sum(1 for r in rs if r.model_id == SIMULATED_MODEL_ID)
                agg.add_child(student_patterns(st, reviewed_only=True))
                for r in rs:
                    w = (r.metrics or {}).get("wcpm")
                    if w is not None:
                        wcpm.append(w)
                        wk = weeks[_week_start(r.created_at)]
                        wk["children"].add(st.id)
                        wk["wcpm"].append(w)
        total.merge(agg)
        total_wcpm += wcpm
        total_children += children
        total_assessed += assessed
        total_readings += n_read
        row = {"id": s.id, "name": s.name, "upazila": s.upazila, "district": s.district, "classes": len(classes),
               "children": children, "assessed": assessed, "hidden": assessed < MIN_GROUP}
        if not row["hidden"]:
            row.update({"reviewed_readings": n_read,
                        "median_wcpm": round(statistics.median(wcpm), 1) if wcpm else None,
                        "categories": {cat: _cell(agg.cats.get(cat)) for cat in CATEGORIES},
                        "weakest": _weakest(agg, passages)})
        out_schools.append(row)

    start = _week_start(now) - timedelta(weeks=TREND_WEEKS - 1)
    trend = []
    for i in range(TREND_WEEKS):
        wk = start + timedelta(weeks=i)
        w = weeks.get(wk)
        n = len(w["children"]) if w else 0
        trend.append({"week": wk.date().isoformat(), "children": n, "hidden": n < MIN_GROUP,
                      "median_wcpm": round(statistics.median(w["wcpm"]), 1) if w and n >= MIN_GROUP else None})

    unassigned = db.scalars(select(Classroom).where(Classroom.school_id.is_(None))).all()
    return {
        "generated": now.isoformat(timespec="seconds"),
        "min_group": MIN_GROUP,
        "categories": [{"key": k, "bn": CATEGORY_LABELS[k][0], "en": CATEGORY_LABELS[k][1]} for k in CATEGORIES],
        "totals": {"schools": len(schools), "children": total_children, "assessed": total_assessed,
                   "reviewed_readings": total_readings, "simulated_readings": simulated,
                   "median_wcpm": (round(statistics.median(total_wcpm), 1)
                                   if total_wcpm and total_assessed >= MIN_GROUP else None),
                   "categories": {cat: _cell(total.cats.get(cat)) for cat in CATEGORIES},
                   "weakest": _weakest(total, passages) if total_assessed >= MIN_GROUP else []},
        "schools": out_schools,
        "trend": trend,
        "unassigned_classes": len(unassigned),
    }


def summary_csv(data: dict) -> str:
    """One row per school and unit category (counts only), for a spreadsheet."""
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["district", "upazila", "school", "classes", "children", "assessed", "median_wcpm", "unit",
                "children_read_unit", "children_with_errors", "errors", "opportunities", "error_rate"])
    for s in data["schools"]:
        base = [s["district"] or "", s["upazila"] or "", s["name"], s["classes"], s["children"], s["assessed"]]
        if s["hidden"]:
            w.writerow(base + ["", "(too few children to show)", "", "", "", "", ""])
            continue
        for cat in data["categories"]:
            c = s["categories"][cat["key"]]
            if c["hidden"]:
                w.writerow(base + [s["median_wcpm"], cat["en"], c["children"], "(hidden: fewer than "
                                   f"{data['min_group']})", "", "", ""])
            else:
                w.writerow(base + [s["median_wcpm"], cat["en"], c["children"], c["children_with_errors"],
                                   c["errors"], c["opportunities"], c["error_rate"]])
    return buf.getvalue()
