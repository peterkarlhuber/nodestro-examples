"""Shipped agent templates (NAL-B1): single agents, ready to try, copy and insert into a workflow.

An agent template is the configuration of one agent with a description of what it needs. Like the examples, it
has a language-neutral structure and texts per language:

- ``agents/<id>.json``: the structure (:class:`AgentSpec`): category, revision, what the model must support,
  and the agent itself as a :class:`~nodestro_examples.NodeSpec` (tier, task profile, tools, output fields,
  quality criteria). An agent taken over from an example names it instead (``example``: template and node), so its
  prompt is kept in one place.
- ``texts/<lang>/agents/<id>.json``: the texts (:class:`AgentTexts`): summary, help, example requests and test
  cases, and the agent's own texts (name, description, system prompt, task, field descriptions, criteria) unless
  they come from the example.

:func:`build_agent` turns a template into an ``AgentConfig`` (the same way :func:`~nodestro_examples.build` builds
the agents of an example, including the common rules of the system prompt) and a ``TemplateMeta`` whose
``origin`` names this package's version and the template's revision. Agents name a model tier, never a model;
the caller maps the tiers (:class:`~nodestro_examples.ModelChoice`) and chooses the service connections.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import cache
import json
import re
from typing import Literal

from nodestro_runtime.schemas import LANGUAGES, AgentConfig, TemplateMeta, TemplateRequirements, TemplateTest
from nodestro_runtime.tool_spec import BUILTIN_SPECS
from pydantic import Field, model_validator

from . import (
    _ROOT,
    AGENT_TASKS,
    ModelChoice,
    NodeSpec,
    NodeTexts,
    __version__,
    _build_nodes,
    _context,
    _Strict,
    common,
    language_of,
    structure,
    texts,
    tier_fits,
)

#: The package name in a template's origin (``builtin:<package>@<version>/<id>``).
PACKAGE = "nodestro-examples"
#: The categories of agent templates, in the order the gallery shows them.
AgentCategory = Literal["research", "text", "analysis"]
AGENT_CATEGORIES: tuple[str, ...] = ("research", "text", "analysis")
Capability = Literal["tools", "vision", "structured_output", "long_context"]
_ID = re.compile(r"[a-z0-9-]+")


class ExampleAgent(_Strict):
    """An agent node of an example that a template takes over with its texts."""

    template: str
    node: str


class AgentSpec(_Strict):
    id: str
    number: int = Field(ge=1)
    category: AgentCategory
    #: Counts the changes of this template within one package version; part of its version.
    revision: int = Field(default=1, ge=1)
    #: What the model must support besides plain text.
    capabilities: list[Capability] = Field(default_factory=list)
    #: Whether the agent works without internet access.
    offline_capable: bool = True
    #: Whether its texts handle sensitive data (adds the common caution to the system prompt).
    sensitive: bool = False
    example: ExampleAgent | None = None
    agent: NodeSpec | None = None

    @model_validator(mode="after")
    def _one_source(self) -> AgentSpec:
        if (self.example is None) == (self.agent is None):
            raise ValueError("an agent template has either its own agent or an example's agent")
        if self.agent is not None and self.agent.type != "agent":
            raise ValueError("the agent of a template is an agent node")
        return self


class AgentTexts(_Strict):
    summary: str
    help: str
    examples: list[str] = Field(min_length=1, max_length=20)
    tests: list[TemplateTest] = Field(min_length=1, max_length=50)
    #: The agent's texts; ``None`` when they come from the example.
    agent: NodeTexts | None = None


@cache
def agent_ids() -> tuple[str, ...]:
    """Every agent template id, in the order of their numbers."""
    specs = [agent_structure(path.stem) for path in (_ROOT / "agents").glob("*.json")]
    return tuple(spec.id for spec in sorted(specs, key=lambda spec: spec.number))


@cache
def agent_structure(agent_id: str) -> AgentSpec:
    path = _ROOT / "agents" / f"{agent_id}.json"
    if not _ID.fullmatch(agent_id) or not path.is_file():
        raise KeyError(agent_id)
    return AgentSpec.model_validate(json.loads(path.read_text("utf-8")))


@cache
def agent_texts(agent_id: str, language: str) -> AgentTexts:
    agent_structure(agent_id)  # KeyError for an unknown id
    path = _ROOT / "texts" / language_of(language) / "agents" / f"{agent_id}.json"
    return AgentTexts.model_validate(json.loads(path.read_text("utf-8")))


def _node_and_texts(agent_id: str, language: str) -> tuple[NodeSpec, NodeTexts]:
    spec = agent_structure(agent_id)
    if spec.example is not None:
        source = structure(spec.example.template)
        node = next(item for item in source.nodes if item.id == spec.example.node)
        return node, texts(spec.example.template, language).agents[spec.example.node]
    own = agent_texts(agent_id, language).agent
    assert spec.agent is not None and own is not None  # checked by agent_problems()
    return spec.agent, own


def agent_node(agent_id: str, language: str = "en") -> tuple[NodeSpec, NodeTexts]:
    """The agent of a template as an agent node of an example, with its texts in a language."""
    return _node_and_texts(agent_id, language)


def agent_version(agent_id: str) -> str:
    """The version of a shipped template: the package version and the template's revision (``0.3.0+r1``)."""
    return f"{__version__}+r{agent_structure(agent_id).revision}"


