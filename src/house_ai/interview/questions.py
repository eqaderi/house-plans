"""The question bank: what the interview can ask, when, and how answers are read.

Questions are asked one at a time in this order, skipping those whose
condition does not hold (e.g. no garage question for a household without
cars) and those whose slots are already known from earlier answers. A
question whose answer leaves a slot open is followed up with that slot's own
short question. Parsers are deterministic; an optional LLM may only propose
values for the same slots (see :mod:`house_ai.interview.llm`).
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from house_ai.domain.brief import BriefTopic as T
from house_ai.domain.brief import FactValue

from . import parsing as p

Values = dict[str, Any]
Parser = Callable[[str], dict[str, FactValue]]


@dataclass(frozen=True)
class Slot:
    key: str
    topic: T
    label: str
    #: Short question used to follow up when the main answer left this open.
    followup: str
    parse: Parser
    #: The owner's statement about the household is a fact, not a wish.
    is_fact: bool = False
    #: Must be known (or explicitly unknown) before the program can be approved.
    critical: bool = False


@dataclass(frozen=True)
class Question:
    id: str
    topic: T
    text: str
    slots: tuple[str, ...]
    parse: Parser
    #: Ask only when this holds for the values known so far.
    when: Callable[[Values, Any], bool] = lambda v, site: True
    #: Slots that, if still open after the answer, get a follow-up question.
    required: tuple[str, ...] = ()
    #: Explanation shown when the answer could not be read.
    hint: str = ""
    examples: list[str] = field(default_factory=list)

    def render(self, values: Values, site: Any) -> str:
        return self.text.format(**_render_context(values, site))


def _render_context(values: Values, site: Any) -> dict[str, str]:
    relief = getattr(site, "relief_m", None)
    area = getattr(site, "parcel_area_m2", None)
    verified = bool(getattr(site, "verified", False))
    return {
        "relief": f"{relief:.1f}" if relief is not None else "?",
        "area": f"{area:.0f}" if area is not None else "?",
        "site_note": "" if verified else " (from the survey; you have not confirmed the site yet)",
    }


# ----------------------------------------------------------------- parsers


def _single(slot: str, reader: Callable[[str], FactValue]) -> Parser:
    def parse(text: str) -> dict[str, FactValue]:
        value = reader(text)
        return {} if value is None else {slot: value}

    return parse


def _bool(slot: str) -> Parser:
    return _single(slot, p.yes_no)


def _int(slot: str, nouns: str | None = None) -> Parser:
    def read(text: str) -> FactValue:
        if nouns:
            n = p.count_of(text, nouns)
            if n is not None:
                return n
        if p.is_none(text):
            return 0
        return p.first_int(text)

    return _single(slot, read)


def _choice(slot: str, options: dict[str, list[str]]) -> Parser:
    return _single(slot, lambda text: p.choice(text, options))


def _household(text: str) -> dict[str, FactValue]:
    adults = p.count_of(text, r"adults?|grown-ups?|parents") or 0
    children = p.count_of(text, r"children|kids?|child|sons?|daughters?|babies|baby|teenagers?")
    elders = p.count_of(text, r"grandparents?|elders?|elderly|seniors?")
    lowered = text.lower()
    if not adults:
        if re.search(r"\b(me|i|myself)\b", lowered):
            adults += 1
        if re.search(r"\b(wife|husband|partner|spouse|girlfriend|boyfriend)\b", lowered):
            adults += 1
        if re.search(r"\b(we are a couple|my partner and i|the two of us)\b", lowered):
            adults = max(adults, 2)
    if children is None:
        children = len(re.findall(r"\b(son|daughter|child|kid|baby)\b", lowered))
    if elders is None:
        elders = len(
            re.findall(
                r"\b(my|our|his|her) (mother|father|mum|mom|dad|grandmother|grandfather|"
                r"mother-in-law|father-in-law)\b",
                lowered,
            )
        )
    if not (adults or children or elders):
        total = p.first_int(text)
        return {"household_size": total} if total else {}
    return {
        "adults": adults,
        "children": children,
        "elders": elders,
        "household_size": adults + children + elders,
    }


def _bathrooms(text: str) -> dict[str, FactValue]:
    out: dict[str, FactValue] = {}
    n = p.count_of(text, r"bathrooms?|baths?") or (
        p.first_int(text) if not re.search(r"en-?suite|own bathroom", text, re.I) else None
    )
    if n is None:
        n = p.first_int(p.clause_about(text, "bath") or "")
    if n is not None:
        out["bathrooms"] = n
    clause = p.clause_about(text, r"en-?suite|own bathroom|private bathroom")
    if clause is not None:
        yn = p.yes_no(clause)
        out["ensuite"] = True if yn is None else yn
    return out


def _floors(text: str) -> dict[str, FactValue]:
    if re.search(r"\b(single[- ]stor(e)?y|one level|bungalow|one floor|ground floor only)\b",
                 text, re.I):  # fmt: skip
        return {"floors": 1}
    n = p.count_of(text, r"floors?|stor(?:e)?ys?|levels?") or p.first_int(text)
    return {"floors": n} if n else {}


def _kitchen(text: str) -> dict[str, FactValue]:
    out: dict[str, FactValue] = {}
    if re.search(r"\b(every ?day|daily|a lot|often|heavy|traditional|big meals|love cooking)\b",
                 text, re.I):  # fmt: skip
        out["cooking"] = "frequent"
    elif re.search(r"\b(rarely|seldom|little|light|simple|not much|hardly)\b", text, re.I):
        out["cooking"] = "light"
    smell = p.clause_about(text, r"smell|odou?r|fumes")
    if smell is not None:
        if re.search(r"\b(don'?t mind|do not mind|fine|okay|ok|no problem|not a problem)\b",
                     smell, re.I):  # fmt: skip
            out["kitchen_smell_separate"] = False
        elif re.search(r"\b(stay out|keep|separate|closed|not reach|away|out of)\b", smell, re.I):
            out["kitchen_smell_separate"] = True
    pantry = p.clause_about(text, "pantry|larder")
    if pantry is not None:
        yn = p.yes_no(pantry)
        out["pantry"] = True if yn is None else yn
    return out


def _guests(text: str) -> dict[str, FactValue]:
    out: dict[str, FactValue] = {}
    kind = p.choice(
        text,
        {
            "suite": [r"suite", r"own bathroom", r"separate (?:flat|apartment|unit)"],
            "room": [r"guest ?room", r"(?:their|a) own room", r"spare room", r"a room"],
            "none": [r"no guests?", r"never", r"rarely", r"hardly ever", r"sofa", r"no need"],
        },
    )
    if kind:
        out["guest_accommodation"] = kind
    freq = p.choice(
        text,
        {
            "often": [r"often", r"every (?:week|month)", r"frequently", r"weeks? at a time",
                      r"months?"],
            "sometimes": [r"sometimes", r"few times a year", r"occasionally", r"holidays"],
            "rarely": [r"rarely", r"hardly ever", r"once a year", r"never"],
        },
    )  # fmt: skip
    if freq:
        out["guest_frequency"] = freq
    return out


def _office(text: str) -> dict[str, FactValue]:
    out: dict[str, FactValue] = {}
    if p.is_none(text) or re.search(r"\b(nobody|no one|none of us|we don'?t)\b", text, re.I):
        return {"workspaces": 0}
    n = p.count_of(text, r"(?:work)?(?:places?|spaces?|desks?|offices?|stud(?:y|ies)|rooms?)")
    if n is None:
        n = p.count_of(text, r"(?:of us|people|persons?)") or p.first_int(text)
    if n is None and re.search(r"\b(i|my (?:wife|husband|partner)|one of us)\b.*\b(work|study)",
                               text, re.I):  # fmt: skip
        n = 1
    if n is not None:
        out["workspaces"] = n
    quiet = p.clause_about(text, r"quiet|calls?|concentrat|noise|meetings")
    if quiet is not None:
        out["office_quiet"] = not re.search(r"\b(doesn'?t|don'?t|not)\b", quiet, re.I)
    return out


def _parking(text: str) -> dict[str, FactValue]:
    out: dict[str, FactValue] = {}
    n = p.count_of(text, r"cars?|vehicles?") or (0 if p.is_none(text) else None)
    if n is None and re.search(r"\b(no car|don'?t have a car|without a car)\b", text, re.I):
        n = 0
    if n is not None:
        out["cars"] = n
    kind = p.choice(
        text,
        {"garage": [r"garage"], "carport": [r"carport"], "open": [r"open parking", r"driveway",
                                                                     r"outside", r"street"]},
    )  # fmt: skip
    if kind:
        out["parking_type"] = kind
    ev = p.clause_about(text, r"ev\b|electric|charg")
    if ev is not None:
        yn = p.yes_no(ev)
        out["ev_charging"] = True if yn is None else yn
    return out


def _storage(text: str) -> dict[str, FactValue]:
    out: dict[str, FactValue] = {}
    laundry = p.clause_about(text, r"laundry|washing|utility")
    if laundry is not None:
        yn = p.yes_no(laundry)
        out["laundry_room"] = True if yn is None else yn
    storage = p.clause_about(text, r"storage|store ?room|storeroom|basement|attic")
    if storage is not None:
        yn = p.yes_no(storage)
        out["storage_room"] = True if yn is None else yn
    if not out:
        yn = p.yes_no(text)
        if yn is not None:
            out = {"laundry_room": yn, "storage_room": yn}
    return out


_OUTDOOR = {
    "roof_terrace": r"roof(?: ?top)? terrace|roof garden",
    "terrace": r"terrace|patio|deck",
    "garden": r"garden|lawn|yard",
    "balcony": r"balcon(?:y|ies)",
    "pool": r"pool",
    "play_area": r"play(?:ground| area)?",
    "vegetable_garden": r"vegetables?|kitchen garden|orchard",
}


def _outdoor(text: str) -> dict[str, FactValue]:
    if p.is_none(text):
        return {"outdoor": []}
    found = []
    rest = text
    for key, pattern in _OUTDOOR.items():
        hit = re.search(r"\b(" + pattern + r")", rest, re.I)
        if hit is None:
            continue
        negated = re.search(r"\b(no|not|without|don'?t (?:want|need))\s+(?:a |an |any )?(?:"
                            + pattern + r")", rest, re.I)  # fmt: skip
        if not negated:
            found.append(key)
        if key == "roof_terrace":
            rest = re.sub(pattern, "", rest, flags=re.I)
    return {"outdoor": found} if found or re.search(r"\bno\b", text, re.I) else {}


def _accessibility(text: str) -> dict[str, FactValue]:
    out: dict[str, FactValue] = {}
    kind = p.choice(
        text,
        {
            "wheelchair": [r"wheelchair"],
            "step_free": [r"step-?free", r"no stairs", r"avoid stairs",
                          r"(?:can'?t|cannot|can not|unable to) (?:climb|use|manage) stairs",
                          r"walker", r"difficulty walking"],
            "future_ready": [r"later", r"future", r"when we are older", r"ready for", r"age"],
        },
    )  # fmt: skip
    if kind is None and (p.is_none(text) or re.search(r"\b(nobody|no one|not needed)\b", text,
                                                       re.I)):  # fmt: skip
        kind = "none"
    if kind:
        out["accessibility"] = kind
    lift = p.clause_about(text, r"lift|elevator")
    if lift is not None:
        yn = p.yes_no(lift)
        out["lift"] = True if yn is None else yn
    return out


def _privacy(text: str) -> dict[str, FactValue]:
    out: dict[str, FactValue] = {}
    level = p.choice(
        text,
        {
            "high": [r"very", r"high(?:ly)?", r"extremely", r"essential", r"a lot", r"must",
                     r"very important"],
            "normal": [r"normal", r"some", r"moderate", r"average", r"somewhat"],
            "low": [r"not important", r"low", r"don'?t care", r"not much"],
        },
    )  # fmt: skip
    if level:
        out["privacy"] = level
    beds = p.clause_about(text, r"bedrooms?|sleeping")
    if beds is not None:
        out["bedrooms_separate"] = bool(re.search(r"\b(away|separate|apart|quiet|private|upstairs)",
                                                  beds, re.I))  # fmt: skip
    return out


def _relationships(text: str) -> dict[str, FactValue]:
    if p.is_none(text):
        return {"relationships": []}
    rels = p.relationships(text)
    return {"relationships": rels} if rels else {}


def _sizes(text: str) -> dict[str, FactValue]:
    if p.is_none(text) or re.search(r"\b(usual is fine|normal sizes?|standard)\b", text, re.I):
        return {"room_sizes": []}
    sizes = p.room_sizes(text)
    return {"room_sizes": sizes} if sizes else {}


def _light(text: str) -> dict[str, FactValue]:
    out: dict[str, FactValue] = {"light_wishes": text.strip()}
    vent = p.clause_about(text, r"ventilat|fresh air|cross|breeze|draft")
    if vent is not None:
        yn = p.yes_no(vent)
        out["cross_ventilation"] = True if yn is None else yn
    return out


def _budget(text: str) -> dict[str, FactValue]:
    m = p.money(text)
    return {"budget": f"{m[0]:.0f} {m[1]}"} if m else {}


def _area(text: str) -> dict[str, FactValue]:
    a = p.area_m2(text)
    if a is None:
        n = p.first_int(text)
        a = float(n) if n and n >= 20 else None
    return {"target_area": a} if a else {}


def _priorities(text: str) -> dict[str, FactValue]:
    found = [i for i in p.items(text) if i]
    return {"priorities": found[:5]} if found else {}


def _expansion(text: str) -> dict[str, FactValue]:
    yn = p.yes_no(text)
    if yn is None and re.search(r"\b(maybe|possibly|perhaps|might)\b", text, re.I):
        yn = True
    return {} if yn is None else {"future_expansion": yn}


def _practices(text: str) -> dict[str, FactValue]:
    out: dict[str, FactValue] = {}
    if p.is_none(text):
        return {"prayer_room": False, "gathering_space": False}
    prayer = p.clause_about(text, r"pray|prayer|worship|meditat|shrine")
    if prayer is not None:
        yn = p.yes_no(prayer)
        out["prayer_room"] = True if yn is None else yn
    gather = p.clause_about(text, r"gather|guests|family events|parties|large|celebrat")
    if gather is not None:
        yn = p.yes_no(gather)
        out["gathering_space"] = True if yn is None else yn
    return out


def _slope(text: str) -> dict[str, FactValue]:
    kind = p.choice(
        text,
        {
            "step_down": [r"step", r"split", r"down the slope", r"follow", r"terrace(?:d)? into",
                          r"lower floor", r"garden level", r"basement"],
            "platform": [r"flat", r"platform", r"level ground", r"one level", r"cut into"],
        },
    )  # fmt: skip
    if kind is None and re.search(r"\b(don'?t mind|either|no preference)\b", text, re.I):
        kind = "no_preference"
    return {"slope_strategy": kind} if kind else {}


# ------------------------------------------------------------------- slots

SLOTS: dict[str, Slot] = {
    s.key: s
    for s in [
        Slot("adults", T.HOUSEHOLD, "Adults", "How many adults will live in the house?",
             _int("adults", r"adults?"), is_fact=True, critical=True),
        Slot("children", T.HOUSEHOLD, "Children", "How many children will live in the house?",
             _int("children", r"children|kids?"), is_fact=True),
        Slot("elders", T.MULTIGENERATIONAL, "Older relatives living with you",
             "Will older relatives (e.g. grandparents) live with you? How many?",
             _int("elders", r"grandparents?|elders?|relatives?"), is_fact=True),
        Slot("household_size", T.HOUSEHOLD, "People in the household",
             "How many people will live in the house in total?", _int("household_size"),
             is_fact=True),
        Slot("children_own_rooms", T.BEDROOMS_BATHROOMS, "Each child has their own bedroom",
             "Should each child have their own bedroom?", _bool("children_own_rooms")),
        Slot("elder_step_free", T.ACCESSIBILITY, "Older relative must avoid stairs",
             "Does your older relative need to avoid stairs?", _bool("elder_step_free"),
             is_fact=True),
        Slot("bedrooms", T.BEDROOMS_BATHROOMS, "Bedrooms",
             "How many bedrooms in total, including any guest bedroom?",
             _int("bedrooms", r"bedrooms?|rooms?"), critical=True),
        Slot("bathrooms", T.BEDROOMS_BATHROOMS, "Bathrooms",
             "How many bathrooms (with shower or bath) do you want?",
             _int("bathrooms", r"bathrooms?|baths?"), critical=True),
        Slot("ensuite", T.BEDROOMS_BATHROOMS, "Main bedroom has its own bathroom",
             "Should the main bedroom have its own bathroom (en-suite)?", _bool("ensuite")),
        Slot("floors", T.LEVELS, "Floors", "How many floors should the house have?", _floors,
             critical=True),
        Slot("slope_strategy", T.SITE_RESPONSE, "How the house meets the slope",
             "Should the house step down the slope, or sit on one flat platform?", _slope),
        Slot("entry_at_road", T.SITE_RESPONSE, "Entrance and parking at road level",
             "Should the main entrance and parking be at road level?", _bool("entry_at_road")),
        Slot("open_plan", T.LIFESTYLE, "Open living, dining and kitchen",
             "Do you want living, dining and kitchen as one open space?", _bool("open_plan")),
        Slot("cooking", T.COOKING, "How much you cook",
             "Do you cook every day, or only light meals?",
             _choice("cooking", {"frequent": [r"every ?day", r"daily", r"a lot", r"often"],
                                 "light": [r"light", r"rarely", r"little"]})),
        Slot("kitchen_smell_separate", T.KITCHEN_TYPE, "Cooking smells kept out of living areas",
             "Should cooking smells stay out of the living room?",
             _bool("kitchen_smell_separate")),
        Slot("pantry", T.KITCHEN_TYPE, "Pantry", "Do you want a pantry?", _bool("pantry")),
        Slot("dining", T.DINING, "Where everyday meals are eaten",
             "Do you eat in the kitchen, or do you want a separate dining room?",
             _choice("dining", {"kitchen": [r"kitchen"], "separate_room": [r"separate",
                                                                           r"dining room"]})),
        Slot("guest_accommodation", T.LONG_TERM_GUESTS, "Guest accommodation",
             "Should guests have no special room, a guest room, or a guest suite with its own "
             "bathroom?", _guests),
        Slot("guest_frequency", T.LONG_TERM_GUESTS, "How often guests stay",
             "How often do guests stay overnight?", _guests),
        Slot("workspaces", T.WORK_STUDY, "Workplaces at home",
             "How many people need a place to work or study at home?", _office),
        Slot("office_quiet", T.WORK_STUDY, "Workplace must be quiet",
             "Does the workplace need to be quiet (for calls or concentration)?",
             _bool("office_quiet")),
        Slot("cars", T.VEHICLES, "Cars to park", "How many cars should fit?", _parking),
        Slot("parking_type", T.VEHICLES, "Type of parking",
             "A closed garage, a carport, or open parking?", _parking),
        Slot("ev_charging", T.EV_CHARGING, "EV charging", "Do you need an EV charger?",
             _bool("ev_charging")),
        Slot("laundry_room", T.LAUNDRY, "Separate laundry room",
             "Do you want a separate laundry room?", _bool("laundry_room")),
        Slot("storage_room", T.STORAGE, "Store room", "Do you want a separate store room?",
             _bool("storage_room")),
        Slot("outdoor", T.OUTDOOR_LIVING, "Outdoor spaces",
             "Which outdoor spaces do you want (terrace, garden, balcony, pool…)?", _outdoor),
        Slot("accessibility", T.ACCESSIBILITY, "Accessibility",
             "Does anyone need step-free access or a wheelchair, now or later?", _accessibility),
        Slot("lift", T.ACCESSIBILITY, "Lift", "Do you want a lift?", _bool("lift")),
        Slot("accessible_ground_suite", T.ACCESSIBILITY,
             "Bedroom and bathroom on the entrance level for step-free living",
             "Should one bedroom and a bathroom be on the entrance level?",
             _bool("accessible_ground_suite")),
        Slot("privacy", T.PRIVACY, "Privacy from street and neighbours",
             "How important is privacy from the street and neighbours?", _privacy),
        Slot("bedrooms_separate", T.PRIVACY, "Bedrooms kept away from living areas",
             "Should the bedrooms be kept away from the living areas?",
             _bool("bedrooms_separate")),
        Slot("relationships", T.ROOM_RELATIONSHIPS, "Rooms next to each other or kept apart",
             "Which rooms must be next to each other or kept apart?", _relationships),
        Slot("light_wishes", T.DAYLIGHT, "Daylight wishes",
             "Which rooms should get morning or evening sun?", _light),
        Slot("cross_ventilation", T.NATURAL_VENTILATION, "Cross-ventilation",
             "Is cross-ventilation (windows on two sides) important?",
             _bool("cross_ventilation")),
        Slot("room_sizes", T.ROOM_SIZES, "Room size wishes",
             "Are there rooms you want bigger or smaller than usual?", _sizes),
        Slot("style", T.MATERIALS_STYLE, "Style and materials",
             "Which style or materials do you like?",
             lambda t: {"style": t.strip()} if t.strip() else {}),
        Slot("budget", T.BUDGET, "Building budget",
             "What is your building budget, with currency?", _budget),
        Slot("target_area", T.TARGET_AREA, "Total floor area in mind",
             "Do you have a total floor area in mind (m²)?", _area),
        Slot("priorities", T.PRIORITIES, "Top priorities", "What matters most to you?",
             _priorities),
        Slot("future_expansion", T.FUTURE_EXPANSION, "May extend later",
             "Might you want to extend the house later?", _expansion),
        Slot("prayer_room", T.RELIGIOUS_NEEDS, "Prayer or quiet room",
             "Do you need a room for prayer or meditation?", _bool("prayer_room")),
        Slot("gathering_space", T.CULTURAL_PRACTICES, "Space for large family gatherings",
             "Do you need space for large family gatherings?", _bool("gathering_space")),
        Slot("kitchen_layout", T.KITCHEN_TYPE, "Kitchen layout",
             "Should the kitchen be open, semi-open (glass doors) or closed?",
             _choice("kitchen_layout", {"open": [r"open"], "semi_open": [r"semi", r"glass",
                                                                          r"sliding"],
                                        "closed": [r"closed", r"separate"]})),
    ]
}  # fmt: skip


def _known(v: Values, key: str) -> bool:
    return key in v and v[key] is not None


def _relief(site: Any) -> float:
    return getattr(site, "relief_m", None) or 0.0


QUESTIONS: list[Question] = [
    Question(
        "q-household", T.HOUSEHOLD,
        "Let's start with the people. Who will live in the house? For example "
        "'2 adults and 2 children (6 and 9)' or 'my wife, me and my mother'.",
        ("adults", "children", "elders", "household_size"), _household,
        required=("adults",),
        hint="I could not tell how many adults and children. Try '2 adults and 1 child'.",
    ),
    Question(
        "q-children-rooms", T.BEDROOMS_BATHROOMS,
        "Should each child have their own bedroom, or can some of them share?",
        ("children_own_rooms",),
        lambda t: {"children_own_rooms": False} if re.search(r"\bshar", t, re.I) else (
            {"children_own_rooms": True} if re.search(r"\bown\b|each|separate", t, re.I)
            else {}),
        when=lambda v, s: (v.get("children") or 0) >= 2,
    ),
    Question(
        "q-elder", T.MULTIGENERATIONAL,
        "Does your older relative need to avoid stairs, now or in the next few years?",
        ("elder_step_free",), _bool("elder_step_free"),
        when=lambda v, s: (v.get("elders") or 0) >= 1,
    ),
    Question(
        "q-bedrooms", T.BEDROOMS_BATHROOMS,
        "How many bedrooms do you want in total, including any guest bedroom?",
        ("bedrooms",), _int("bedrooms", r"bedrooms?|rooms?"),
        hint="Please give a number, e.g. '4 bedrooms'.",
    ),
    Question(
        "q-bathrooms", T.BEDROOMS_BATHROOMS,
        "How many bathrooms would you like, and should the main bedroom have its own "
        "bathroom (en-suite)?",
        ("bathrooms", "ensuite"), _bathrooms, required=("bathrooms", "ensuite"),
    ),
    Question(
        "q-floors", T.LEVELS,
        "How many floors would you like the house to have? 'Not sure yet' is a fine answer.",
        ("floors",), _floors,
    ),
    Question(
        "q-slope", T.SITE_RESPONSE,
        "The survey shows the ground falls about {relief} m across the parcel{site_note}. "
        "Would you like the house to step down the slope (split levels, or a lower floor "
        "opening to the garden), or to sit on one flat platform cut into the ground? "
        "'No preference' is fine too.",
        ("slope_strategy",), _slope, when=lambda v, s: _relief(s) >= 2.0,
    ),
    Question(
        "q-entry", T.SITE_RESPONSE,
        "Should the main entrance and the parking be at road level, with the rest of the "
        "house below or above it?",
        ("entry_at_road",), _bool("entry_at_road"),
        when=lambda v, s: _relief(s) >= 2.0 and (v.get("floors") or 2) > 1,
    ),
    Question(
        "q-living", T.LIFESTYLE,
        "How do you like to live day to day: one open space for living, dining and "
        "kitchen, or separate rooms?",
        ("open_plan",),
        lambda t: {"open_plan": True} if re.search(r"\bopen\b", t, re.I) and not re.search(
            r"\bnot open|closed|separate", t, re.I) else (
            {"open_plan": False} if re.search(r"separate|closed|not open|distinct", t, re.I)
            else {}),
    ),
    Question(
        "q-kitchen", T.COOKING,
        "Tell me about cooking: do you cook every day or only light meals, should cooking "
        "smells stay out of the living room, and would you like a pantry?",
        ("cooking", "kitchen_smell_separate", "pantry"), _kitchen,
        required=("kitchen_smell_separate",),
    ),
    Question(
        "q-dining", T.DINING,
        "Where do you want to eat everyday meals: at a table in the kitchen, or in a "
        "separate dining room?",
        ("dining",), SLOTS["dining"].parse, when=lambda v, s: v.get("open_plan") is False,
    ),
    Question(
        "q-guests", T.LONG_TERM_GUESTS,
        "How often do guests stay overnight? Should they have no special room, a guest "
        "room, or a guest suite with its own bathroom?",
        ("guest_accommodation", "guest_frequency"), _guests,
        required=("guest_accommodation",),
    ),
    Question(
        "q-office", T.WORK_STUDY,
        "Does anyone work or study from home? How many separate workplaces do you need, "
        "and do they need to be quiet?",
        ("workspaces", "office_quiet"), _office, required=("workspaces",),
    ),
    Question(
        "q-office-quiet", T.WORK_STUDY,
        "Does the workplace need to be quiet, for example for calls?",
        ("office_quiet",), _bool("office_quiet"),
        when=lambda v, s: (v.get("workspaces") or 0) > 0,
    ),
    Question(
        "q-parking", T.VEHICLES,
        "How many cars should fit on the property, and do you want a closed garage, a "
        "carport or open parking? Do you need an electric-car charger?",
        ("cars", "parking_type", "ev_charging"), _parking, required=("cars",),
    ),
    Question(
        "q-parking-type", T.VEHICLES,
        "For the car(s): a closed garage, a carport, or open parking?",
        ("parking_type",), _parking, when=lambda v, s: (v.get("cars") or 0) > 0,
    ),
    Question(
        "q-storage", T.STORAGE,
        "Do you want a separate laundry room, and extra storage such as a store room?",
        ("laundry_room", "storage_room"), _storage,
    ),
    Question(
        "q-outdoor", T.OUTDOOR_LIVING,
        "Which outdoor spaces matter to you: a terrace, a garden, a balcony, a roof "
        "terrace, a pool, a play area? Say 'none' if none.",
        ("outdoor",), _outdoor,
    ),
    Question(
        "q-accessibility", T.ACCESSIBILITY,
        "Does anyone need step-free access or a wheelchair now, or would you like the "
        "house ready for that later? Would you like a lift?",
        ("accessibility", "lift"), _accessibility, required=("accessibility",),
    ),
    Question(
        "q-lift", T.ACCESSIBILITY, "Would you like a lift between the floors?",
        ("lift",), _bool("lift"),
        when=lambda v, s: (v.get("floors") or 1) > 1 and (
            v.get("accessibility") in ("step_free", "wheelchair", "future_ready")
            or v.get("elder_step_free") is True
        ),
    ),
    Question(
        "q-privacy", T.PRIVACY,
        "How important is privacy from the street and the neighbours? Should the bedrooms "
        "be kept away from the living areas?",
        ("privacy", "bedrooms_separate"), _privacy,
    ),
    Question(
        "q-relationships", T.ROOM_RELATIONSHIPS,
        "Are there rooms that must be next to each other, or kept apart? For example "
        "'kitchen next to the garden' or 'office away from the children's rooms'. "
        "Say 'none' if nothing comes to mind.",
        ("relationships",), _relationships,
        hint="I could not tell which rooms you meant. Try 'kitchen next to the dining room'.",
    ),
    Question(
        "q-light", T.DAYLIGHT,
        "What about daylight and fresh air: which rooms should get morning or evening sun, "
        "and is cross-ventilation (windows on two sides) important?",
        ("light_wishes", "cross_ventilation"), _light,
    ),
    Question(
        "q-sizes", T.ROOM_SIZES,
        "Are there rooms you want bigger or smaller than usual? For example 'living room "
        "about 40 m²' or 'small bedrooms are fine'. 'Usual is fine' is an answer too.",
        ("room_sizes",), _sizes,
    ),
    Question(
        "q-practices", T.CULTURAL_PRACTICES,
        "Do you need space for cultural or religious practices, such as a prayer room, or "
        "room for large family gatherings?",
        ("prayer_room", "gathering_space"), _practices,
    ),
    Question(
        "q-style", T.MATERIALS_STYLE,
        "Which architectural style or materials do you like (for example modern, "
        "traditional, brick, stone, wood, plaster)?",
        ("style",), SLOTS["style"].parse,
    ),
    Question(
        "q-budget", T.BUDGET,
        "What is your budget for building the house, with the currency? A rough figure or "
        "'not decided' is fine.",
        ("budget",), _budget,
        hint="Please give an amount with a currency, e.g. '350,000 EUR', or say 'not decided'.",
    ),
    Question(
        "q-area", T.TARGET_AREA,
        "Do you have a total floor area in mind (in m²)? If not, I will estimate it from the "
        "rooms.",
        ("target_area",), _area,
    ),
    Question(
        "q-priorities", T.PRIORITIES,
        "If not everything fits, what matters most? Please name your top three priorities.",
        ("priorities",), _priorities,
    ),
    Question(
        "q-expansion", T.FUTURE_EXPANSION,
        "Might you want to extend the house later, for example another bedroom or a floor?",
        ("future_expansion",), _expansion,
    ),
]  # fmt: skip

QUESTION_BY_ID: dict[str, Question] = {q.id: q for q in QUESTIONS}
assert all(s in SLOTS for q in QUESTIONS for s in q.slots)

#: Slots that answers to any question may fill, when said unambiguously
#: ("we need 4 bedrooms" in the household answer). Avoids repeating a question.
OPPORTUNISTIC: dict[str, Parser] = {
    "bedrooms": lambda t: {"bedrooms": n} if (n := p.count_of(t, r"bedrooms?")) else {},
    "bathrooms": lambda t: {"bathrooms": n} if (n := p.count_of(t, r"bathrooms?")) else {},
    "floors": lambda t: {"floors": n} if (n := p.count_of(t, r"floors?|stor(?:e)?ys?")) else {},
    "cars": lambda t: {"cars": n} if (n := p.count_of(t, r"cars?")) is not None else {},
    "lift": lambda t: {"lift": True} if re.search(r"\b(need|want) (?:a )?(lift|elevator)",
                                                  t, re.I) else {},
}  # fmt: skip


def followup_id(question_id: str, slot: str) -> str:
    return f"{question_id}#{slot}"


def question_for(question_id: str) -> tuple[Question, str | None]:
    """The question (and slot, for a follow-up) behind a pending question id."""
    base, _, slot = question_id.partition("#")
    return QUESTION_BY_ID[base], slot or None


def needed_bedrooms(v: Values) -> int | None:
    """Bedrooms the household needs by what the owner said about sharing."""
    if not _known(v, "adults"):
        return None
    children = v.get("children") or 0
    own = v.get("children_own_rooms")
    kids = children if own is not False else math.ceil(children / 2)
    guest = 1 if v.get("guest_accommodation") == "room" else 0
    return max(1, math.ceil(v["adults"] / 2)) + kids + (v.get("elders") or 0) + guest
