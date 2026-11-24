"""Trust guards: regional accent, background noise, odd words; accept-accent and tricky-word API."""

import numpy as np

from app.assessment import types as T
from app.assessment.marking import assess, passage_words
from app.assessment.robust import (GuardOptions, accent_only, apply_guards, odd_word_reason, word_snr)
from app.bangla.normalize import normalize_word as n
from app.speech.audio import SR, frame_db
from tests.test_api import FakeRecognizer, wait_done, wav_bytes  # noqa: F401  (sets up the temp data dir)
from tests.test_api import client  # noqa: F401  (fixture)
from tests.test_marking import evidence, rec
from app.services import readings as svc

TH = T.Thresholds()
OFF = GuardOptions(accent=False, noise=False, odd_words=False)


def test_accent_only_pairs():
    assert accent_only(n("ভাত"), n("বাত"))  # aspiration dropped
    assert accent_only(n("বাড়ি"), n("বারি"))  # র / ড় merged
    assert accent_only(n("চাল"), n("সাল"))  # চ said as স
    assert not accent_only(n("মা"), n("বা"))  # a real misread
    assert not accent_only(n("কলম"), n("কলক"))
    assert not accent_only(n("ভাত"), n("বাত ভাত"))  # two words heard


def _misread(passage: str, heard: list[str], bad: int):
    pw = passage_words(passage)
    marks = assess(pw, rec(heard), evidence(pw, overrides={bad: -4.0}), TH)
    return pw, marks


def test_accent_guard_sends_possible_variant_to_teacher():
    pw, marks = _misread("আমি ভাত খাই", ["আমি", "বাত", "খাই"], 1)
    assert marks[1].status == T.MISREAD
    counts = apply_guards(marks, None, pw)
    assert marks[1].status == T.UNSURE and T.FLAG_ACCENT in marks[1].flags and counts["accent"] == 1
    assert "teacher" in marks[1].note_en.lower()
    # a real misread is untouched
    pw, marks = _misread("আমি ভাত খাই", ["আমি", "মাত", "খাই"], 1)
    apply_guards(marks, None, pw)
    assert marks[1].status == T.MISREAD


def test_guards_can_be_switched_off():
    pw, marks = _misread("আমি ভাত খাই", ["আমি", "বাত", "খাই"], 1)
    apply_guards(marks, None, pw, OFF)
    assert marks[1].status == T.MISREAD


def test_noise_guard_makes_misread_unsure():
    pw, marks = _misread("আমি মা খাই", ["আমি", "বা", "খাই"], 1)
    # quiet speech everywhere, loud noise burst over the second word (0.5 s per word from 0.5 s)
    rng = np.random.default_rng(1)
    x = rng.normal(0, 0.002, int(SR * 3)).astype(np.float32)
    t = np.arange(len(x)) / SR
    x += (0.2 * np.sin(2 * np.pi * 200 * t) * ((t > 0.5) & (t < 1.0))).astype(np.float32)  # word 1: clean speech
    noisy = (t > 1.0) & (t < 1.8)
    x[noisy] = rng.normal(0, 0.2, noisy.sum()).astype(np.float32)  # word 2 drowned in noise
    counts = apply_guards(marks, x, pw)
    assert marks[0].snr_db is not None and marks[0].snr_db > 20
    assert marks[1].status == T.UNSURE and T.FLAG_NOISY in marks[1].flags and counts["noisy"] == 1


def test_word_snr_without_timing():
    fr = frame_db(np.zeros(SR, dtype=np.float32))
    assert word_snr(None, None, None, fr, -60.0) is None


def test_odd_word_guard():
    pw = passage_words("স্ত্রী এল")
    assert odd_word_reason(pw[0].display, pw[0].units) == "three-letter conjunct"
    assert odd_word_reason(pw[1].display, pw[1].units) is None
    marks = assess(pw, rec(["সতী", "এল"], conf=0.75), evidence(pw, overrides={0: -4.0}), TH)
    assert marks[0].status == T.MISREAD
    apply_guards(marks, None, pw, GuardOptions(accent=False, noise=False))
    assert marks[0].status == T.UNSURE and T.FLAG_ODD in marks[0].flags
    # very confident recogniser keeps the misread
    marks = assess(pw, rec(["সতী", "এল"], conf=0.97), evidence(pw, overrides={0: -4.0}), TH)
    apply_guards(marks, None, pw, GuardOptions(accent=False, noise=False))
    assert marks[0].status == T.MISREAD
    # a word the teacher marked as tricky is always left to the teacher
    pw = passage_words("মা এল")
    marks = assess(pw, rec(["বা", "এল"], conf=0.97), evidence(pw, overrides={0: -4.0}), TH)
    apply_guards(marks, None, pw, GuardOptions(accent=False, noise=False, tricky_words={n("মা")}))
    assert marks[0].status == T.UNSURE


