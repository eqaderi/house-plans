"""The human-only check (``house_ai.cli.human``, ADR 0027), through its own interface.

A scripted terminal stands in for the process's stdin, so these tests need no
monkeypatching. ``tests/test_human_gates.py`` checks that each command uses it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from house_ai.cli import human
from house_ai.cli.human import HumanCheckFailed, NotConfirmed, require_human, require_phrase
from house_ai.domain.provenance import Actor, ActorKind

ALL_ACTIONS = [
    human.APPROVE,
    human.REOPEN,
    human.CONFIRM_SITE,
    human.CONSENT,
    human.REJECT_PROGRAM,
    human.INTERVIEW,
]


@dataclass
class ScriptedTerminal:
    tty: bool = True
    typed: list[str] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)

    def isatty(self) -> bool:
        return self.tty

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.typed.pop(0)


@pytest.mark.parametrize("action", ALL_ACTIONS, ids=lambda a: a.noun)
@pytest.mark.parametrize("who", ["owner", Actor(kind=ActorKind.HUMAN, id="owner")])
def test_no_terminal_refuses_even_a_human(action, who):
    with pytest.raises(HumanCheckFailed, match="needs an interactive terminal") as exc:
        require_human(action, who, ScriptedTerminal(tty=False))
    assert exc.value.exit_code == 2
    assert action.deed in str(exc.value)


@pytest.mark.parametrize("action", ALL_ACTIONS, ids=lambda a: a.noun)
@pytest.mark.parametrize("kind", [ActorKind.AGENT, ActorKind.SYSTEM])
def test_a_non_human_actor_is_refused_at_a_terminal(action, kind):
    with pytest.raises(HumanCheckFailed, match=f"cannot {action.deed}") as exc:
        require_human(action, Actor(kind=kind, id="claude-code"), ScriptedTerminal())
    assert exc.value.exit_code == 2


@pytest.mark.parametrize(
    "name", ["agent:gemini", "claude-code", "codex", "gemini", "system:ci", "Agent:Codex", ""]
)
def test_an_agent_looking_or_empty_name_is_refused(name):
    with pytest.raises(HumanCheckFailed, match="disallowed approver") as exc:
        require_human(human.APPROVE, name, ScriptedTerminal())
    assert exc.value.exit_code == 2


def test_a_human_at_a_terminal_is_returned_as_a_human_actor():
    assert require_human(human.APPROVE, "ershad", ScriptedTerminal()) == Actor(
        kind=ActorKind.HUMAN, id="ershad"
    )
    owner = Actor(kind=ActorKind.HUMAN, id="owner")
    assert require_human(human.REOPEN, owner, ScriptedTerminal()) is owner


def test_only_the_exact_phrase_confirms():
    terminal = ScriptedTerminal(typed=["  approve site site v1 \n"])
    require_phrase(human.APPROVE, "approve site site v1", terminal)
    assert terminal.prompts == ['Type "approve site site v1" to confirm: ']
    for typed in ["approve site site v2", "APPROVE SITE SITE V1", "yes", ""]:
        with pytest.raises(NotConfirmed, match="nothing approved") as exc:
            require_phrase(human.APPROVE, "approve site site v1", ScriptedTerminal(typed=[typed]))
        assert exc.value.exit_code == 1


def test_the_prompt_names_the_verb():
    terminal = ScriptedTerminal(typed=["allow anthropic"])
    require_phrase(human.CONSENT, "allow anthropic", terminal, verb="allow")
    assert terminal.prompts == ['Type "allow anthropic" to allow: ']
