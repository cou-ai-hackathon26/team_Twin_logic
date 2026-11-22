"""Word marking: combine alignment with the two confidence signals.

Decision rule (Proposal, Step 5), applied to every potential error found by
the alignment:

* Error   - free decoding differs with high confidence AND the expected-text
            score for that unit is low.
* Correct - free decoding matches, OR the expected-text score is high.
* Unsure  - anything else (signals disagree / near threshold / missing).
            Never counted as an error; shown to the teacher.

Hesitation (gap >= 3 s before a word) and repetition are *flags*, not statuses.
"""

from __future__ import annotations

from dataclasses import asdict

from ..alignment.words import AlignedGroup, align_units, align_words, word_distance
from ..bangla.normalize import tokenize_display
from ..bangla.phonetics import diff_units, homophone_key
from ..bangla.segment import Unit, segment_normalized
from . import types as T


def passage_words(text: str) -> list[T.PassageWord]:
    return [
        T.PassageWord(index=i, display=disp, norm=norm, units=segment_normalized(norm))
        for i, (disp, norm) in enumerate(tokenize_display(text))
    ]


def _min(vals: list[float | None]) -> float | None:
    xs = [v for v in vals if v is not None]
    return min(xs) if xs else None


def _detect_conjunct_split(exp_u: Unit, rec_u: Unit, extra: Unit) -> bool:
    """True when a conjunct was read as separate letters, e.g. প্র -> প + র."""
    if len(exp_u.consonants) < 2 or not rec_u.consonants or not extra.consonants:
        return False
    return rec_u.consonants[0] == exp_u.consonants[0] and extra.consonants[0] in exp_u.consonants[1:]