def test_accept_accent_and_tricky_words_api(client, monkeypatch):  # noqa: F811
    c = client
    cls = next(x for x in c.get("/api/classrooms").json() if x["name"] == "Class 2")
    sid = c.get(f"/api/classrooms/{cls['id']}").json()["students"][0]["id"]
    pid = c.post("/api/passages", json={"title": "accent test", "grade": 2, "text": "আমি ভাত মা খাই"}).json()["id"]
    monkeypatch.setattr(svc, "get_ctc", lambda: FakeRecognizer(["আমি", "বাত", "বা", "খাই"]))
    monkeypatch.setattr(svc, "guard_options", lambda db: GuardOptions(accent=False, noise=False, odd_words=False))
    rid = c.post("/api/readings", data={"student_id": sid, "passage_id": pid},
                 files={"audio": ("a.wav", wav_bytes(), "audio/wav")}).json()["id"]
    r = wait_done(c, rid)
    by = {m["display"]: m for m in r["marks"]}
    assert by["ভাত"]["final_status"] == "misread" and r["review_stats"]["to_check"] >= 2
    r = c.post(f"/api/readings/{rid}/marks/{by['ভাত']['index']}/accept-accent").json()
    m = next(x for x in r["marks"] if x["display"] == "ভাত")
    assert m["final_status"] == "correct" and r["review_stats"]["changed"] == 1
    assert any(v["word"] == n("ভাত") and v["variant"] == n("বাত") for v in c.get("/api/variants").json())
    # a two-word or identical heard form cannot be accepted
    assert c.post(f"/api/readings/{rid}/marks/{by['আমি']['index']}/accept-accent").status_code == 422
    # tricky words
    t = c.post("/api/tricky-words", json={"word": "মা"}).json()
    assert any(x["word"] == n("মা") for x in c.get("/api/tricky-words").json())
    assert c.delete(f"/api/tricky-words/{t['id']}").status_code == 204


def test_silent_skip_is_not_called_noise():
    pw = passage_words("আমি মা খাই")
    marks = assess(pw, rec(["আমি", "মা", "খাই"]), evidence(pw), TH)
    marks[1].status, marks[1].heard, marks[1].start, marks[1].end = T.SKIPPED, "", 1.1, 1.6
    rng = np.random.default_rng(2)
    x = rng.normal(0, 0.003, int(SR * 3)).astype(np.float32)  # mic hiss only where the word was skipped
    t = np.arange(len(x)) / SR
    x += (0.2 * np.sin(2 * np.pi * 200 * t) * (((t > 0.5) & (t < 1.0)) | ((t > 1.7) & (t < 2.2)))).astype(np.float32)
    apply_guards(marks, x, pw)
    assert marks[1].status == T.SKIPPED


def test_soft_word_in_quiet_room_is_not_noise():
    pw, marks = _misread("আমি মা খাই", ["আমি", "বা", "খাই"], 1)
    rng = np.random.default_rng(3)
    x = rng.normal(0, 0.0005, int(SR * 3)).astype(np.float32)  # quiet room
    t = np.arange(len(x)) / SR
    x += (0.3 * np.sin(2 * np.pi * 200 * t) * (((t > 0.5) & (t < 1.0)) | ((t > 1.7) & (t < 2.2)))).astype(np.float32)
    x += (0.002 * np.sin(2 * np.pi * 180 * t) * ((t > 1.1) & (t < 1.6))).astype(np.float32)  # the misread word, said softly
    apply_guards(marks, x, pw)
    assert marks[1].status == T.MISREAD and T.FLAG_NOISY not in marks[1].flags
