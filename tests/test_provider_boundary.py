"""Every provider call goes through ``providers.base.send`` (agent contract section 5).

``send`` checks the owner's ``DataFlowPolicy`` and then calls ``provider.complete``. A
second place that calls ``.complete`` would reach a provider without that check, so the
only ``.complete`` in the code an agent or the CLI runs is the one inside ``send``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from .conftest import REPO

#: The code that runs: the package, the tools and the examples' scripts.
SCANNED = ("src", "tools", "examples")
#: The method every ``ModelProvider`` implements (``providers/base.py``).
METHOD = "complete"
SEND = ("src/house_ai/providers/base.py", "send")


def provider_method_uses(root: Path) -> list[tuple[str, str, int]]:
    """``(file, enclosing function, line)`` of every ``<x>.complete`` read under ``root``.

    An attribute read, not only a call, so ``call = provider.complete; call(request)``
    and ``functools.partial(provider.complete, ...)`` count as well. ``def complete`` (an
    adapter implementing the method) is a definition, not a use.
    """
    uses = []
    for top in SCANNED:
        for path in sorted((root / top).rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            if METHOD not in text:  # an attribute or getattr name is spelled out in full
                continue
            tree = ast.parse(text)
            for func in ast.walk(tree):
                if not isinstance(func, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                name = getattr(func, "name", "<module>")
                for node in _own_nodes(func):
                    if isinstance(node, ast.Attribute) and node.attr == METHOD:
                        uses.append((path.relative_to(root).as_posix(), name, node.lineno))
                    elif (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == "getattr"
                        and any(isinstance(a, ast.Constant) and a.value == METHOD
                                for a in node.args)  # fmt: skip
                    ):
                        uses.append((path.relative_to(root).as_posix(), name, node.lineno))
    return uses


def _own_nodes(scope: ast.AST):
    """The nodes of ``scope`` outside any function nested in it."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


def test_only_send_calls_a_provider():
    uses = provider_method_uses(REPO)
    assert [(f, fn) for f, fn, _ in uses] == [SEND]


def _scratch(tmp_path: Path, extra: str) -> Path:
    """A copy of the providers package plus one module with ``extra`` in it."""
    for top in SCANNED:
        (tmp_path / top).mkdir()
    pkg = tmp_path / "src" / "house_ai" / "providers"
    pkg.mkdir(parents=True)
    for path in (REPO / "src" / "house_ai" / "providers").glob("*.py"):
        (pkg / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "src" / "house_ai" / "shortcut.py").write_text(extra, encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    ("bypass", "where"),
    [
        ("def ask(provider, request):\n    return provider.complete(request)\n", "ask"),
        ("def ask(provider, request):\n    call = provider.complete\n    return call(request)\n",
         "ask"),
        ("def ask(provider, request):\n    return getattr(provider, 'complete')(request)\n",
         "ask"),
        ("class Helper:\n    def ask(self, request):\n        return self.p.complete(request)\n",
         "ask"),
        ("RESULT = PROVIDER.complete(REQUEST)\n", "<module>"),
    ],
)  # fmt: skip
def test_a_direct_provider_call_anywhere_else_is_found(tmp_path, bypass, where):
    """The check bites: a scratch copy of the providers package plus one bypass."""
    uses = provider_method_uses(_scratch(tmp_path, bypass))
    assert [(f, fn) for f, fn, _ in uses] == [SEND, ("src/house_ai/shortcut.py", where)]


def test_an_adapter_defining_complete_is_not_a_call(tmp_path):
    root = _scratch(
        tmp_path,
        "class Adapter:\n    name = 'x'\n\n    def complete(self, request):\n        return 1\n",
    )
    assert [(f, fn) for f, fn, _ in provider_method_uses(root)] == [SEND]