def _assess_group(
    group: AlignedGroup,
    pw: list[T.PassageWord],
    rw: list[T.RecognizedWord],
    ev: list[T.ExpectedEvidence],
    th: T.Thresholds,
    variant_pairs: set[tuple[str, str]],
) -> list[T.WordMarkResult]:
    """Mark the passage words of one aligned group (not insertions)."""
    results: list[T.WordMarkResult] = []
    heard_text = " ".join(rw[j].text for j in group.rec)

    if group.kind == "del":
        i = group.exp[0]
        e = ev[i]
        units = [
            T.UnitResult(u.text, None, "del", k, None, e.unit_gop[k] if k < len(e.unit_gop) else None,
                         [asdict(x) for x in diff_units(u, None)])
            for k, u in enumerate(pw[i].units)
        ]
        g = e.word_gop
        if g is not None and g <= th.gop_low:
            status, bn, en = T.SKIPPED, "শব্দটি পড়া হয়নি", "Word was not read"
        else:
            status = T.UNSURE
            bn, en = "শব্দটি শোনা যায়নি, তবে নিশ্চিত নয়", "Word not heard clearly; check the audio"
        results.append(T.WordMarkResult(
            index=i, display=pw[i].display, expected=pw[i].norm, heard="", status=status,
            raw_status=T.SKIPPED, start=e.start, end=e.end, free_conf=None, gop=g, units=units,
            patterns=["skip"] if status == T.SKIPPED else [], note_bn=bn, note_en=en))
        return results

    # Concatenate units of the group, remembering who owns each unit.
    exp_units: list[Unit] = []
    exp_owner: list[tuple[int, int]] = []  # (word index, unit index in word)
    for i in group.exp:
        for k, u in enumerate(pw[i].units):
            exp_units.append(u)
            exp_owner.append((i, k))
    rec_units: list[Unit] = []
    rec_conf: list[float] = []
    for j in group.rec:
        rec_units.extend(rw[j].units)
        rec_conf.extend(rw[j].unit_conf if len(rw[j].unit_conf) == len(rw[j].units)
                        else [rw[j].confidence] * len(rw[j].units))

    # Accepted variants / exact matches short-circuit to "correct".
    if len(group.exp) == 1 and len(group.rec) == 1:
        i, j = group.exp[0], group.rec[0]
        if pw[i].norm == rw[j].text or (pw[i].norm, rw[j].text) in variant_pairs:
            flags = [] if pw[i].norm == rw[j].text else [T.FLAG_VARIANT]
            e = ev[i]
            units = [T.UnitResult(u.text, u.text, "match", k, rw[j].unit_conf[k] if k < len(rw[j].unit_conf) else None,
                                  e.unit_gop[k] if k < len(e.unit_gop) else None) for k, u in enumerate(pw[i].units)]
            results.append(T.WordMarkResult(
                index=i, display=pw[i].display, expected=pw[i].norm, heard=rw[j].text, status=T.CORRECT,
                raw_status=T.CORRECT, flags=flags, start=e.start if e.start is not None else rw[j].start,
                end=e.end if e.end is not None else rw[j].end, free_conf=rw[j].confidence, gop=e.word_gop,
                units=units))
            return results

    ops, _ = align_units(exp_units, rec_units)

    per_word_units: dict[int, list[T.UnitResult]] = {i: [] for i in group.exp}
    per_word_err_free: dict[int, list[float | None]] = {i: [] for i in group.exp}
    per_word_err_gop: dict[int, list[float | None]] = {i: [] for i in group.exp}
    per_word_spelling: dict[int, bool] = {i: False for i in group.exp}

    last_owner = group.exp[0]
    for idx, op in enumerate(ops):
        if op.i is not None:
            wi, uk = exp_owner[op.i]
            last_owner = wi
            gop_list = ev[wi].unit_gop
            gop = gop_list[uk] if uk < len(gop_list) else None
        else:
            wi, uk, gop = last_owner, None, None
        eu = exp_units[op.i] if op.i is not None else None
        ru = rec_units[op.j] if op.j is not None else None
        conf = rec_conf[op.j] if op.j is not None else None

        if op.kind == "match":
            per_word_units[wi].append(T.UnitResult(eu.text, ru.text, "match", uk, conf, gop))
            continue
        if op.kind == "sub":
            assert eu is not None and ru is not None
            errs = diff_units(eu, ru)
            # conjunct read as two letters: sub followed by an insertion
            nxt = ops[idx + 1] if idx + 1 < len(ops) else None
            if nxt is not None and nxt.kind == "ins" and _detect_conjunct_split(eu, ru, rec_units[nxt.j]):
                key = f"conj:{eu.core_text}" if eu.is_conjunct else (f"phala:{eu.phalas[0]}" if eu.phalas else f"conj:{eu.core_text}")
                errs = [type(errs[0])(key, "split", eu.text, ru.text + rec_units[nxt.j].text,
                                      f"যুক্তাক্ষর {eu.text} ভেঙে আলাদা করে পড়েছে",
                                      f"{eu.text} read as separate letters")] if errs else errs
            if not errs:
                per_word_spelling[wi] = per_word_spelling[wi] or homophone_key(eu.text) == homophone_key(ru.text)
                per_word_units[wi].append(T.UnitResult(eu.text, ru.text, "spelling", uk, conf, gop))
                continue
            per_word_units[wi].append(T.UnitResult(eu.text, ru.text, "sub", uk, conf, gop, [asdict(e) for e in errs]))
            per_word_err_free[wi].append(conf)
            per_word_err_gop[wi].append(gop)
        elif op.kind == "del":
            assert eu is not None
            errs = diff_units(eu, None)
            per_word_units[wi].append(T.UnitResult(eu.text, None, "del", uk, None, gop, [asdict(e) for e in errs]))
            # nothing was emitted for this unit: use the confidence of the word's
            # recognised neighbours as the free-decoding evidence
            per_word_err_free[wi].append(_min(rec_conf) if rec_conf else None)
            per_word_err_gop[wi].append(gop)
        else:  # ins
            assert ru is not None
            # skip insertions already explained as a conjunct split
            prev = ops[idx - 1] if idx > 0 else None
            if prev is not None and prev.kind == "sub" and per_word_units[wi] and per_word_units[wi][-1].errors \
                    and per_word_units[wi][-1].errors[0]["kind"] == "split":
                continue
            per_word_units[wi].append(T.UnitResult(None, ru.text, "ins", None, conf, None, [{
                "pattern": _neighbour_pattern(pw[wi].units, uk), "kind": "added", "expected": None,
                "heard": ru.text, "description_bn": f"অতিরিক্ত {ru.text}",
                "description_en": f"Extra {ru.text} added"}]))
            per_word_err_free[wi].append(conf)
            per_word_err_gop[wi].append(_min(ev[wi].unit_gop))

    for i in group.exp:
        e = ev[i]
        units = per_word_units[i]
        has_err = any(u.errors for u in units)
        start = e.start if e.start is not None else (rw[group.rec[0]].start if group.rec else None)
        end = e.end if e.end is not None else (rw[group.rec[-1]].end if group.rec else None)
        heard = heard_text
        free_word = _min([u.free_conf for u in units])
        flags: list[str] = []
        if not has_err:
            if per_word_spelling[i]:
                flags.append(T.FLAG_SPELLING_ONLY)
            results.append(T.WordMarkResult(
                index=i, display=pw[i].display, expected=pw[i].norm, heard=heard, status=T.CORRECT,
                raw_status=T.CORRECT, flags=flags, start=start, end=end, free_conf=free_word, gop=e.word_gop,
                units=units,
                note_bn="শুধু বানানে পার্থক্য, উচ্চারণ একই" if per_word_spelling[i] else "",
                note_en="Spelling-only difference between letters that sound the same" if per_word_spelling[i] else ""))
            continue

        free_err = _min(per_word_err_free[i])
        gop_err = _min(per_word_err_gop[i])
        if gop_err is not None and gop_err >= th.gop_high:
            status = T.CORRECT
            bn, en = "শব্দ শনাক্তকরণ ভিন্ন, কিন্তু প্রত্যাশিত উচ্চারণের স্কোর বেশি", \
                "Decoder differed but the expected-text score is high"
        elif free_err is not None and gop_err is not None and free_err >= th.free_high and gop_err <= th.gop_low:
            status = T.MISREAD
            bn, en = "ভুল পড়েছে", "Misread"
        else:
            status = T.UNSURE
            bn, en = "নিশ্চিত নয়: শিক্ষক যাচাই করুন", "Unsure: please check"
        patterns: list[str] = []
        if status == T.MISREAD:
            for u in units:
                for er in u.errors:
                    if er["pattern"] not in patterns:
                        patterns.append(er["pattern"])
        results.append(T.WordMarkResult(
            index=i, display=pw[i].display, expected=pw[i].norm, heard=heard, status=status,
            raw_status=T.MISREAD, flags=flags, start=start, end=end, free_conf=free_word, gop=gop_err,
            units=units, patterns=patterns, note_bn=bn, note_en=en))
    return results


