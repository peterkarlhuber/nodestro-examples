"""The example library: multi-agent workflow templates in every interface language.

This is the package ``nodestro-examples``. Nodestro reads the library only through the
functions of this module (:func:`summaries`, :func:`detail`, :func:`build`, :func:`instantiate`,
:func:`build_part`, :func:`link_parts`, :func:`structure`, :func:`texts` and :mod:`.samples`); the files are
package data of the installed package, never a path into a source checkout.

A template is data, kept in two kinds of files in this package:

- ``templates/<id>.json`` holds the language-neutral structure: nodes, model tiers, tools,
  connections, output fields, quality criteria, teams, knowledge files and integrations.
- ``texts/<language>/<id>.json`` holds everything a person reads: name, description,
  agent names, system prompts, tasks, the prepared test input and the guide.
  ``texts/<language>/_common.json`` adds the rules every system prompt ends with.

Templates are never changed at runtime and never installed on their own. Copying one
(``POST /api/library/{id}/copy``, :func:`instantiate`) builds an ordinary workflow in the chosen
language; the copy has its own id and is saved, versioned and edited like any other workflow, so
later changes or language switches never touch the template or other copies.

In a task text ``{{node:<id>}}`` names the result of another node; it becomes the
placeholder of that node's name in the respective language (``{{Root cause analyst}}``).

Templates can use every kind of node: decisions (``condition``), approvals, loops, input forms on
the start node (file fields with accepted formats, limits and delivery mode), result files and an
output contract on the result node, knowledge, proposals and memory on agents, sub-workflows and
orchestrators. Every setting is an ordinary workflow setting: a copy needs nothing that exists only
for the gallery.

Format 2 adds, without changing how format 1 templates are read:

- *Parts as teams*: a part (``templates/parts/<id>.json``, texts in ``texts/<language>/parts``) is a small
  workflow that is not an example of its own. A sub-workflow node runs one; an orchestrator node
  (``orchestrator``) delegates to several parts as its team pool. Parts carry capabilities, an output contract,
  an input form and approval steps like any workflow. Copying a template copies its parts first (parts used by
  other parts before those), as workflows of their own, and pins every reference to the copy's first version.
- *Model tiers*: agents name a tier (``fast``, ``standard``, ``strong``) instead of a model; :func:`model_choice`
  maps the tiers to the models of the workspace's provider, so the examples are not bound to one provider.
- *Knowledge files* (``knowledge``): synthetic reference documents a copy stores in the knowledge base and
  gives to agents (search with citations by default).
- *Integrations* (``integrations``): optional MCP tools. A copy is either connected to an MCP server the
  person chose (only approved read-only tools are bound) or works in an explicitly labelled offline mode
  with the example's sample files; the template never pretends a connection that does not exist.
- *Budget and limits* of the copy (``budget_usd``, ``limits``).

Sample files (``samples``) are small synthetic files for the file fields of a template. They
are built on request from the texts of a language with the writers result files use
(:mod:`nodestro_runtime.office`, :mod:`nodestro_runtime.reports`), or read from ``samples/`` for files without
text (an image), so no large binary data lives in the templates (see :mod:`.samples`). Test
cases (``tests``) describe a test series with checks on the result; copying a template can
create it for the copy, with the sample files stored as the copy's input files.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cache
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import re
from typing import Any, Literal, Protocol

from nodestro_runtime.providers import provider_of
from nodestro_runtime.schemas import (
    LANGUAGES,
    MAX_CAPABILITIES,
    AgentConfig,
    ApprovalConfig,
    ConditionConfig,
    ConditionOperator,
    ConditionRule,
    ContentKind,
    Edge,
    EdgeLoop,
    Effort,
    InputField,
    InputFieldType,
    KnowledgeConfig,
    KnowledgeProposalConfig,
    MemoryConfig,
    Node,
    OrchestratorConfig,
    OrchestratorMember,
    OutputConfig,
    OutputField,
    OutputFieldType,
    OutputNodeConfig,
    Position,
    QualityConfig,
    QualityCriterion,
    ReportFormat,
    ResultFileSpec,
    StartConfig,
    SubworkflowConfig,
    WorkflowIn,
    WorkflowLimits,
)
from pydantic import BaseModel, Field, model_validator

try:
    __version__ = version("nodestro-examples")
except PackageNotFoundError:  # pragma: no cover - running from a source checkout
    __version__ = "0.0.0"

#: The version of the template format (``templates/``, ``texts/``). Format 2 adds teams (orchestrators over
#: parts), model tiers, knowledge files, integrations, contracts, budgets and limits; every format 1 template
#: is still read the same way (the new settings are optional and default to format 1's behaviour).
FORMAT_VERSION = 2
#: The package data (templates, texts, sample files) inside the installed package.
_ROOT = Path(__file__).parent
_NODE_REF = re.compile(r"\{\{\s*node:([a-z0-9_]+)\s*\}\}")
FALLBACK_LANGUAGE = "en"

Category = Literal["industry", "business", "customers", "knowledge", "administration", "private"]
#: The categories in the order the gallery shows them.
CATEGORIES: tuple[str, ...] = ("industry", "business", "customers", "knowledge", "administration", "private")
Role = Literal["research", "analysis", "planning", "review", "writing"]
Level = Literal["beginner", "advanced"]
#: ``adaptive``: an orchestrator decides at run time which teams work on the task.
Pattern = Literal["sequential", "parallel", "branching", "adaptive"]
Feature = Literal[
    "tools",
    "structured",
    "judge",
    "review",
    "decision",
    "approval",
    "form",
    "subworkflow",
    "files",
    "documents",
    "proposals",
    "memory",
    "orchestrator",
    "knowledge",
    "integration",
    "loop",
    "budget",
    "contract",
]
#: The prefix of a sub-workflow or team id that names a part of the library (resolved when copying).
PART_PREFIX = "library-part:"
#: The prefix of a knowledge file id that names a knowledge file of the template (resolved when copying).
KNOWLEDGE_PREFIX = "library-knowledge:"

Tier = Literal["fast", "standard", "strong"]
#: The models of the tiers in a workspace whose default model is Anthropic's (the default of Nodestro).
DEFAULT_MODELS: dict[str, str] = {
    "fast": "anthropic:claude-haiku-5-5",
    "standard": "anthropic:claude-sonnet-5-5",
    "strong": "anthropic:claude-opus-5-5",
}
#: The tier of the built-in quality check's judge; the standard tier keeps the examples affordable.
JUDGE_TIER: Tier = "standard"
#: Server tools run on Anthropic's side; with another provider they are left out (see :func:`build`).
_SERVER_TOOL_PROVIDER = "anthropic"


class ModelChoice(BaseModel):
    """The model of each tier in a copy (``provider:model``)."""

    fast: str = DEFAULT_MODELS["fast"]
    standard: str = DEFAULT_MODELS["standard"]
    strong: str = DEFAULT_MODELS["strong"]

    def of(self, tier: Tier) -> str:
        return str(getattr(self, tier))


def model_choice(default_model: str | None = None, assistant_model: str | None = None) -> ModelChoice:
    """The models a copy gets in a workspace with these default models.

    With Anthropic (or no setting) the curated tiers: Haiku for fast extraction and classification, Sonnet for
    everyday agent work, Opus for demanding analysis. With another provider every tier uses the workspace's
    default model, and the strong tier the assistant model when it belongs to the same provider: Nodestro knows
    no tiers of other providers, so it never guesses a model id that might not exist there.
    """
    if not default_model or provider_of(default_model) == "anthropic":
        return ModelChoice()
    provider = provider_of(default_model)
    strong = assistant_model if assistant_model and provider_of(assistant_model) == provider else default_model
    return ModelChoice(fast=default_model, standard=default_model, strong=strong)


# ---- the files ------------------------------------------------------------------


class _Strict(BaseModel):
    model_config = {"extra": "forbid"}


class FieldSpec(_Strict):
    name: str
    type: OutputFieldType = "string"
    required: bool = True


class RuleSpec(_Strict):
    id: str
    field: str = ""
    operator: ConditionOperator = "equals"
    value: Any = None


class ConditionSpec(_Strict):
    #: The node whose result is evaluated.
    source: str | None = None
    mode: Literal["first", "all"] = "first"
    on_invalid: Literal["default", "fail"] = "default"
    rules: list[RuleSpec]


class ApprovalSpec(_Strict):
    on_reject: Literal["branch", "stop"] = "branch"
    require_comment_on_reject: bool = False
    show: list[str] = Field(default_factory=list)


class InputSpec(_Strict):
    """A field of the start node's form; label, description, default and choices are texts.

    The file settings mirror :class:`~nodestro_runtime.schemas.InputField` with the same defaults.
    """

    name: str
    type: InputFieldType = "text"
    required: bool = False
    accept: list[str] = Field(default_factory=list)
    multiple: bool = True
    max_files: int | None = Field(default=None, ge=1, le=100)
    max_size_mb: int | None = Field(default=None, ge=1, le=50)
    delivery: Literal["auto", "inline", "on_demand"] = "auto"


class FileSpec(_Strict):
    """A result file; a plain format (``"pdf"``) is the short form with the default settings."""

    format: ReportFormat
    #: Replace credentials and personal data by placeholders (:class:`~nodestro_runtime.schemas.ResultFileSpec`).
    sanitize: bool = False


class MemorySpec(_Strict):
    """Persistent memory in a named space; the agent must work just as well while the space is empty."""

    space: str


class KnowledgeUse(_Strict):
    """Knowledge files of the template an agent gets (:class:`~nodestro_runtime.schemas.KnowledgeConfig`)."""

    files: list[str] = Field(min_length=1)
    #: ``search``: the search tool over the files' text (with ``citations`` the answer names its sources).
    mode: Literal["context", "on_demand", "search"] = "search"
    citations: bool = True


class McpUse(_Strict):
    """Tools of an integration an agent gets while the copy is connected to it."""

    integration: str
    tools: list[str] = Field(min_length=1)


class OrchestratorSpec(_Strict):
    """An orchestrator over parts of the library (:class:`~nodestro_runtime.schemas.OrchestratorConfig`).

    Name, instructions and task are texts (``steps``); the members are part ids, pinned to the copies' first
    version when the template is copied.
    """

    members: list[str] = Field(min_length=1)
    max_decisions: int = Field(default=8, ge=1, le=50)
    max_per_member: int | None = Field(default=None, ge=1, le=50)
    max_parallel: int = Field(default=1, ge=1, le=5)
    staffing: bool = False
    max_team: int = Field(default=5, ge=1, le=20)
    allow_values: bool = False


class LimitsSpec(_Strict):
    """Execution limits of a copy (:class:`~nodestro_runtime.schemas.WorkflowLimits`)."""

    max_parallel: int | None = Field(default=None, ge=1, le=32)
    max_duration_s: float | None = Field(default=None, gt=0)
    max_steps: int | None = Field(default=None, ge=1)


class NodeSpec(_Strict):
    id: str
    type: Literal["start", "agent", "output", "condition", "approval", "subworkflow", "orchestrator"]
    x: float
    y: float
    role: Role | None = None
    icon: str = "bot"
    #: The model tier (agents and orchestrators); see :func:`model_choice`.
    tier: Tier | None = None
    #: A fixed model instead of a tier (format 1); a tier keeps a copy usable with other providers.
    model: str | None = None
    effort: Effort | None = "medium"
    tools: list[str] = Field(default_factory=list)
    #: Tools that run on the provider's side (Anthropic only; left out with other providers).
    server_tools: list[str] = Field(default_factory=list)
    max_tokens: int = 8000
    output_name: str = "Result"
    output_fields: list[FieldSpec] = Field(default_factory=list)
    criteria: list[str] = Field(default_factory=list)
    max_revisions: int = 1
    condition: ConditionSpec | None = None
    approval: ApprovalSpec | None = None
    #: The part this sub-workflow node runs.
    part: str | None = None
    #: The orchestrator's team pool and limits.
    orchestrator: OrchestratorSpec | None = None
    #: Start node: the input form.
    form: list[InputSpec] = Field(default_factory=list)
    #: Result node: the files it writes.
    files: list[ReportFormat | FileSpec] = Field(default_factory=list)
    #: Result node: the fields the workflow promises (an output contract; descriptions are texts).
    contract: list[FieldSpec] = Field(default_factory=list)
    #: Agents: propose the result for knowledge (what it is); a person always decides.
    proposals: ContentKind | None = None
    #: Agents: persistent memory.
    memory: MemorySpec | None = None
    #: Agents: knowledge files of the template.
    knowledge: KnowledgeUse | None = None
    #: Agents: tools of integrations, bound only while a copy is connected.
    mcp: list[McpUse] = Field(default_factory=list)


#: ``[source, target]``, ``[source, target, branch]`` or ``[source, target, branch, loop]``: a loop
#: (``{"max_iterations": n, "on_exhausted": "fail" | "continue"}``) leads from a branch back to an earlier step.
Connection = tuple[str, str] | tuple[str, str, str] | tuple[str, str, str, EdgeLoop]


def _is_loop(connection: Connection) -> bool:
    return len(connection) == 4


def _graph_problems(nodes: list[NodeSpec], edges: list[Connection]) -> list[str]:
    """What makes a graph of a template or part invalid (empty when it is a valid workflow)."""
    found: list[str] = []
    kinds = {node.id: node.type for node in nodes}
    if len(kinds) != len(nodes):
        found.append("node ids are not unique")
    for kind in ("start", "output"):
        if sum(node.type == kind for node in nodes) != 1:
            found.append(f"exactly one {kind} node is needed")
    for node in nodes:
        if node.type == "condition" and not node.condition:
            found.append(f"decision {node.id} has no rules")
        if node.type == "subworkflow" and not node.part:
            found.append(f"sub-workflow {node.id} names no part")
        if node.type == "orchestrator" and not node.orchestrator:
            found.append(f"orchestrator {node.id} has no teams")
        if node.orchestrator is not None and node.type != "orchestrator":
            found.append(f"{node.id} has teams but is no orchestrator")
        if node.orchestrator is not None and len(set(node.orchestrator.members)) != len(node.orchestrator.members):
            found.append(f"orchestrator {node.id} names a team twice")
        if node.contract and node.type != "output":
            found.append(f"{node.id} has a contract but is no result node")
        if (node.knowledge or node.mcp or node.server_tools) and node.type != "agent":
            found.append(f"{node.id} has agent settings but is no agent")
    if len({edge[:3] for edge in edges}) != len(edges):
        found.append("a connection is listed twice")
    successors: dict[str, list[str]] = {}
    for edge in edges:
        source, target = edge[0], edge[1]
        if source not in kinds or target not in kinds:
            found.append(f"connection {source} -> {target} names an unknown node")
            continue
        if not _is_loop(edge):
            # A loop leads back on purpose; the runtime checks it (check_workflow).
            successors.setdefault(source, []).append(target)
        if len(edge) >= 3:
            condition = next(node.condition for node in nodes if node.id == source)
            handles = {
                "condition": {"default", *(rule.id for rule in condition.rules)} if condition else set(),
                "approval": {"approved", "rejected"},
            }.get(kinds[source], set())
            if edge[2] not in handles:
                found.append(f"connection {source} -> {target} uses the unknown branch {edge[2]!r}")
    # No cycles except loops, and every node lies on a way from the start node to the result node.
    order: list[str] = []
    state: dict[str, int] = {}

    def visit(node_id: str) -> None:
        state[node_id] = 1
        for target in successors.get(node_id, []):
            if state.get(target) == 1:
                found.append(f"the connections form a cycle at {target}")
            elif target not in state:
                visit(target)
        state[node_id] = 2
        order.append(node_id)

    start = next((node.id for node in nodes if node.type == "start"), None)
    if start is not None:
        visit(start)
    unreachable = sorted(set(kinds) - set(state))
    if unreachable:
        found.append(f"not reachable from the start node: {', '.join(unreachable)}")
    output = next((node.id for node in nodes if node.type == "output"), None)
    leads = {output}
    for node_id in order:
        if any(target in leads for target in successors.get(node_id, [])):
            leads.add(node_id)
    dead = sorted(set(state) - leads)
    if dead:
        found.append(f"no way to the result node from: {', '.join(dead)}")
    return found


def _referenced_parts(nodes: list[NodeSpec]) -> list[str]:
    """The parts the nodes run (sub-workflows) or delegate to (orchestrators), in order of appearance."""
    found: list[str] = []
    for node in nodes:
        if node.part:
            found.append(node.part)
        if node.orchestrator is not None:
            found += node.orchestrator.members
    return list(dict.fromkeys(found))


class PartSpec(_Strict):
    """A small workflow used as a sub-workflow or a team by templates; not an example of its own."""

    id: str
    #: What the part can do as a team (tags the orchestrator sees, also used for capability selection).
    capabilities: list[str] = Field(default_factory=list, max_length=MAX_CAPABILITIES)
    budget_usd: float | None = Field(default=None, gt=0)
    limits: LimitsSpec | None = None
    nodes: list[NodeSpec]
    edges: list[Connection]

    @model_validator(mode="after")
    def _valid_graph(self) -> PartSpec:
        problems = _graph_problems(self.nodes, self.edges)
        if any(node.knowledge or node.mcp for node in self.nodes):
            problems.append("parts use no knowledge files or integrations (they belong to the template)")
        if problems:
            raise ValueError("; ".join(problems))
        return self


SampleFormat = Literal["txt", "md", "csv", "json", "xlsx", "docx", "pdf", "zip", "png"]


class SampleSpec(_Strict):
    """A synthetic sample file for a file field of the template."""

    id: str
    format: SampleFormat
    #: The file field the sample is meant for.
    field: str
    #: A language-neutral file in ``samples/`` (e.g. an image); otherwise it is built from the texts.
    file: str | None = None


class KnowledgeSpec(_Strict):
    """A synthetic reference document a copy stores in the knowledge base (name and content are texts)."""

    id: str
    format: Literal["md", "pdf", "docx"] = "md"


class IntegrationSpec(_Strict):
    """An optional connection to an MCP server; the tools are the server's own tool names.

    A copy binds the tools only when the person connects the integration to a server whose tools an
    administrator approved as read-only; otherwise the copy works in the labelled offline mode.
    """

    id: str
    kind: Literal["mcp"] = "mcp"
    tools: list[str] = Field(min_length=1)


class CheckSpec(_Strict):
    """A check of a test case on the run's result (the rules of decision nodes)."""

    #: The node whose result is checked when the result node receives several results.
    node: str | None = None
    field: str = ""
    operator: ConditionOperator = "is_not_empty"
    value: Any = None


