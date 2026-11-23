"""The trained word classifier re-decides only words the decoder flagged; no model -> rules unchanged."""

from app.assessment import learned
from app.assessment import types as T


def _mark(i, status, raw, err_free=0.9, gop=-6.0):
    units = [T.UnitResult("ক", "খ", "sub", 0, err_free, gop,
                          [{"pattern": "letter:ক", "kind": "sub", "expected": "ক", "heard": "খ"}])]
    return T.WordMarkResult(index=i, display="ক", expected="ক", heard="খ", status=status, raw_status=raw,
                            free_conf=err_free, gop=gop, units=units, err_free=err_free)


def _model(bias, lo=0.3, hi=0.7):
    n = len(learned.FEATURES)
    return {"mean": [0.0] * n, "std": [1.0] * n, "weights": [0.0] * n, "bias": bias, "lo": lo, "hi": hi}


def test_features_have_fixed_length():
    assert len(learned.features(_mark(0, T.MISREAD, T.MISREAD).to_dict())) == len(learned.FEATURES)


def test_confident_error_restores_patterns():
    m = _mark(0, T.UNSURE, T.MISREAD)
    learned.apply([m], _model(bias=5.0))
    assert m.status == T.MISREAD and m.patterns == ["letter:ক"]


def test_low_probability_becomes_correct_and_middle_unsure():
    a, b = _mark(0, T.MISREAD, T.MISREAD), _mark(1, T.MISREAD, T.MISREAD)
    learned.apply([a], _model(bias=-5.0))
    learned.apply([b], _model(bias=0.0))
    assert a.status == T.CORRECT and not a.patterns
    assert b.status == T.UNSURE


def test_untouched_words():
    correct = _mark(0, T.CORRECT, T.CORRECT)
    nr = _mark(1, T.NOT_REACHED, T.SKIPPED)
    learned.apply([correct, nr], _model(bias=5.0))
    assert correct.status == T.CORRECT and nr.status == T.NOT_REACHED
