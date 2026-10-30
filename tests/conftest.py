"""Shared helpers: copies of templates in a workspace and a deterministic model double.

Nothing here calls a provider: the agents answer from doubles built on
:mod:`nodestro_runtime.testing`, and runs go through the same engine, pre-check and Orkexa
agents as in the studio.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import threading
from types import SimpleNamespace
from typing import Any

from nodestro_runtime.schemas import Run, RunIn, Workflow
from nodestro_runtime.testing import AnswerAll, Parsed, sample_instance, text
from nodestro_runtime.workspace import Workspace
import pytest

import nodestro_examples as library


def copy(workspace: Workspace, template_id: str, language: str) -> Workflow:
    """A template as an ordinary saved workflow, its parts saved first (like the gallery's copy)."""
    sensitive = library.structure(template_id).sensitive
    parts: dict[str, tuple[str, int | None]] = {}
    for part_id in library.part_ids(template_id):
        child = workspace.save_workflow(library.build_part(part_id, language, sensitive=sensitive))
        parts[part_id] = (child.id, workspace.current_version(child))
    return workspace.save_workflow(library.link_parts(library.build(template_id, language), parts))


class Scenario(AnswerAll):
    """Answers like :class:`~nodestro_runtime.testing.AnswerAll`, but each agent can be given its answer.

    ``answers`` maps a node id to the values of its structured fields (the rest are filled with
    sample values) or, for a text agent, to its text. With ``empty`` every field the scenario
    does not set is empty (``""``, ``[]``, ``0``, ``False``) and text agents answer nothing, so
    checks that hold for any answer stand out. Agents are recognized by their own system prompt.
    """

    def __init__(self, answers: dict[str, Any] | None = None, *, empty: bool = False) -> None:
        super().__init__()
        self.answers = answers or {}
        self.empty = empty
        self.prompts: dict[str, str] = {}
        self._known = threading.Lock()

    def learn(self, workflow: Workflow) -> None:
        """Remember how to recognize the agents of ``workflow`` (and of the parts it runs)."""
        with self._known:
            for node in workflow.nodes:
                if node.agent is not None:
                    self.prompts[node.agent.system_prompt.split("\n\n")[0]] = node.id

    def _node(self, request: dict[str, Any]) -> str | None:
        system = str(request.get("system", ""))
        return next((node_id for own, node_id in self.prompts.items() if own in system), None)

    def _answer(self, request: dict[str, Any]) -> Any:
        model = request.get("output_format")
        node_id = self._node(request)
        if model is not None and model.__name__ == "_Verdict":
            return super()._answer(request)
        wanted = self.answers.get(node_id) if node_id else None
        if model is None:
            if isinstance(wanted, str):
                with self._lock:
                    self.calls.append({key: value for key, value in request.items() if key != "output_format"})
                return text(wanted)
            return text("") if self.empty and node_id else super()._answer(request)
        with self._lock:
            self.calls.append({key: value for key, value in request.items() if key != "output_format"})
        values = sample_instance(model, request).model_dump()
        if self.empty:
            values = {name: _empty(value) for name, value in values.items()}
        values.update(wanted or {})
        return Parsed(text("{}"), model(**values))


def _empty(value: Any) -> Any:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return 0
    return [] if isinstance(value, list) else ""


class ScenarioClient:
    def __init__(self, scenario: Scenario) -> None:
        self.messages = scenario
        self.beta = SimpleNamespace(messages=scenario)


@pytest.fixture
def make_workspace(tmp_path: Path) -> Iterator[Any]:
    """``make_workspace(scenario)``: a workspace whose agents answer from ``scenario``."""
    opened: list[Workspace] = []

    def make(scenario: Scenario | None = None) -> Workspace:
        double = scenario or Scenario()
        client = ScenarioClient(double)
        found = Workspace(tmp_path / f"data{len(opened)}", client_factory=lambda _provider: client, integrations=[])
        found.fake = double  # type: ignore[attr-defined]
        opened.append(found)
        return found

    yield make
    for item in opened:
        item.close()


async def finish(workspace: Workspace, run: Run, decision: str = "approved", comment: str = "ok") -> Run:
    """Wait for ``run``; every approval it reaches (sub-workflows included) gets ``decision``."""
    done = await workspace.wait(run.id, timeout=60)
    for _ in range(10):
        if done.status != "paused":
            break
        for item in [*workspace.runs.live_runs(), done]:
            for node_id, state in item.nodes.items():
                if state.status == "awaiting_approval":
                    workspace.decide(item.id, node_id, decision, comment)
        done = await workspace.wait(run.id, timeout=60)
    return done


def start_request(workflow: Workflow) -> RunIn:
    """The prepared test input with the form's preset values (required fields always filled)."""
    start = next(node for node in workflow.nodes if node.type == "start")
    assert start.start is not None
    values: dict[str, Any] = {}
    for field in start.start.fields:
        if field.type == "file":
            continue
        if field.default not in (None, "", []):
            values[field.name] = field.default
        elif field.required:
            values[field.name] = field.options[0] if field.options else "Example"
    return RunIn(input=start.start.default_input or "", values=values)
