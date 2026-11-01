"""Shared helpers: copies of templates in a workspace and a deterministic model double.

Nothing here calls a provider: the agents answer from doubles built on
:mod:`nodestro_runtime.testing`, and runs go through the same engine, pre-check and Orkexa
agents as in the studio.
"""

from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path
import threading
from types import SimpleNamespace
from typing import Any

from nodestro_runtime.run_views import approvals_of_tree
from nodestro_runtime.schemas import Run, RunIn, Workflow, WorkflowIn
from nodestro_runtime.testing import AnswerAll, Parsed, sample_instance, text, tool_use
from nodestro_runtime.workspace import Workspace
import pytest

import nodestro_examples as library


class Host:
    """Stores a copy in a workspace, like the API's copy route does in its workspace context."""

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def save_workflow(self, workflow: WorkflowIn) -> tuple[str, int | None]:
        saved = self.workspace.save_workflow(workflow)
        return saved.id, self.workspace.current_version(saved)

    def add_knowledge(self, data: bytes, *, name: str, media_type: str, description: str, collection: str) -> str:
        return self.workspace.knowledge.add(
            data, name=name, media_type=media_type, description=description, collection=collection
        ).id


def instantiate(
    workspace: Workspace, template_id: str, language: str, connections: dict[str, dict[str, str]] | None = None
) -> tuple[Workflow, library.Copy]:
    """A template as an ordinary saved workflow with its parts and knowledge files (like the gallery's copy)."""
    made = library.instantiate(template_id, language, Host(workspace), connections=connections)
    saved = workspace.save_workflow(made.workflow)
    learn = getattr(getattr(workspace, "fake", None), "learn_parts", None)
    if learn is not None:
        learn(workspace, made)
    return saved, made


def copy(workspace: Workspace, template_id: str, language: str) -> Workflow:
    return instantiate(workspace, template_id, language)[0]


class Scenario(AnswerAll):
    """Answers like :class:`~nodestro_runtime.testing.AnswerAll`, but each agent can be given its answer.

    ``answers`` maps a node id to the values of its structured fields (the rest are filled with
    sample values) or, for a text agent, to its text. With ``empty`` every field the scenario
    does not set is empty (``""``, ``[]``, ``0``, ``False``) and text agents answer nothing, so
    checks that hold for any answer stand out. Agents are recognized by their own system prompt.
    """

    def __init__(
        self,
        answers: dict[str, Any] | None = None,
        *,
        empty: bool = False,
        decisions: dict[str, list[dict[str, Any]]] | None = None,
        tool_calls: dict[str, list[tuple[str, dict[str, Any]]]] | None = None,
    ) -> None:
        super().__init__()
        self.answers = answers or {}
        self.empty = empty
        self.prompts: dict[str, str] = {}
        #: Orchestrators (node id -> decisions in order, team members named by part id). Without a script an
        #: orchestrator staffs its first teams if it must, gives each team one task and finishes.
        self.decisions = {key: list(value) for key, value in (decisions or {}).items()}
        #: Agents that call tools first (node id -> (tool name or its ``__`` suffix, input) in order).
        self.tool_calls = {key: list(value) for key, value in (tool_calls or {}).items()}
        self.made: dict[str, list[dict[str, Any]]] = {}
        self.orchestrators: dict[str, tuple[str, Any]] = {}
        self.parts: dict[str, str] = {}
        self.tools: dict[str, list[str]] = {}
        self._known = threading.Lock()

    def learn(self, workflow: Workflow | WorkflowIn) -> None:
        """Remember how to recognize the agents and orchestrators of ``workflow``."""
        with self._known:
            for node in workflow.nodes:
                if node.agent is not None:
                    self.prompts[node.agent.system_prompt.split("\n\n")[0]] = node.id
                    self.tools[node.id] = list(node.agent.tools)
                if node.orchestrator is not None:
                    self.orchestrators[node.orchestrator.instructions.split("\n")[0]] = (node.id, node.orchestrator)

    def learn_parts(self, workspace: Workspace, made: library.Copy) -> None:
        """Learn a copy's parts (teams and sub-workflows) and map their part ids to the saved workflows."""
        for part_id, (workflow_id, _version) in made.parts.items():
            self.parts[part_id] = workflow_id
            self.learn(workspace.resolve_workflow(workflow_id, None)[0])
        self.learn(made.workflow)

    def _node(self, request: dict[str, Any]) -> str | None:
        system = str(request.get("system", ""))
        return next((node_id for own, node_id in self.prompts.items() if own in system), None)

    def _orchestrator(self, request: dict[str, Any]) -> tuple[str, Any] | None:
        system = str(request.get("system", ""))
        return next((found for own, found in self.orchestrators.items() if own and own in system), None)

    def _decision(self, node_id: str, config: Any) -> dict[str, Any]:
        script = self.decisions.get(node_id)
        if script is None:
            members = [member.workflow_id for member in config.members]
            first = members[: config.max_team] if config.staffing else members
            script = ([{"action": "staff", "add": first}] if config.staffing else []) + [
                {"action": "delegate", "member": member, "task": "Bitte prüfen."} for member in first
            ]
            script.append({"action": "finish", "answer": "Zusammenfassung der Teams.", "reason": "fertig"})
            self.decisions[node_id] = script
        decision = dict(script.pop(0)) if script else {"action": "finish", "answer": "-", "reason": "-"}
        ids = {**self.parts}

        def resolve(value: Any) -> Any:
            return ids.get(value, value) if isinstance(value, str) else [ids.get(item, item) for item in value]

        for key in ("member", "members", "add", "remove"):
            if key in decision:
                decision[key] = resolve(decision[key])
        values = decision.get("values")
        if isinstance(values, dict):
            if decision["action"] == "parallel":
                values = {ids.get(key, key): value for key, value in values.items()}
            decision["values"] = json.dumps(values)
        self.made.setdefault(node_id, []).append(decision)
        return decision

    def _answer(self, request: dict[str, Any]) -> Any:
        model = request.get("output_format")
        if model is not None and model.__name__ == "Decision":
            found = self._orchestrator(request)
            if found is not None:
                with self._lock:
                    self.calls.append({key: value for key, value in request.items() if key != "output_format"})
                    decision = self._decision(*found)
                fields = {name: None for name, field in model.model_fields.items() if not field.is_required()}
                return Parsed(text("{}"), model(**{**fields, **decision}))
        node_id = self._node(request)
        if model is not None and model.__name__ == "_Verdict":
            return super()._answer(request)
        pending = self.tool_calls.get(node_id or "")
        if pending and request.get("tools"):
            name, payload = pending.pop(0)
            offered = [tool.get("name", "") for tool in request["tools"] if isinstance(tool, dict)]
            full = next((item for item in offered if item == name or item.endswith(f"__{name}")), name)
            with self._lock:
                self.calls.append({key: value for key, value in request.items() if key != "output_format"})
            return tool_use(full, payload, call_id=f"toolu_{node_id}_{len(pending)}")
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
        for pending in approvals_of_tree(workspace.runs, done):
            workspace.decide(pending.run_id, pending.node_id, decision, comment)
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
