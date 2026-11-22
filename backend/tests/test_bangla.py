from app.bangla.normalize import normalize_text, normalize_word, tokenize_display
from app.bangla.phonetics import diff_units
from app.bangla.segment import segment_word


def texts(word):
    return [u.text for u in segment_word(word)]


def test_normalise_nukta_and_o_kar():
    assert normalize_word("ড়") == "ড়"  # ড় composed
    assert normalize_word("কো") == "কো"  # ে + া -> ো
    assert normalize_word("অা") == "আ"
    assert normalize_word("ত্‍") == "ৎ"
    assert normalize_text("আমি, ভাত খাই।") == "আমি ভাত খাই"


def test_tokenize_keeps_display():
    toks = tokenize_display("আমি ভাত খাই ।")
    assert [n for _, n in toks] == ["আমি", "ভাত", "খাই"]
    assert toks[-1][0].endswith("।")


def test_segment_basic():
    assert texts("প্রথম") == ["প্র", "থ", "ম"]
    assert texts("কার্য") == ["কা", "র্য"]
    assert texts("ক্ষেত্র") == ["ক্ষে", "ত্র"]
    assert texts("চাঁদ") == ["চাঁ", "দ"]
    assert texts("উৎসব") == ["উ", "ৎ", "স", "ব"]


def test_segment_parts():
    pr = segment_word("প্র")[0]
    assert pr.core == ("প",) and pr.phalas == ("র",)
    assert "phala:র" in pr.patterns()
    ksh = segment_word("ক্ষ")[0]
    assert ksh.is_conjunct and ksh.core_text == "ক্ষ"
    ry = segment_word("র্য")[0]
    assert ry.reph and ry.core == ("য",)
    mb = segment_word("ম্ব")[0]
    assert mb.is_conjunct and mb.phalas == ()


def test_diff_ra_phala_dropped():
    e = segment_word("প্র")[0]
    g = segment_word("প")[0]
    errs = diff_units(e, g)
    assert [x.pattern for x in errs] == ["phala:র"]


def test_diff_homophone_ignored():
    e = segment_word("সী")[0]
    g = segment_word("শি")[0]
    assert diff_units(e, g) == []


def test_diff_kar_substituted():
    e = segment_word("কে")[0]
    g = segment_word("কা")[0]
    errs = diff_units(e, g)
    assert errs[0].pattern == "kar:ে"


def test_diff_conjunct_simplified():
    e = segment_word("ক্ষ")[0]
    g = segment_word("ক")[0]
    errs = diff_units(e, g)
    assert errs[0].pattern == "conj:ক্ষ"