def _neighbour_pattern(units: list[Unit], uk: int | None) -> str:
    if not units:
        return "letter:?"
    u = units[min(uk or 0, len(units) - 1)]
    keys = u.patterns()
    return keys[0] if keys else f"letter:{u.text}"


def assess(
    pw: list[T.PassageWord],
    rw: list[T.RecognizedWord],
    ev: list[T.ExpectedEvidence] | None,
    th: T.Thresholds,
    variant_pairs: set[tuple[str, str]] | None = None,
) -> list[T.WordMarkResult]:
    """Mark every passage word. ``ev`` may be None if forced alignment failed."""
    variant_pairs = variant_pairs or set()
    if ev is None or len(ev) != len(pw):
        ev = [T.ExpectedEvidence(unit_gop=[None] * len(w.units)) for w in pw]

    def is_eq(i: int, j: int) -> bool:
        return (pw[i].norm, rw[j].text) in variant_pairs

    groups = align_words([w.units for w in pw], [r.units for r in rw], is_eq)

    marks: dict[int, T.WordMarkResult] = {}
    for g in groups:
        if g.kind == "ins":
            continue
        for m in _assess_group(g, pw, rw, ev, th, variant_pairs):
            marks[m.index] = m
    ordered = [marks[i] for i in range(len(pw))]

    # --- insertions: repetitions, partial attempts, extra words ------------
    last_exp = -1
    for g in groups:
        if g.exp:
            last_exp = g.exp[-1]
            continue
        for j in g.rec:
            r = rw[j]
            prev_i, next_i = last_exp, last_exp + 1
            if prev_i >= 0 and word_distance(pw[prev_i].units, r.units) <= 0.34:
                _flag(ordered[prev_i], T.FLAG_REPEATED, r.text)
            elif next_i < len(pw) and word_distance(pw[next_i].units, r.units) <= 0.34:
                _flag(ordered[next_i], T.FLAG_REPEATED, r.text)
            elif next_i < len(pw) and len(r.units) < len(pw[next_i].units) and \
                    [u.text for u in pw[next_i].units[: len(r.units)]] == [u.text for u in r.units]:
                _flag(ordered[next_i], T.FLAG_PARTIAL, r.text)
            else:
                target = ordered[next_i] if next_i < len(pw) else (ordered[prev_i] if prev_i >= 0 else None)
                if target is not None:
                    _flag(target, T.FLAG_EXTRA, r.text)

    # --- not reached: a long trailing run the decoder never heard -----------
    run = 0
    for m in reversed(ordered):
        if m.raw_status == T.SKIPPED:
            run += 1
        else:
            break
    if run >= th.not_reached_min_run:
        for m in ordered[len(ordered) - run:]:
            m.status = T.NOT_REACHED
            m.patterns = []
            m.note_bn, m.note_en = "এখানে পৌঁছায়নি", "Not reached"

    # --- hesitation ----------------------------------------------------------
    prev_end: float | None = None
    for m in ordered:
        if m.status == T.NOT_REACHED:
            break
        if m.start is not None and prev_end is not None and m.start - prev_end >= th.hesitation_sec:
            if T.FLAG_HESITATION not in m.flags:
                m.flags.append(T.FLAG_HESITATION)
        if m.end is not None:
            prev_end = m.end
    return ordered


def _flag(m: T.WordMarkResult, flag: str, text: str) -> None:
    if flag not in m.flags:
        m.flags.append(flag)
    m.inserted.append(text)