class CaseSpec(_Strict):
    """A test case: form values, sample files and checks; name and texts are per language."""

    id: str
    #: ``default``: the prepared test input; ``own``: the case's own text; ``none``: no free text.
    input: Literal["default", "own", "none"] = "default"
    #: Language-neutral form values (numbers, dates, yes/no); texts come from the case's texts.
    values: dict[str, Any] = Field(default_factory=dict)
    #: Sample files, by sample id; each goes into the field of its sample.
    samples: list[str] = Field(default_factory=list)
    checks: list[CheckSpec] = Field(default_factory=list)


class TemplateSpec(_Strict):
    id: str
    number: int
    category: Category
    level: Level
    featured: bool = False
    #: Finance, law, personnel, administration: results must be checked by a person.
    sensitive: bool = False
    #: The example accepts documents (PDF, DOCX, XLSX) as input (also shown for every file field).
    documents: bool = False
    #: The copy's budget in USD (``None``: the workspace's default budget).
    budget_usd: float | None = Field(default=None, gt=0)
    limits: LimitsSpec | None = None
    nodes: list[NodeSpec]
    edges: list[Connection]
    samples: list[SampleSpec] = Field(default_factory=list)
    knowledge: list[KnowledgeSpec] = Field(default_factory=list)
    integrations: list[IntegrationSpec] = Field(default_factory=list)
    tests: list[CaseSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _valid_references(self) -> TemplateSpec:
        problems = _graph_problems(self.nodes, self.edges)
        fields = {field.name: field for node in self.nodes for field in node.form}
        nodes = {node.id for node in self.nodes}
        samples = {sample.id for sample in self.samples}
        knowledge = {item.id for item in self.knowledge}
        integrations = {item.id: set(item.tools) for item in self.integrations}
        for sample in self.samples:
            if sample.field not in fields or fields[sample.field].type != "file":
                problems.append(f"sample {sample.id} names no file field ({sample.field})")
        unique: list[list[str]] = [
            [item.id for item in self.samples],
            [item.id for item in self.tests],
            [item.id for item in self.knowledge],
            [item.id for item in self.integrations],
        ]
        if any(len(set(group)) != len(group) for group in unique):
            problems.append("sample, knowledge, integration or test case ids are not unique")
        used_knowledge: set[str] = set()
        used_integrations: set[str] = set()
        for node in self.nodes:
            if node.knowledge is not None:
                used_knowledge |= set(node.knowledge.files)
                if node.knowledge.citations and node.output_fields:
                    # The runtime cannot attach citations to a structured answer (pre-check error).
                    problems.append(f"{node.id} combines citations with structured output fields")
                problems += [
                    f"{node.id} uses the unknown knowledge file {item}"
                    for item in node.knowledge.files
                    if item not in knowledge
                ]
            for use in node.mcp:
                used_integrations.add(use.integration)
                if use.integration not in integrations:
                    problems.append(f"{node.id} uses the unknown integration {use.integration}")
                    continue
                problems += [
                    f"{node.id} uses {tool}, which the integration {use.integration} does not offer"
                    for tool in use.tools
                    if tool not in integrations[use.integration]
                ]
        problems += [f"knowledge file {item} is not used" for item in sorted(knowledge - used_knowledge)]
        problems += [f"integration {item} is not used" for item in sorted(set(integrations) - used_integrations)]
        for part_id in _referenced_parts(self.nodes):
            try:
                part(part_id)
            except KeyError:
                problems.append(f"the part {part_id} does not exist")
        for case in self.tests:
            name = f"test case {case.id}"
            problems += [f"{name} uses the unknown sample {item}" for item in case.samples if item not in samples]
            problems += [f"{name} sets the unknown field {key}" for key in case.values if key not in fields]
            problems += [
                f"{name} checks the unknown node {check.node}"
                for check in case.checks
                if check.node is not None and check.node not in nodes
            ]
        if problems:
            raise ValueError("; ".join(problems))
        return self


class NodeTexts(_Strict):
    name: str
    description: str
    system: str
    task: str
    fields: dict[str, str] = Field(default_factory=dict)
    criteria: dict[str, str] = Field(default_factory=dict)
    #: Added to the system prompt while the agent's integrations are connected (how to use the tools).
    online: str = ""
    #: Added to the system prompt in offline mode (where the same data comes from instead).
    offline: str = ""


class Guide(BaseModel):
    """What the gallery and the documentation explain about one example."""

    problem: str
    flow: str
    input: str
    result: str
    adapt: str
    #: What is decided automatically, and when and why a person decides.
    control: str
    #: Why this architecture fits the task (and what a simpler or more complex one would cost).
    why: str


class StepTexts(_Strict):
    """Texts of a decision, approval, sub-workflow or orchestrator node."""

    name: str
    #: Approval: what the person checks; orchestrator: how it splits the work.
    instructions: str = ""
    #: Orchestrator: its task (placeholders as in an agent's task).
    task: str = ""
    #: Orchestrator: what it does, shown in the gallery.
    description: str = ""
    #: Decision: the name of each branch (rule id -> label).
    branches: dict[str, str] = Field(default_factory=dict)
    #: Decision: the name of the default branch.
    default: str = ""


class FieldTexts(_Strict):
    label: str
    description: str = ""
    #: The preset value (the sample data of the example).
    default: str = ""
    options: list[str] = Field(default_factory=list)


class SampleTexts(_Strict):
    """A sample file in one language: file name (without extension), what it is and its content.

    The content depends on the format: a Markdown text (``md``, ``txt``, ``docx``, ``pdf``), rows
    with a header row (``csv``), sheets of rows (``xlsx``), any JSON value (``json``) or path ->
    text (``zip``); files from ``samples/`` have no content.
    """

    name: str
    description: str
    content: Any = None


class IntegrationTexts(_Strict):
    """An integration in one language: what it connects and what the person must set up."""

    name: str
    description: str
    #: The steps to connect it (server, approval of the tools as read-only).
    setup: str
    #: Added to the copy's description while it is connected.
    online: str
    #: Added to the copy's description in offline mode.
    offline: str


class CaseTexts(_Strict):
    name: str
    #: The free text of a case with ``input: own``.
    input: str = ""
    #: Text values of the form (labels, names) in this language.
    values: dict[str, str] = Field(default_factory=dict)


class TemplateTexts(_Strict):
    name: str
    field: str
    description: str
    input: str
    guide: Guide
    start: str
    output: str
    agents: dict[str, NodeTexts]
    steps: dict[str, StepTexts] = Field(default_factory=dict)
    form: dict[str, FieldTexts] = Field(default_factory=dict)
    #: The name of the result files (without extension); the workflow name when empty.
    file_name: str = ""
    #: The descriptions of the output contract's fields.
    contract: dict[str, str] = Field(default_factory=dict)
    samples: dict[str, SampleTexts] = Field(default_factory=dict)
    knowledge: dict[str, SampleTexts] = Field(default_factory=dict)
    integrations: dict[str, IntegrationTexts] = Field(default_factory=dict)
    tests: dict[str, CaseTexts] = Field(default_factory=dict)


class PartTexts(_Strict):
    name: str
    description: str
    start: str
    output: str
    agents: dict[str, NodeTexts]
    steps: dict[str, StepTexts] = Field(default_factory=dict)
    form: dict[str, FieldTexts] = Field(default_factory=dict)
    contract: dict[str, str] = Field(default_factory=dict)


class CommonTexts(_Strict):
    language: str
    answer: str
    transparency: str
    caution: str
    #: For agents that receive the files of a form's file fields.
    files: str
    #: The knowledge collection of an example's knowledge files (``{name}``: the example's name).
    collection: str


@cache
def template_ids() -> tuple[str, ...]:
    """Every template id, in the order of their numbers."""
    specs = [structure(path.stem) for path in (_ROOT / "templates").glob("*.json")]
    return tuple(spec.id for spec in sorted(specs, key=lambda spec: spec.number))


@cache
def structure(template_id: str) -> TemplateSpec:
    path = _ROOT / "templates" / f"{template_id}.json"
    if not re.fullmatch(r"[a-z0-9-]+", template_id) or not path.is_file():
        raise KeyError(template_id)
    return TemplateSpec.model_validate(json.loads(path.read_text("utf-8")))


def language_of(language: str | None) -> str:
    return language if language in LANGUAGES else FALLBACK_LANGUAGE


@cache
def texts(template_id: str, language: str) -> TemplateTexts:
    path = _ROOT / "texts" / language_of(language) / f"{template_id}.json"
    return TemplateTexts.model_validate(json.loads(path.read_text("utf-8")))


@cache
def common(language: str) -> CommonTexts:
    path = _ROOT / "texts" / language_of(language) / "_common.json"
    return CommonTexts.model_validate(json.loads(path.read_text("utf-8")))


# ---- building workflows -----------------------------------------------------------


def _system_prompt(own: str, rules: CommonTexts, *, sensitive: bool, files: bool = False) -> str:
    parts = [
        own.strip(),
        *([rules.files] if files else []),
        rules.transparency,
        *([rules.caution] if sensitive else []),
        rules.answer,
    ]
    return "\n\n".join(parts)


def _fed_by_start(spec_nodes: list[NodeSpec], edges: list[Connection]) -> set[str]:
    """The agents whose input comes from the start node (directly or through a decision or approval)."""
    kinds = {node.id: node.type for node in spec_nodes}
    incoming: dict[str, list[str]] = {}
    for connection in edges:
        if not _is_loop(connection):
            incoming.setdefault(connection[1], []).append(connection[0])

    def reaches_start(node_id: str, seen: set[str]) -> bool:
        for source in incoming.get(node_id, []):
            if source in seen:
                continue
            seen.add(source)
            if kinds[source] == "start":
                return True
            if kinds[source] in ("condition", "approval") and reaches_start(source, seen):
                return True
        return False

    return {node.id for node in spec_nodes if node.type == "agent" and reaches_start(node.id, set())}


def _value(raw: str, kind: InputFieldType) -> Any:
    if raw == "":
        return None
    if kind == "number":
        return float(raw) if "." in raw else int(raw)
    if kind == "boolean":
        return raw == "true"
    return raw


def _limits(spec: LimitsSpec | None) -> WorkflowLimits:
    return WorkflowLimits(**spec.model_dump()) if spec is not None else WorkflowLimits()


@dataclass
class _Context:
    """How one build resolves models, connections and knowledge files."""

    models: ModelChoice
    #: integration id -> server tool name -> the agent tool name (``mcp__<slug>__<tool>``).
    connections: Mapping[str, Mapping[str, str]]
    #: knowledge id -> knowledge file id.
    knowledge: Mapping[str, str]

    def model(self, node: NodeSpec) -> str:
        return node.model if node.model else self.models.of(node.tier or "standard")


def _build_nodes(
    spec_nodes: list[NodeSpec],
    edges: list[Connection],
    *,
    start_label: str,
    output_label: str,
    default_input: str,
    agents: dict[str, NodeTexts],
    steps: dict[str, StepTexts],
    form: dict[str, FieldTexts],
    contract: dict[str, str],
    rules: CommonTexts,
    sensitive: bool,
    context: _Context,
    file_name: str = "",
) -> tuple[list[Node], list[Edge]]:
    names = {node_id: agent.name for node_id, agent in agents.items()}
    names.update({node_id: step.name for node_id, step in steps.items()})
    # Agents fed by the start node receive the files of its file fields: tell them how to treat them.
    with_files = (
        _fed_by_start(spec_nodes, edges)
        if any(field.type == "file" for item in spec_nodes for field in item.form)
        else set()
    )

    def task(template: str) -> str:
        return _NODE_REF.sub(lambda match: "{{" + names[match.group(1)] + "}}", template)

    nodes: list[Node] = []
    for item in spec_nodes:
        position = Position(x=item.x, y=item.y)
        if item.type == "start":
            fields = [
                InputField(
                    name=field.name,
                    label=form[field.name].label,
                    type=field.type,
                    description=form[field.name].description,
                    required=field.required,
                    default=_value(form[field.name].default, field.type),
                    options=list(form[field.name].options),
                    accept=list(field.accept),
                    multiple=field.multiple,
                    max_files=field.max_files,
                    max_size_mb=field.max_size_mb,
                    delivery=field.delivery,
                )
                for field in item.form
            ]
            config = StartConfig(default_input=default_input, fields=fields)
            nodes.append(Node(id=item.id, type="start", label=start_label, position=position, start=config))
            continue
        if item.type == "output":
            specs = [FileSpec(format=entry) if isinstance(entry, str) else entry for entry in item.files]
            files = [ResultFileSpec(format=spec.format, name=file_name, sanitize=spec.sanitize) for spec in specs]
            promised = [
                OutputField(name=f.name, type=f.type, required=f.required, description=contract[f.name])
                for f in item.contract
            ]
            output_config = OutputNodeConfig(files=files, contract=promised) if files or promised else None
            nodes.append(Node(id=item.id, type="output", label=output_label, position=position, output=output_config))
            continue
        if item.type == "condition":
            assert item.condition is not None
            step = steps[item.id]
            condition = ConditionConfig(
                source=item.condition.source,
                mode=item.condition.mode,
                on_invalid=item.condition.on_invalid,
                default_label=step.default,
                rules=[
                    ConditionRule(
                        id=rule.id,
                        label=step.branches[rule.id],
                        field=rule.field,
                        operator=rule.operator,
                        value=rule.value,
                    )
                    for rule in item.condition.rules
                ],
            )
            nodes.append(Node(id=item.id, type="condition", label=step.name, position=position, condition=condition))
            continue
        if item.type == "approval":
            spec = item.approval or ApprovalSpec()
            approval = ApprovalConfig(
                instructions=steps[item.id].instructions,
                show=list(spec.show),
                on_reject=spec.on_reject,
                require_comment_on_reject=spec.require_comment_on_reject,
            )
            nodes.append(
                Node(id=item.id, type="approval", label=steps[item.id].name, position=position, approval=approval)
            )
            continue
        if item.type == "subworkflow":
            config_sub = SubworkflowConfig(workflow_id=f"{PART_PREFIX}{item.part}", version=1)
            nodes.append(
                Node(
                    id=item.id, type="subworkflow", label=steps[item.id].name, position=position, subworkflow=config_sub
                )
            )
            continue
        if item.type == "orchestrator":
            assert item.orchestrator is not None
            step = steps[item.id]
            team = item.orchestrator
            orchestrator = OrchestratorConfig(
                members=[
                    OrchestratorMember(workflow_id=f"{PART_PREFIX}{member}", version=1) for member in team.members
                ],
                task_template=task(step.task),
                instructions=step.instructions,
                model=context.model(item),
                max_decisions=team.max_decisions,
                max_per_member=team.max_per_member,
                max_parallel=team.max_parallel,
                staffing=team.staffing,
                max_team=team.max_team,
                allow_values=team.allow_values,
            )
            nodes.append(
                Node(id=item.id, type="orchestrator", label=step.name, position=position, orchestrator=orchestrator)
            )
            continue
        own = agents[item.id]
        output = OutputConfig()
        if item.output_fields:
            output = OutputConfig(
                mode="structured",
                name=item.output_name,
                fields=[
                    OutputField(name=f.name, type=f.type, required=f.required, description=own.fields[f.name])
                    for f in item.output_fields
                ],
            )
        quality = QualityConfig()
        if item.criteria:
            quality = QualityConfig(
                enabled=True,
                criteria=[QualityCriterion(name=name, description=own.criteria[name]) for name in item.criteria],
                max_revisions=item.max_revisions,
                judge_model=context.models.of(JUDGE_TIER),
            )
        model = context.model(item)
        tools = list(item.tools)
        connected = bool(item.mcp) and all(use.integration in context.connections for use in item.mcp)
        if connected:
            tools += [context.connections[use.integration][tool] for use in item.mcp for tool in use.tools]
        system = own.system
        if item.mcp:
            extra = own.online if connected else own.offline
            system = f"{system.strip()}\n\n{extra.strip()}" if extra.strip() else system
        knowledge = KnowledgeConfig()
        if item.knowledge is not None:
            knowledge = KnowledgeConfig(
                file_ids=[context.knowledge.get(ref, f"{KNOWLEDGE_PREFIX}{ref}") for ref in item.knowledge.files],
                mode=item.knowledge.mode,
                citations=item.knowledge.citations,
            )
        server_tools = list(item.server_tools) if provider_of(model) == _SERVER_TOOL_PROVIDER else []
        nodes.append(
            Node(
                id=item.id,
                type="agent",
                label=own.name,
                position=position,
                agent=AgentConfig(
                    name=own.name,
                    description=own.description,
                    icon=item.icon,
                    model=model,
                    system_prompt=_system_prompt(system, rules, sensitive=sensitive, files=item.id in with_files),
                    task_template=task(own.task),
                    tools=tools,
                    server_tools=server_tools,
                    effort=item.effort,
                    max_tokens=item.max_tokens,
                    output=output,
                    quality=quality,
                    knowledge=knowledge,
                    knowledge_proposals=KnowledgeProposalConfig(
                        enabled=item.proposals is not None, content_kind=item.proposals or "generated"
                    ),
                    memory=MemoryConfig(mode="persistent", space=item.memory.space) if item.memory else MemoryConfig(),
                ),
            )
        )
    built_edges = []
    for connection in edges:
        source, target = connection[0], connection[1]
        handle = connection[2] if len(connection) >= 3 else None
        loop = connection[3] if len(connection) == 4 else None
        edge_id = f"e-{source}-{target}" + (f"-{handle}" if handle else "")
        built_edges.append(Edge(id=edge_id, source=source, target=target, source_handle=handle, loop=loop))
    return nodes, built_edges


def _context(
    models: ModelChoice | None,
    connections: Mapping[str, Mapping[str, str]] | None,
    knowledge: Mapping[str, str] | None,
) -> _Context:
    return _Context(models=models or ModelChoice(), connections=connections or {}, knowledge=knowledge or {})


def build(
    template_id: str,
    language: str,
    *,
    models: ModelChoice | None = None,
    connections: Mapping[str, Mapping[str, str]] | None = None,
    knowledge: Mapping[str, str] | None = None,
) -> WorkflowIn:
    """The workflow a template describes, in one language (a fresh object every time).

    ``models`` maps the tiers to models (default: :data:`DEFAULT_MODELS`). ``connections`` names, per connected
    integration, the agent tool name of each of its server tools (:func:`connect`); integrations without one run
    in offline mode. ``knowledge`` maps the template's knowledge files to stored knowledge file ids. Until a copy
    resolves them, sub-workflow and team references read ``library-part:<id>`` and knowledge files
    ``library-knowledge:<id>``.
    """
    spec = structure(template_id)
    text = texts(template_id, language)
    context = _context(models, connections, knowledge)
    nodes, edges = _build_nodes(
        spec.nodes,
        spec.edges,
        start_label=text.start,
        output_label=text.output,
        default_input=text.input,
        agents=text.agents,
        steps=text.steps,
        form=text.form,
        contract=text.contract,
        rules=common(language),
        sensitive=spec.sensitive,
        context=context,
        file_name=text.file_name,
    )
    description = text.description
    for integration in spec.integrations:
        note = text.integrations[integration.id]
        description += "\n\n" + (note.online if integration.id in context.connections else note.offline)
    return WorkflowIn(
        name=text.name,
        description=description,
        nodes=nodes,
        edges=edges,
        budget_usd=spec.budget_usd,
        limits=_limits(spec.limits),
    )


@cache
def part(part_id: str) -> PartSpec:
    path = _ROOT / "templates" / "parts" / f"{part_id}.json"
    if not re.fullmatch(r"[a-z0-9-]+", part_id) or not path.is_file():
        raise KeyError(part_id)
    return PartSpec.model_validate(json.loads(path.read_text("utf-8")))


@cache
def part_texts(part_id: str, language: str) -> PartTexts:
    path = _ROOT / "texts" / language_of(language) / "parts" / f"{part_id}.json"
    return PartTexts.model_validate(json.loads(path.read_text("utf-8")))


def part_ids(template_id: str) -> list[str]:
    """Every part a template needs, the parts used by other parts first (the order a copy saves them in)."""
    ordered: list[str] = []
    visiting: set[str] = set()

    def add(part_id: str) -> None:
        if part_id in ordered:
            return
        if part_id in visiting:
            raise ValueError(f"the parts call each other in a cycle at {part_id}")
        visiting.add(part_id)
        for inner in _referenced_parts(part(part_id).nodes):
            add(inner)
        visiting.discard(part_id)
        ordered.append(part_id)

    for part_id in _referenced_parts(structure(template_id).nodes):
        add(part_id)
    return ordered


def build_part(
    part_id: str,
    language: str,
    *,
    sensitive: bool = False,
    models: ModelChoice | None = None,
) -> WorkflowIn:
    spec = part(part_id)
    text = part_texts(part_id, language)
    nodes, edges = _build_nodes(
        spec.nodes,
        spec.edges,
        start_label=text.start,
        output_label=text.output,
        default_input="",
        agents=text.agents,
        steps=text.steps,
        form=text.form,
        contract=text.contract,
        rules=common(language),
        sensitive=sensitive,
        context=_context(models, None, None),
    )
    return WorkflowIn(
        name=text.name,
        description=text.description,
        nodes=nodes,
        edges=edges,
        capabilities=list(spec.capabilities),
        budget_usd=spec.budget_usd,
        limits=_limits(spec.limits),
    )


def link_parts(workflow: WorkflowIn, copies: Mapping[str, tuple[str, int | None]]) -> WorkflowIn:
    """Point sub-workflow nodes and orchestrator teams at the copies of their parts (part id -> id, version)."""
    for node in workflow.nodes:
        if node.subworkflow is not None and node.subworkflow.workflow_id.startswith(PART_PREFIX):
            workflow_id, version = copies[node.subworkflow.workflow_id[len(PART_PREFIX) :]]
            node.subworkflow.workflow_id = workflow_id
            node.subworkflow.version = version
        if node.orchestrator is not None:
            for member in node.orchestrator.members:
                if member.workflow_id.startswith(PART_PREFIX):
                    workflow_id, version = copies[member.workflow_id[len(PART_PREFIX) :]]
                    member.workflow_id = workflow_id
                    member.version = version
    return workflow


# ---- integrations and copies -------------------------------------------------------


class IntegrationProblem(Exception):
    """The chosen MCP server does not offer an integration's tools as approved read-only tools."""

    def __init__(self, integration: str, missing: list[str], not_read_only: list[str]) -> None:
        self.integration = integration
        self.missing = missing
        self.not_read_only = not_read_only
        parts = []
        if missing:
            parts.append(f"missing or not approved: {', '.join(missing)}")
        if not_read_only:
            parts.append(f"not approved as read-only: {', '.join(not_read_only)}")
        super().__init__(f"the server cannot serve the integration {integration} ({'; '.join(parts)})")


@dataclass(frozen=True)
class ServerTool:
    """A tool of an MCP server as the copy sees it: the name agents use, approval and classification."""

    agent_name: str
    approved: bool
    access: str


def connect(template_id: str, integration_id: str, offered: Mapping[str, ServerTool]) -> dict[str, str]:
    """The agent tool names for an integration on a server that offers ``offered`` (server tool name -> tool).

    Every tool of the integration must be approved by an administrator and classified as read-only: the
    examples never get tools that change data, whatever the per-call approval settings are. Raises
    :class:`IntegrationProblem` (nothing is copied) when the server cannot serve the integration.
    """
    spec = next((item for item in structure(template_id).integrations if item.id == integration_id), None)
    if spec is None:
        raise KeyError(integration_id)
    missing = [tool for tool in spec.tools if tool not in offered or not offered[tool].approved]
    not_read_only = [
        tool for tool in spec.tools if tool in offered and offered[tool].approved and offered[tool].access != "read"
    ]
    if missing or not_read_only:
        raise IntegrationProblem(integration_id, missing, not_read_only)
    return {tool: offered[tool].agent_name for tool in spec.tools}


class CopyHost(Protocol):
    """Where a copy is stored: the API's workspace context, or a :class:`~nodestro_runtime.workspace.Workspace`."""

    def save_workflow(self, workflow: WorkflowIn) -> tuple[str, int | None]:
        """Save a new workflow; its id and version."""
        ...

    def add_knowledge(self, data: bytes, *, name: str, media_type: str, description: str, collection: str) -> str:
        """Store a knowledge file; its id."""
        ...


@dataclass
class Copy:
    """A template instantiated for one workspace: the workflow (not saved yet) and what was created for it."""

    workflow: WorkflowIn
    #: part id -> (workflow id, version) of the saved parts.
    parts: dict[str, tuple[str, int | None]] = field(default_factory=dict)
    #: knowledge id -> knowledge file id.
    knowledge: dict[str, str] = field(default_factory=dict)
    #: The integrations that are connected; every other integration runs in offline mode.
    connected: list[str] = field(default_factory=list)
    offline: list[str] = field(default_factory=list)


def instantiate(
    template_id: str,
    language: str,
    host: CopyHost,
    *,
    models: ModelChoice | None = None,
    connections: Mapping[str, Mapping[str, str]] | None = None,
) -> Copy:
    """Everything a copy of a template needs, created through ``host``; the copy itself is returned unsaved.

    Knowledge files are stored (identical content keeps one file), the parts are saved as workflows of their
    own (parts used by other parts first) and every reference is pinned to the saved version. ``connections``
    comes from :func:`connect`; integrations without a connection run in offline mode.
    """
    from .samples import render_knowledge

    spec = structure(template_id)
    text = texts(template_id, language)
    connections = dict(connections or {})
    unknown = set(connections) - {item.id for item in spec.integrations}
    if unknown:
        raise KeyError(", ".join(sorted(unknown)))
    stored: dict[str, str] = {}
    collection = common(language).collection.replace("{name}", text.name)
    for item in spec.knowledge:
        name, media_type, data = render_knowledge(template_id, item.id, language)
        stored[item.id] = host.add_knowledge(
            data,
            name=name,
            media_type=media_type,
            description=text.knowledge[item.id].description,
            collection=collection,
        )
    copies: dict[str, tuple[str, int | None]] = {}
    for part_id in part_ids(template_id):
        built = build_part(part_id, language, sensitive=spec.sensitive, models=models)
        copies[part_id] = host.save_workflow(link_parts(built, copies))
    workflow = build(template_id, language, models=models, connections=connections, knowledge=stored)
    return Copy(
        workflow=link_parts(workflow, copies),
        parts=copies,
        knowledge=stored,
        connected=[item.id for item in spec.integrations if item.id in connections],
        offline=[item.id for item in spec.integrations if item.id not in connections],
    )


# ---- what the API returns ---------------------------------------------------------


class TemplateAgent(BaseModel):
    node_id: str
    name: str
    description: str
    role: Role | None
    model: str
    tools: list[str]
    structured: bool
    judge: bool
    #: Names of the nodes whose results this agent receives ("start" for the input).
    receives: list[str]
    #: ``orchestrator``: an AI model that delegates to teams instead of working itself.
    kind: Literal["agent", "orchestrator"] = "agent"
    #: The names of the knowledge files the agent searches.
    knowledge: list[str] = Field(default_factory=list)
    #: The integrations whose tools the agent gets while connected.
    integrations: list[str] = Field(default_factory=list)
    memory: bool = False


class TemplateTeam(BaseModel):
    """A team an orchestrator of the template can delegate to (a part, copied as a workflow of its own)."""

    part_id: str
    name: str
    description: str
    capabilities: list[str]
    agents: list[TemplateAgent]
    #: The team stops for a person's approval; the orchestrator waits for the decision.
    approval: bool
    #: The fields the team promises to deliver (its output contract).
    contract: list[str]
    #: The start form fields an orchestrator may fill when it delegates.
    parameters: list[str]


class TemplateIntegration(BaseModel):
    id: str
    kind: str
    name: str
    description: str
    setup: str
    #: The server's tool names the integration needs (approved, read-only).
    tools: list[str]
    #: What the copy says in offline mode.
    offline: str


class TemplateKnowledge(BaseModel):
    id: str
    name: str
    description: str


class TemplateSummary(BaseModel):
    id: str
    number: int
    language: str
    category: Category
    field: str
    name: str
    description: str
    level: Level
    pattern: Pattern
    featured: bool
    sensitive: bool
    agents: int
    features: list[Feature]
    tools: list[str]
    #: Teams the orchestrators delegate to (0 without orchestrator).
    teams: int = 0


class SampleInfo(BaseModel):
    """A sample file as the gallery lists it (download: ``/api/library/{id}/samples/{sample}``)."""

    id: str
    field: str
    field_label: str
    format: SampleFormat
    file_name: str
    description: str


class TemplateDetail(TemplateSummary):
    guide: Guide
    agent_details: list[TemplateAgent]
    input: str
    samples: list[SampleInfo] = Field(default_factory=list)
    #: The names of the test cases a copy can take over as a test series.
    tests: list[str] = Field(default_factory=list)
    team_details: list[TemplateTeam] = Field(default_factory=list)
    integrations: list[TemplateIntegration] = Field(default_factory=list)
    knowledge: list[TemplateKnowledge] = Field(default_factory=list)
    budget_usd: float | None = None
    #: The workflow exactly as a copy would get it (offline, with Nodestro's default models); shown read-only.
    workflow: WorkflowIn


def _successors(edges: list[Connection]) -> dict[str, list[str]]:
    successors: dict[str, list[str]] = {}
    for edge in edges:
        if not _is_loop(edge):
            successors.setdefault(edge[0], []).append(edge[1])
    return successors


def _pattern(spec: TemplateSpec) -> Pattern:
    """Adaptive with an orchestrator; branching with a decision; parallel when two agents can work at once."""
    if any(node.type == "orchestrator" for node in spec.nodes):
        return "adaptive"
    if any(node.type == "condition" for node in spec.nodes):
        return "branching"
    agents = [node.id for node in spec.nodes if node.type == "agent"]
    successors = _successors(spec.edges)

    def reachable(start: str) -> set[str]:
        seen: set[str] = set()
        todo = [start]
        while todo:
            for target in successors.get(todo.pop(), []):
                if target not in seen:
                    seen.add(target)
                    todo.append(target)
        return seen

    after = {agent: reachable(agent) for agent in agents}
    independent = any(b not in after[a] and a not in after[b] for i, a in enumerate(agents) for b in agents[i + 1 :])
    return "parallel" if independent else "sequential"


def _all_nodes(spec: TemplateSpec) -> list[NodeSpec]:
    """The template's nodes and those of every part it uses."""
    return [*spec.nodes, *(node for part_id in part_ids(spec.id) for node in part(part_id).nodes)]


def _features(spec: TemplateSpec) -> list[Feature]:
    nodes = _all_nodes(spec)
    agents = [node for node in nodes if node.type == "agent"]
    found: list[Feature] = []
    if any(node.tools for node in agents) or spec.integrations:
        found.append("tools")
    if any(node.output_fields for node in agents):
        found.append("structured")
    if any(node.criteria for node in agents):
        found.append("judge")
    if any(node.role == "review" for node in agents):
        found.append("review")
    types = {node.type for node in nodes}
    if "condition" in types:
        found.append("decision")
    if "approval" in types:
        found.append("approval")
    if any(node.form for node in spec.nodes):
        found.append("form")
    if "subworkflow" in types:
        found.append("subworkflow")
    if any(node.files for node in spec.nodes):
        found.append("files")
    if spec.documents or any(field.type == "file" for node in spec.nodes for field in node.form):
        found.append("documents")
    if any(node.proposals for node in agents):
        found.append("proposals")
    if any(node.memory for node in agents):
        found.append("memory")
    if "orchestrator" in types:
        found.append("orchestrator")
    if spec.knowledge:
        found.append("knowledge")
    if spec.integrations:
        found.append("integration")
    if any(_is_loop(edge) for edge in spec.edges) or any(
        _is_loop(edge) for part_id in part_ids(spec.id) for edge in part(part_id).edges
    ):
        found.append("loop")
    if spec.budget_usd is not None or spec.limits is not None:
        found.append("budget")
    if any(node.contract for node in nodes):
        found.append("contract")
    return found


def summary(template_id: str, language: str) -> TemplateSummary:
    spec = structure(template_id)
    text = texts(template_id, language)
    agents = [node for node in spec.nodes if node.type == "agent"]
    tools = {tool for node in _all_nodes(spec) if node.type == "agent" for tool in node.tools}
    teams = {member for node in spec.nodes if node.orchestrator for member in node.orchestrator.members}
    return TemplateSummary(
        id=spec.id,
        number=spec.number,
        language=language_of(language),
        category=spec.category,
        field=text.field,
        name=text.name,
        description=text.description,
        level=spec.level,
        pattern=_pattern(spec),
        featured=spec.featured,
        sensitive=spec.sensitive,
        agents=len(agents) + sum(node.type == "orchestrator" for node in spec.nodes),
        features=_features(spec),
        tools=sorted(tools),
        teams=len(teams),
    )


def summaries(language: str) -> list[TemplateSummary]:
    return [summary(template_id, language) for template_id in template_ids()]


def _agents_of(
    nodes: list[NodeSpec],
    edges: list[Connection],
    workflow: WorkflowIn,
    agents: dict[str, NodeTexts],
    steps: dict[str, StepTexts],
    knowledge: dict[str, SampleTexts],
    integrations: dict[str, IntegrationTexts],
) -> list[TemplateAgent]:
    labels = {node.id: node.label for node in workflow.nodes}
    models = {node.id: node.agent.model for node in workflow.nodes if node.agent is not None}
    models.update({node.id: node.orchestrator.model for node in workflow.nodes if node.orchestrator is not None})
    found = []
    for item in nodes:
        receives = [labels[edge[0]] for edge in edges if edge[1] == item.id and not _is_loop(edge)]
        if item.type == "orchestrator":
            step = steps[item.id]
            found.append(
                TemplateAgent(
                    node_id=item.id,
                    name=step.name,
                    description=step.description,
                    role=item.role,
                    model=models[item.id],
                    tools=[],
                    structured=False,
                    judge=False,
                    receives=receives,
                    kind="orchestrator",
                )
            )
            continue
        if item.type != "agent":
            continue
        own = agents[item.id]
        found.append(
            TemplateAgent(
                node_id=item.id,
                name=own.name,
                description=own.description,
                role=item.role,
                model=models[item.id],
                tools=list(item.tools),
                structured=bool(item.output_fields),
                judge=bool(item.criteria),
                receives=receives,
                knowledge=[knowledge[ref].name for ref in item.knowledge.files] if item.knowledge else [],
                integrations=[integrations[use.integration].name for use in item.mcp],
                memory=item.memory is not None,
            )
        )
    return found


def detail(template_id: str, language: str) -> TemplateDetail:
    spec = structure(template_id)
    text = texts(template_id, language)
    workflow = build(template_id, language)
    agents = _agents_of(spec.nodes, spec.edges, workflow, text.agents, text.steps, text.knowledge, text.integrations)
    teams = []
    for part_id in dict.fromkeys(
        member for node in spec.nodes if node.orchestrator for member in node.orchestrator.members
    ):
        part_spec = part(part_id)
        own = part_texts(part_id, language)
        built = build_part(part_id, language, sensitive=spec.sensitive)
        output = next(node for node in part_spec.nodes if node.type == "output")
        teams.append(
            TemplateTeam(
                part_id=part_id,
                name=own.name,
                description=own.description,
                capabilities=list(part_spec.capabilities),
                agents=_agents_of(part_spec.nodes, part_spec.edges, built, own.agents, own.steps, {}, {}),
                approval=any(node.type == "approval" for node in part_spec.nodes),
                contract=[item.name for item in output.contract],
                parameters=[own.form[field.name].label for node in part_spec.nodes for field in node.form],
            )
        )
    from .samples import file_name

    return TemplateDetail(
        **summary(template_id, language).model_dump(),
        guide=text.guide,
        agent_details=agents,
        input=text.input,
        samples=[
            SampleInfo(
                id=sample.id,
                field=sample.field,
                field_label=text.form[sample.field].label,
                format=sample.format,
                file_name=file_name(template_id, sample.id, language),
                description=text.samples[sample.id].description,
            )
            for sample in spec.samples
        ],
        tests=[text.tests[case.id].name for case in spec.tests],
        team_details=teams,
        integrations=[
            TemplateIntegration(
                id=item.id,
                kind=item.kind,
                name=text.integrations[item.id].name,
                description=text.integrations[item.id].description,
                setup=text.integrations[item.id].setup,
                tools=list(item.tools),
                offline=text.integrations[item.id].offline,
            )
            for item in spec.integrations
        ],
        knowledge=[
            TemplateKnowledge(
                id=item.id, name=text.knowledge[item.id].name, description=text.knowledge[item.id].description
            )
            for item in spec.knowledge
        ],
        budget_usd=spec.budget_usd,
        workflow=workflow,
    )


def search_fields(template_id: str, language: str) -> list[tuple[str, float]]:
    """The texts the global search looks at, with their weights."""
    text = texts(template_id, language)
    agents = " ".join(f"{agent.name} {agent.description}" for agent in text.agents.values())
    return [(text.name, 4), (text.field, 3), (text.description, 1.5), (agents, 1)]


def raw_texts(template_id: str, language: str) -> dict[str, Any]:
    """The text file as stored (used by tests to compare languages)."""
    path = _ROOT / "texts" / language_of(language) / f"{template_id}.json"
    return json.loads(path.read_text("utf-8"))  # type: ignore[no-any-return]


def raw_part_texts(part_id: str, language: str) -> dict[str, Any]:
    """A part's text file as stored (used by tests to compare languages)."""
    path = _ROOT / "texts" / language_of(language) / "parts" / f"{part_id}.json"
    return json.loads(path.read_text("utf-8"))  # type: ignore[no-any-return]
