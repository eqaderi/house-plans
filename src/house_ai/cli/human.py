"""The one check behind every human-only command (ADR 0027).

A human-only command (gate approval and reopening, site confirmation, provider
consent, program rejection, the owner's interview) runs only in an interactive
terminal, under a human identity, and records a decision only after the human
types its exact phrase. This module is that rule; a command names its
:class:`HumanOnly` action and calls :func:`require_human` and, when it records
something, :func:`require_phrase`.

This stops an agent driving a non-interactive shell from crossing a gate by
accident. It is not a security boundary against a determined local process;
the library refuses non-human actors as well
(:func:`house_ai.domain.provenance.refuse_non_human`).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError

from house_ai.domain.provenance import Actor, ActorKind, ApprovalRequiresHuman, refuse_non_human

from .exit_codes import EXIT_FAIL, EXIT_USAGE


class Terminal(Protocol):
    def isatty(self) -> bool: ...

    def ask(self, prompt: str) -> str: ...


class StdinTerminal:
    """The process's own terminal."""

    def isatty(self) -> bool:
        return sys.stdin.isatty()

    def ask(self, prompt: str) -> str:
        return input(prompt)


class HumanCheckFailed(Exception):
    """A human-only command was refused; ``exit_code`` is what the command returns."""

    exit_code = EXIT_USAGE


class NotConfirmed(HumanCheckFailed):
    exit_code = EXIT_FAIL


@dataclass(frozen=True)
class HumanOnly:
    #: What needs the terminal, as the subject of a sentence ("approval").
    noun: str
    #: What an agent must not do ("approve gates").
    deed: str
    #: What did not happen when the phrase is wrong ("nothing approved").
    undone: str
    #: The option naming the human when it is a bare name ("approver").
    role: str = "actor"


APPROVE = HumanOnly("approval", "approve gates", "nothing approved", role="approver")
REOPEN = HumanOnly("reopening a gate", "reopen gates", "nothing reopened")
CONFIRM_SITE = HumanOnly(
    "site confirmation",
    "confirm units, CRS, datum or boundary",
    "nothing confirmed",
    role="confirmer",
)
CONSENT = HumanOnly("provider consent", "grant provider consent", "not allowed")
REJECT_PROGRAM = HumanOnly("program rejection", "reject the space program", "nothing rejected")
INTERVIEW = HumanOnly("the interview", "answer for the owner", "nothing recorded", role="owner")


def require_human(action: HumanOnly, who: Actor | str, terminal: Terminal | None = None) -> Actor:
    """The human running ``action`` at this terminal, or :class:`HumanCheckFailed`.

    ``who`` is an actor (``--actor``) or a bare human name (``--approver``). The
    terminal is checked first, so nothing about the identity is reported to a
    non-interactive caller.
    """
    terminal = terminal or StdinTerminal()
    if not terminal.isatty():
        raise HumanCheckFailed(
            f"{action.noun} needs an interactive terminal and a typed confirmation from a "
            f"human. Agents must not {action.deed}; ask the human to run this command "
            "themselves."
        )
    if isinstance(who, Actor):
        try:
            refuse_non_human(who, action.deed)
        except ApprovalRequiresHuman as exc:
            raise HumanCheckFailed(f"{exc}.") from exc
        return who
    try:
        return Actor(kind=ActorKind.HUMAN, id=who)
    except ValidationError as exc:
        raise HumanCheckFailed(
            f"disallowed {action.role} {who!r}: {action.role} must be a real human identifier, "
            f"not an agent or tool name (agents must not {action.deed})."
        ) from exc


def require_phrase(
    action: HumanOnly, phrase: str, terminal: Terminal | None = None, *, verb: str = "confirm"
) -> None:
    """Ask the human to type ``phrase`` exactly; :class:`NotConfirmed` otherwise."""
    terminal = terminal or StdinTerminal()
    if terminal.ask(f'Type "{phrase}" to {verb}: ').strip() != phrase:
        raise NotConfirmed(f"confirmation did not match; {action.undone}")