def agent_origin(agent_id: str) -> str:
    return f"builtin:{PACKAGE}@{agent_version(agent_id)}/{agent_id}"


def agent_services(agent_id: str) -> list[str]:
    """The kinds of service connection (``search``) the agent's built-in tools need."""
    node, _ = _node_and_texts(agent_id, "en")
    found = {BUILTIN_SPECS[name].connection_type for name in node.tools if name in BUILTIN_SPECS}
    return sorted(kind for kind in found if kind)


def _capabilities(node: NodeSpec, spec: AgentSpec) -> list[Capability]:
    found: list[Capability] = ["tools"] if node.tools else []
    return found + [item for item in spec.capabilities if item not in found]


def agent_meta(agent_id: str, language: str) -> TemplateMeta:
    spec = agent_structure(agent_id)
    node, _ = _node_and_texts(agent_id, language)
    text = agent_texts(agent_id, language)
    return TemplateMeta(
        category=spec.category,
        summary=text.summary,
        requirements=TemplateRequirements(
            capabilities=_capabilities(node, spec),
            min_tier=node.tier,
            tools=list(node.tools),
            services=agent_services(agent_id),
            offline_capable=spec.offline_capable,
        ),
        origin=agent_origin(agent_id),
        examples=list(text.examples),
        tests=list(text.tests),
        locale=language_of(language),
    )


def build_agent(
    agent_id: str,
    language: str,
    *,
    models: ModelChoice | None = None,
    services: Mapping[str, str] | None = None,
) -> tuple[AgentConfig, TemplateMeta]:
    """The agent of a template in one language with its description (a fresh object every time).

    ``models`` maps the tiers to models (default: :data:`~nodestro_examples.DEFAULT_MODELS`); ``services`` maps a
    kind of service connection to the connection the agent's built-in tools use (none: the workflow check names
    the missing connection, as for examples)."""
    spec = agent_structure(agent_id)
    node, own = _node_and_texts(agent_id, language)
    node = node.model_copy(update={"id": "agent", "variant_of": None})
    context = _context(models, None, None, memory_space=None, services=services)
    [built], _ = _build_nodes(
        [node],
        [],
        start_label="",
        output_label="",
        default_input="",
        agents={"agent": own},
        steps={},
        form={},
        contract={},
        rules=common(language),
        sensitive=spec.sensitive,
        context=context,
    )
    assert built.agent is not None
    agent = built.agent.model_copy(update={"task": node.task})
    return agent, agent_meta(agent_id, language)


def agent_problems() -> list[str]:
    """What is wrong with the shipped agent templates (empty: nothing): structure, texts in every language, the
    example an agent comes from, task profile and tier, tools and output fields."""
    problems: list[str] = []
    numbers: dict[int, str] = {}
    for path in sorted((_ROOT / "agents").glob("*.json")):
        agent_id = path.stem
        try:
            spec = agent_structure(agent_id)
        except Exception as exc:  # reported, not raised
            problems.append(f"{agent_id}: {exc}")
            continue
        if spec.id != agent_id:
            problems.append(f"{agent_id}: id {spec.id!r} differs from the file name")
        if spec.number in numbers:
            problems.append(f"{agent_id}: number {spec.number} is also used by {numbers[spec.number]}")
        numbers[spec.number] = agent_id
        if spec.example is not None:
            try:
                nodes = {item.id: item for item in structure(spec.example.template).nodes}
            except KeyError:
                problems.append(f"{agent_id}: unknown example {spec.example.template!r}")
                continue
            if nodes.get(spec.example.node) is None or nodes[spec.example.node].type != "agent":
                problems.append(f"{agent_id}: {spec.example.template} has no agent {spec.example.node!r}")
                continue
        for language in LANGUAGES:
            try:
                text = agent_texts(agent_id, language)
            except Exception as exc:
                problems.append(f"{agent_id} ({language}): {exc}")
                continue
            if (text.agent is None) != (spec.example is not None):
                problems.append(f"{agent_id} ({language}): agent texts must be given exactly when there is no example")
                continue
            node, own = _node_and_texts(agent_id, language)
            missing = [f.name for f in node.output_fields if f.name not in own.fields]
            missing += [name for name in node.criteria if name not in own.criteria]
            if missing:
                problems.append(f"{agent_id} ({language}): no texts for {', '.join(missing)}")
            names = [test.name for test in text.tests]
            if len(set(names)) != len(names):
                problems.append(f"{agent_id} ({language}): test names repeat")
        node, _ = _node_and_texts(agent_id, "en")
        if node.task not in AGENT_TASKS:
            problems.append(f"{agent_id}: task {node.task!r} is not an agent task profile")
        elif not tier_fits(node.tier, node.task):
            problems.append(f"{agent_id}: tier {node.tier} does not fit task {node.task}")
        unknown = [name for name in node.tools if name not in BUILTIN_SPECS]
        if unknown:
            problems.append(f"{agent_id}: unknown tools {', '.join(unknown)}")
        if node.tools and spec.offline_capable and agent_services(agent_id):
            problems.append(f"{agent_id}: needs a service connection, so it is not offline capable")
    for language in LANGUAGES:
        folder = _ROOT / "texts" / language / "agents"
        extra = sorted(path.stem for path in folder.glob("*.json") if path.stem not in numbers.values())
        if extra:
            problems.append(f"texts ({language}): texts of unknown agent templates {', '.join(extra)}")
    return problems
