"""Human-readable labels for pattern keys produced by ``Unit.patterns``."""

from __future__ import annotations

from . import chars as C

CATEGORY_LABELS = {
    "conj": ("যুক্তাক্ষর", "Conjunct"),
    "reph": ("রেফ", "Reph"),
    "phala": ("ফলা", "Phala sign"),
    "kar": ("কার", "Vowel sign"),
    "sign": ("চিহ্ন", "Diacritic"),
    "letter": ("বর্ণ", "Letter"),
    "vowel": ("স্বরবর্ণ", "Vowel letter"),
    "hasanta": ("হসন্ত", "Hasanta"),
    "skip": ("শব্দ বাদ", "Skipped word"),
}

# Kar signs shown on a dotted circle so they are readable alone.
_DOTTED = "◌"


def pattern_category(key: str) -> str:
    return key.split(":", 1)[0]


def pattern_label(key: str) -> dict[str, str]:
    """Return {key, category, bn, en, glyph} for a pattern key."""
    cat = pattern_category(key)
    val = key.split(":", 1)[1] if ":" in key else ""
    bn_cat, en_cat = CATEGORY_LABELS.get(cat, (cat, cat))
    glyph = val
    if cat == "conj":
        bn, en = f"যুক্তাক্ষর {val}", f"Conjunct {val}"
    elif cat == "reph":
        bn, en, glyph = "রেফ (র্)", "Reph (র্ above a letter)", "র্"
    elif cat == "phala":
        name = C.PHALA_NAMES.get(val, f"{val}-ফলা")
        bn, en, glyph = name, f"{name} (phala)", _DOTTED + C.VIRAMA + val
    elif cat == "kar":
        name = C.KAR_NAMES.get(val, "কার")
        bn, en, glyph = f"{name} ({_DOTTED}{val})", f"Vowel sign {_DOTTED}{val}", _DOTTED + val
    elif cat == "sign":
        name = C.SIGN_NAMES.get(val, "চিহ্ন")
        bn, en, glyph = name, f"{name} ({_DOTTED}{val})", _DOTTED + val
    elif cat == "letter":
        bn, en = f"বর্ণ {val}", f"Letter {val}"
    elif cat == "vowel":
        bn, en = f"স্বরবর্ণ {val}", f"Vowel letter {val}"
    elif cat == "hasanta":
        bn, en, glyph = "হসন্ত", "Hasanta (্)", _DOTTED + C.VIRAMA
    elif cat == "skip":
        bn, en, glyph = "শব্দ বাদ দেওয়া", "Skipped whole word", "—"
    else:
        bn, en = key, key
    return {"key": key, "category": cat, "category_bn": bn_cat, "category_en": en_cat,
            "bn": bn, "en": en, "glyph": glyph}


# Patterns that are worth teaching explicitly; plain letters are tracked too but
# ranked after these when a child has both.
TEACHING_PRIORITY = {"conj": 0, "reph": 0, "phala": 0, "kar": 1, "sign": 1, "hasanta": 2,
                     "vowel": 2, "letter": 3, "skip": 4}
