"""Deterministic readers for free-text owner answers.

Every function returns None (or an empty result) when the text does not say
the thing clearly; the caller then asks again instead of guessing.
"""

from __future__ import annotations

import re

from house_ai.domain.brief import Priority

_NUMBER_WORDS = {
    "no": 0, "none": 0, "zero": 0, "one": 1, "a": 1, "an": 1, "single": 1, "two": 2,
    "both": 2, "couple": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}  # fmt: skip
_NUM = r"(\d+(?:[.,]\d+)?|" + "|".join(sorted(_NUMBER_WORDS, key=len, reverse=True)) + r")"

_UNKNOWN = re.compile(
    r"\b(don'?t know|do not know|not sure|unsure|undecided|no idea|haven'?t decided|"
    r"not decided|can'?t say|cannot say|later|unknown|skip|no preference|don'?t mind|"
    r"either is fine|whatever you suggest)\b",
    re.I,
)
_NONE = re.compile(r"^\s*(no|none|nothing|nope|not really|no thanks|n/a)\s*[.!]?\s*$", re.I)
_YES = re.compile(
    r"\b(yes|yeah|yep|sure|definitely|of course|please|absolutely|certainly|want|need|"
    r"would like|we'?d like|important|must|essential|required)\b",
    re.I,
)
_NO = re.compile(
    r"\b(no|nope|not|don'?t|do not|doesn'?t|never|none|without|neither|nor)\b", re.I
)
_MUST = re.compile(
    r"\b(must|essential|required|need|needs|have to|non-negotiable|critical)\b", re.I
)
_NICE = re.compile(
    r"\b(would like|nice|prefer|ideally|if possible|bonus|wish|maybe|could)\b", re.I
)


def number(token: str) -> float | None:
    token = token.strip().lower().replace(",", ".")
    if token in _NUMBER_WORDS:
        return float(_NUMBER_WORDS[token])
    try:
        return float(token)
    except ValueError:
        return None


def is_unknown(text: str) -> bool:
    """The owner says they do not know or have not decided."""
    return bool(_UNKNOWN.search(text))


def is_none(text: str) -> bool:
    """The whole answer is a plain "no" / "none"."""
    return bool(_NONE.match(text))


def yes_no(text: str) -> bool | None:
    """True for a clear yes, False for a clear no, None when unclear or mixed."""
    yes, no = bool(_YES.search(text)), bool(_NO.search(text))
    if yes and not no:
        return True
    if no and not yes:
        return False
    if no and yes:
        # "we don't need ...", "no, but we want ..." stay unclear unless the
        # negation directly precedes the wish.
        if re.search(r"\b(don'?t|do not|doesn'?t|not)\s+(\w+\s+)?(want|need|like)\b", text, re.I):
            return False
    return None


def priority(text: str) -> Priority | None:
    if _MUST.search(text):
        return Priority.MUST
    if _NICE.search(text):
        return Priority.COULD if re.search(r"\b(maybe|bonus|could)\b", text, re.I) else (
            Priority.SHOULD
        )
    return None


def first_int(text: str) -> int | None:
    """The first whole number in the text (digits or a number word like "three")."""
    words = "|".join(w for w in _NUMBER_WORDS if w not in ("a", "an", "no", "none", "both",
                                                          "couple", "single"))
    for m in re.finditer(r"\b(\d+(?:[.,]\d+)?|" + words + r")\b", text, re.I):
        value = number(m.group(1))
        if value is not None and value == int(value):
            return int(value)
    return None


def count_of(text: str, nouns: str) -> int | None:
    """``N <noun>``, e.g. count_of("2 adults and three kids", "kids?|children")."""
    m = re.search(r"\b" + _NUM + r"\s+(?:\w+\s+)?(?:" + nouns + r")\b", text, re.I)
    if not m:
        return None
    value = number(m.group(1))
    return int(value) if value is not None and value == int(value) else None


def area_m2(text: str) -> float | None:
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(m2|m²|sqm|sq\.? ?m|square met(?:er|re)s?)", text, re.I)
    return number(m.group(1)) if m else None


_CURRENCIES = {
    "EUR": r"€|eur|euros?", "USD": r"\$|usd|dollars?", "GBP": r"£|gbp|pounds?",
    "IRR": r"irr|rials?", "CHF": r"chf|francs?", "TRY": r"try|lira",
}  # fmt: skip
_SCALE = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mio": 1e6, "million": 1e6, "billion": 1e9}


