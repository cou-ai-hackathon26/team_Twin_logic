from app.assessment import types as T
from app.assessment.marking import assess, passage_words
from app.assessment.metrics import compute_metrics
from app.assessment.weak_patterns import compute_patterns
from app.bangla.normalize import normalize_word
from app.bangla.segment import segment_normalized

TH = T.Thresholds()


def rec(words, conf=0.95, step=0.6):
    out = []
    t = 0.5
    for w in words:
        n = normalize_word(w)
        units = segment_normalized(n)
        out.append(T.RecognizedWord(n, units, [conf] * len(units), t, t + 0.5))
        t += step
    return out


def evidence(pw, gop=2.0, overrides=None, step=0.6):
    overrides = overrides or {}
    ev = []
    t = 0.5
    for w in pw:
        g = overrides.get(w.index, gop)
        ev.append(T.ExpectedEvidence(t, t + 0.5, [g] * len(w.units)))
        t += step
    return ev


def statuses(marks):
    return [m.status for m in marks]


def test_all_correct():
    pw = passage_words("আমার প্রথম দিন স্কুলে।")
    marks = assess(pw, rec(["আমার", "প্রথম", "দিন", "স্কুলে"]), evidence(pw), TH)
    assert statuses(marks) == ["correct"] * 4


def test_misread_ra_phala():
    pw = passage_words("আমার প্রথম দিন")
    marks = assess(pw, rec(["আমার", "পথম", "দিন"]), evidence(pw, overrides={1: -2.0}), TH)
    assert statuses(marks) == ["correct", "misread", "correct"]
    assert "phala:র" in marks[1].patterns


def test_disagreement_is_unsure():
    pw = passage_words("আমার প্রথম দিন")
    # decoder says error, expected-text score is middling -> unsure
    marks = assess(pw, rec(["আমার", "পথম", "দিন"]), evidence(pw, overrides={1: 0.2}), TH)
    assert marks[1].status == "unsure"
    assert marks[1].raw_status == "misread"


def test_high_gop_overrides_decoder():
    pw = passage_words("আমার প্রথম দিন")
    marks = assess(pw, rec(["আমার", "পথম", "দিন"]), evidence(pw, overrides={1: 3.0}), TH)
    assert marks[1].status == "correct"


def test_skip_and_repetition():
    pw = passage_words("আমি ভাত খাই আজ")
    marks = assess(pw, rec(["আমি", "আমি", "খাই", "আজ"]), evidence(pw, overrides={1: -3.0}), TH)
    assert statuses(marks) == ["correct", "skipped", "correct", "correct"]
    assert "repeated" in marks[0].flags


def test_homophone_spelling_is_correct():
    pw = passage_words("সকাল")
    marks = assess(pw, rec(["শকাল"]), evidence(pw), TH)
    assert marks[0].status == "correct"
    assert "spelling_only" in marks[0].flags


def test_merge_two_words():
    pw = passage_words("আমার বাড়ি")
    marks = assess(pw, rec(["আমারবাড়ি"]), evidence(pw), TH)
    assert statuses(marks) == ["correct", "correct"]


def test_not_reached_and_metrics():
    pw = passage_words("এক দুই তিন চার পাঁচ ছয়")
    marks = assess(pw, rec(["এক", "দুই", "তিন"]), evidence(pw, overrides={3: -3, 4: -3, 5: -3}), TH)
    assert statuses(marks)[3:] == ["not_reached"] * 3
    m = compute_metrics([x.to_dict() for x in marks])
    assert m.attempted_words == 3 and m.correct == 3 and m.accuracy == 1.0


def test_hesitation_flag():
    pw = passage_words("আমি ভাত খাই")
    ev = evidence(pw)
    ev[2].start = ev[1].end + 3.5
    marks = assess(pw, rec(["আমি", "ভাত", "খাই"]), ev, TH)
    assert "hesitation" in marks[2].flags


def test_weak_patterns_need_repetition():
    def mk(heard):
        pw = passage_words("প্রথম প্রাণ")
        marks = assess(pw, rec(heard), evidence(pw, gop=-2.0), TH)
        return [m.to_dict() for m in marks]

    r1 = mk(["পথম", "পাণ"])
    r2 = mk(["পথম", "প্রাণ"])
    pats = compute_patterns([(1, "2026-01-01", r1), (2, "2026-01-02", r2)])
    ra = next(p for p in pats if p["key"] == "phala:র")
    assert ra["errors"] == 3 and ra["candidate"]
    single = compute_patterns([(1, "2026-01-01", r1)])
    assert not next(p for p in single if p["key"] == "phala:র")["candidate"]
