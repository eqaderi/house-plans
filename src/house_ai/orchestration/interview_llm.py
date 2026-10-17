"""Optional LLM help for the interview (ADR 0008).

The LLM may only (a) rephrase the question the planner chose and (b) propose
slot values from a free-text answer. Every request goes through
:func:`house_ai.providers.base.send`, so private interview content reaches a
provider only if the owner allowed it. Proposed values are checked against
:mod:`house_ai.interview.slot_types`; anything invalid is dropped, and what is
kept is still an inference until the owner confirms it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, ValidationError

from house_ai.domain.brief import FactValue
from house_ai.domain.provenance import DataClassification
from house_ai.interview.questions import SLOTS
from house_ai.interview.slot_types import InvalidValue, check
from house_ai.providers.base import DataFlowPolicy, ModelProvider, ProviderRequest, send

SYSTEM = (
    "You help an architect interview a homeowner. Read the owner's answer and return only "
    "what the answer clearly states, as JSON matching the schema. Use null when the owner "
    "says they do not know. Never guess a value the answer does not state."
)


class _Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slot: str
    value: str | int | float | bool | list[str] | None


class _Extraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    values: list[_Proposal]


@dataclass
class LlmAssist:
    provider: ModelProvider
    policy: DataFlowPolicy
    classification: DataClassification = DataClassification.PRIVATE

    @property
    def method(self) -> str:
        return f"llm:{self.provider.name}"

    def extract(self, question: str, slots: list[str], answer: str) -> dict[str, FactValue]:
        described = {s: SLOTS[s].label for s in slots}
        request = ProviderRequest(
            system=SYSTEM,
            prompt=json.dumps(
                {"question": question, "answer": answer, "slots": described}, ensure_ascii=False
            ),
            classification=self.classification,
            response_schema=_Extraction.model_json_schema(),
        )
        response = send(self.provider, request, self.policy)
        try:
            parsed = _Extraction.model_validate_json(response.text)
        except ValidationError:
            return {}
        out: dict[str, FactValue] = {}
        for p in parsed.values:
            if p.slot not in slots:
                continue
            try:
                out[p.slot] = check(p.slot, p.value)
            except InvalidValue:
                continue
        return out

    def phrase(self, question: str, context: str) -> str:
        """A friendlier wording of ``question``; the original if the reply is unusable."""
        request = ProviderRequest(
            system="Rephrase the architect's question warmly and briefly. Keep its meaning. "
            "Return only the question.",
            prompt=json.dumps({"question": question, "context": context}, ensure_ascii=False),
            classification=self.classification,
        )
        text = send(self.provider, request, self.policy).text.strip()
        return text if 0 < len(text) <= 600 and "\n\n\n" not in text else question