def money(text: str) -> tuple[float, str] | None:
    """An amount with a currency, e.g. "about 350k EUR" -> (350000.0, "EUR")."""
    m = re.search(
        r"(\d+(?:[.,]\d+)*)\s*(k|thousand|mio|million|billion|m\b)?", text.replace(" ", " "), re.I
    )
    if not m:
        return None
    raw = m.group(1)
    raw = raw.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", raw) else raw
    raw = raw.replace(".", "") if re.fullmatch(r"\d{1,3}(\.\d{3})+", raw) else raw
    value = number(raw)
    if value is None:
        return None
    if m.group(2):
        value *= _SCALE[m.group(2).lower()]
    for code, pattern in _CURRENCIES.items():
        if re.search(r"(?<![a-z])(" + pattern + r")(?![a-z])", text, re.I):
            return value, code
    return None


def choice(text: str, options: dict[str, list[str]]) -> str | None:
    """The single option whose keywords appear in the text; None if none or several."""
    hits = [
        key
        for key, words in options.items()
        if any(re.search(r"\b" + w + r"\b", text, re.I) for w in words)
    ]
    return hits[0] if len(hits) == 1 else None


def clauses(text: str) -> list[str]:
    return [c.strip() for c in re.split(r"[.;\n!?]|,\s*(?:and|but)\s+|\bbut\b", text) if c.strip()]


def clause_about(text: str, words: str) -> str | None:
    """The first clause mentioning one of ``words`` (a regex alternation)."""
    return next((c for c in clauses(text) if re.search(r"\b(" + words + r")", c, re.I)), None)


def items(text: str) -> list[str]:
    """Comma / "and" separated items, lower-cased and trimmed."""
    parts = re.split(r",|;|\band\b|\n|/", text)
    return [re.sub(r"^\s*(a|an|the|some|our|my)\s+", "", p.strip().lower()).strip(" .") for p in
            parts if p.strip(" .")]  # fmt: skip


# ------------------------------------------------------------ rooms

#: Canonical room words used in relationship and size answers.
ROOMS: dict[str, str] = {
    "kitchen": r"kitchen",
    "living": r"living(?: room| area)?|lounge|sitting room",
    "dining": r"dining(?: room| area)?",
    "main_bedroom": r"main bedroom|master bedroom|our bedroom|parents'? (?:bed)?room",
    "children_bedrooms": r"(?:children'?s|kids'?|childrens) (?:bed)?rooms?",
    "bedrooms": r"bedrooms?",
    "bathroom": r"bathrooms?",
    "office": r"office|study|workspace",
    "guest": r"guest(?: room| suite)?s?",
    "garage": r"garage|carport|parking",
    "laundry": r"laundry|utility room",
    "entry": r"entrance|entry|front door|hall",
    "garden": r"garden|yard",
    "terrace": r"terrace|patio",
    "elder_room": r"(?:grand)?(?:mother|father|parents?)'?s? room|granny flat",
}

_NEAR = r"next to|near|beside|adjacent to|connected to|open to|close to|opening (?:on)?to|by"
_APART = (
    r"away from|far from|separate from|separated from|not next to|apart from|not near|"
    r"isolated from|out of earshot of"
)


def room_in(text: str) -> str | None:
    for key, pattern in ROOMS.items():
        if re.search(r"\b(" + pattern + r")\b", text, re.I):
            return key
    return None


def relationships(text: str) -> list[str]:
    """Room relationships as ``"a|near|b"`` or ``"a|apart|b"`` strings."""
    out: list[str] = []
    for clause in clauses(text):
        for kind, pattern in (("apart", _APART), ("near", _NEAR)):
            m = re.search(r"(.*?)\b(" + pattern + r")\b(.*)", clause, re.I)
            if m:
                a, b = room_in(m.group(1)), room_in(m.group(3))
                if a and b and a != b:
                    rel = f"{a}|{kind}|{b}"
                    if rel not in out:
                        out.append(rel)
                break
    return out


def room_sizes(text: str) -> list[str]:
    """Size wishes as ``"room=40"`` (m²) or ``"room*1.3"`` (relative) strings."""
    out: list[str] = []
    for clause in re.split(r"[,;.\n]|\band\b|\bbut\b", text):
        room = room_in(clause)
        if room is None:
            continue
        a = area_m2(clause)
        if a is None:
            m = re.search(r"\b(?:about|around|roughly|at least)?\s*(\d+(?:[.,]\d+)?)\b", clause)
            a = number(m.group(1)) if m and re.search(r"\b(m|metre|meter)", clause) else None
        if a is not None:
            out.append(f"{room}={a:g}")
        elif re.search(r"\b(big|bigger|large|larger|generous|spacious)\b", clause, re.I):
            out.append(f"{room}*1.3")
        elif re.search(r"\b(small|smaller|compact|minimal)\b", clause, re.I):
            out.append(f"{room}*0.8")
    return out
