"""Bangla Unicode character classes used by the normaliser and the segmenter.

Everything here is plain data. Code points come from the Unicode Bengali block
(U+0980 to U+09FF).
"""

VIRAMA = "্"  # হসন্ত  ্
NUKTA = "়"  # ়
CHANDRABINDU = "ঁ"  # ঁ
ANUSVARA = "ং"  # ং
VISARGA = "ঃ"  # ঃ
KHANDA_TA = "ৎ"  # ৎ
AU_LENGTH_MARK = "ৗ"  # ৗ
ZWJ = "‍"
ZWNJ = "‌"

RA = "র"  # র
YA = "য"  # য
BA = "ব"  # ব
MA = "ম"  # ম
TA = "ত"  # ত

RRA = "ড়"  # ড়
RHA = "ঢ়"  # ঢ়
YYA = "য়"  # য়

_ASSIGNED_CONSONANTS = [
    c
    for c in range(0x0995, 0x09BA)
    if c not in (0x09A9, 0x09B1, 0x09B3, 0x09B4, 0x09B5)
]
CONSONANTS: frozenset[str] = frozenset(
    [chr(c) for c in _ASSIGNED_CONSONANTS] + [RRA, RHA, YYA]
)

INDEPENDENT_VOWELS: frozenset[str] = frozenset(
    [chr(c) for c in range(0x0985, 0x098D)]  # অ আ ই ঈ উ ঊ ঋ ঌ
    + ["এ", "ঐ", "ও", "ঔ", "ৠ", "ৡ"]  # এ ঐ ও ঔ ৠ ৡ
)

VOWEL_SIGNS: frozenset[str] = frozenset(
    [
        "া",  # া
        "ি",  # ি
        "ী",  # ী
        "ু",  # ু
        "ূ",  # ূ
        "ৃ",  # ৃ
        "ৄ",  # ৄ
        "ে",  # ে
        "ৈ",  # ৈ
        "ো",  # ো
        "ৌ",  # ৌ
        "ৢ",
        "ৣ",
    ]
)

SIGNS: frozenset[str] = frozenset([CHANDRABINDU, ANUSVARA, VISARGA])

DIGITS: frozenset[str] = frozenset(chr(c) for c in range(0x09E6, 0x09F0))

# Phala letters: a consonant that follows another consonant inside a cluster
# and is written as a reduced sign under or after it.
PHALA_LETTERS: frozenset[str] = frozenset([RA, YA, BA])

KAR_NAMES: dict[str, str] = {
    "া": "আ-কার",
    "ি": "ই-কার",
    "ী": "ঈ-কার",
    "ু": "উ-কার",
    "ূ": "ঊ-কার",
    "ৃ": "ঋ-কার",
    "ৄ": "ৠ-কার",
    "ে": "এ-কার",
    "ৈ": "ঐ-কার",
    "ো": "ও-কার",
    "ৌ": "ঔ-কার",
}

SIGN_NAMES: dict[str, str] = {
    CHANDRABINDU: "চন্দ্রবিন্দু",
    ANUSVARA: "অনুস্বার",
    VISARGA: "বিসর্গ",
}

PHALA_NAMES: dict[str, str] = {RA: "র-ফলা", YA: "য-ফলা", BA: "ব-ফলা"}

# Punctuation that may appear in passages. It is kept for display and removed
# for comparison.
PUNCTUATION: frozenset[str] = frozenset(
    list("।॥,.;:!?'\"()[]{}-–—‘’“”…/") + ["।", "॥"]
)


def is_bangla_letter(ch: str) -> bool:
    return (
        ch in CONSONANTS
        or ch in INDEPENDENT_VOWELS
        or ch in VOWEL_SIGNS
        or ch in SIGNS
        or ch in (VIRAMA, KHANDA_TA, NUKTA, AU_LENGTH_MARK)
    )
