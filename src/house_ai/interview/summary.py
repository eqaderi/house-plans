"""Plain-language summary of the interview for the owner to review."""

from __future__ import annotations

from house_ai.domain.interview import InterviewSession, SiteContext

from .brief_builder import describe
from .questions import QUESTION_BY_ID, SLOTS
from .state import fold, next_prompt, open_contradictions, resolved_contradictions

_LABEL = {
    "confirmed": "confirmed by you",
    "inference": "understood from your answer, please confirm",
    "unknown": "you said: not known / not decided",
}


def summary_markdown(session: InterviewSession, site: SiteContext | None = None) -> str:
    state = fold(session)
    lines = ["# What I have understood so far", ""]
    if site is not None and site.parcel_area_m2:
        note = "confirmed by you" if site.verified else "from the survey, NOT yet confirmed by you"
        lines += [
            "## Your site",
            "",
            f"- Parcel area about {site.parcel_area_m2:.0f} m² ({note})",
        ]
        if site.relief_m is not None:
            lines.append(f"- The ground falls about {site.relief_m:.1f} m across the parcel")
        if site.frontage_m:
            lines.append(f"- Road frontage about {site.frontage_m:.1f} m")
        lines.append("")
    by_topic: dict[str, list[str]] = {}
    for slot, st in state.slots.items():
        spec = SLOTS[slot]
        by_topic.setdefault(spec.topic.value.replace("_", " "), []).append(
            f"- {spec.label}: **{describe(st.value)}** ({_LABEL[st.status]})"
        )
    for topic in sorted(by_topic):
        lines += [f"## {topic.capitalize()}", "", *sorted(by_topic[topic]), ""]
    custom_notes = [
        turn
        for qid, turn in state.answers.items()
        if qid.partition("#")[0] not in QUESTION_BY_ID and turn.text
    ]
    if custom_notes:
        lines += ["## Additional notes", ""]
        for turn in custom_notes:
            prefix = f"{turn.question_text} — " if turn.question_text else ""
            lines.append(f'- {prefix}"{turn.text}"')
        lines.append("")
    pending = state.unconfirmed()
    if pending:
        lines += [
            "## Please confirm",
            "",
            "These come from my reading of your answers. Say if any is wrong:",
            "",
            *[f"- {SLOTS[s].label}: {describe(state.slots[s].value)}" for s in pending],
            "",
        ]
    conflicts = open_contradictions(state)
    if conflicts:
        lines += ["## Things that do not fit together", ""]
        for f in conflicts:
            lines += [f"- **{f.statement}** {f.tradeoff}"]
            lines += [f"  {i + 1}. {o.label}" for i, o in enumerate(f.options)]
        lines.append("")
    resolved = resolved_contradictions(state)
    if resolved:
        lines += ["## Decisions you made", ""]
        for f, turn in resolved:
            what = f.statement if f else turn.contradiction_id
            choice = f"option {turn.option + 1}" if turn.option is not None else "your words"
            lines.append(f"- {what} You chose {choice}: \"{turn.text}\"")
        lines.append("")
    nxt = next_prompt(state, site)
    lines += ["## Next", "", f"- {nxt.text.splitlines()[0]}" if nxt else
              "- All questions are answered. You can still revise any answer.", ""]  # fmt: skip
    return "\n".join(lines)
