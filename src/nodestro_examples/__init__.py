"""The example library: multi-agent workflow templates in every interface language.

This is the package ``nodestro-examples``. Nodestro reads the library only through the
functions of this module (:func:`summaries`, :func:`detail`, :func:`build`, :func:`build_part`,
:func:`link_parts`, :func:`structure`, :func:`texts` and :mod:`.samples`); the files are package
data of the installed package, never a path into a source checkout.

A template is data, kept in two kinds of files in this package:

- ``templates/<id>.json`` holds the language-neutral structure: nodes, models, tools,
  connections, output fields and quality criteria.
- ``texts/<language>/<id>.json`` holds everything a person reads: name, description,
  agent names, system prompts, tasks, the prepared test input and the guide.
  ``texts/<language>/_common.json`` adds the rules every system prompt ends with.

Templates are never changed at runtime and never installed on their own. Copying one
(``POST /api/library/{id}/copy``) builds an ordinary workflow in the chosen language;
the copy has its own id and is saved, versioned and edited like any other workflow, so
later changes or language switches never touch the template or other copies.

In a task text ``{{node:<id>}}`` names the result of another node; it becomes the
placeholder of that node's name in the respective language (``{{Root cause analyst}}``).

Templates can use every kind of node: decisions (``condition``), approvals, input forms on
the start node (file fields with accepted formats, limits and delivery mode), result files on
the result node, knowledge proposals and memory on agents, and sub-workflows. Every setting is
an ordinary workflow setting: a copy needs nothing that exists only for the gallery. A sub-workflow node
names a *part* (``templates/parts/<id>.json`` with texts in ``texts/<language>/parts``):
a small workflow that is not an example of its own. Copying the template copies the
part as a separate workflow first and pins the sub-workflow node to that copy's first
version, so the copy works on its own and the template stays untouched.

Sample files (``samples``) are small synthetic files for the file fields of a template. They
are built on request from the texts of a language with the writers result files use
(:mod:`nodestro_runtime.office`, :mod:`nodestro_runtime.reports`), or read from ``samples/`` for files without
text (an image), so no large binary data lives in the templates (see :mod:`.samples`). Test
cases (``tests``) describe a test series with checks on the result; copying a template can
create it for the copy, with the sample files stored as the copy's input files.
"""

from __future__ import annotations

from functools import cache
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import re
from typing import Any, Literal

from nodestro_runtime.schemas import (
    LANGUAGES,
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
    KnowledgeProposalConfig,
    MemoryConfig,
    Node,
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
)
from pydantic import BaseModel, Field, model_validator

try:
    __version__ = version("nodestro-examples")
except PackageNotFoundError:  # pragma: no cover - running from a source checkout
    __version__ = "0.0.0"

#: The version of the template format (``templates/``, ``texts/``); it changes only when existing
#: templates would no longer be read correctly. The studio refuses a library with another format.
FORMAT_VERSION = 1
#: The package data (templates, texts, sample files) inside the installed package.
_ROOT = Path(__file__).parent
_NODE_REF = re.compile(r"\{\{\s*node:([a-z0-9_]+)\s*\}\}")
FALLBACK_LANGUAGE = "en"

Category = Literal["industry", "business", "customers", "knowledge", "administration", "private"]
#: The categories in the order the gallery shows them.
CATEGORIES: tuple[str, ...] = ("industry", "business", "customers", "knowledge", "administration", "private")
Role = Literal["research", "analysis", "planning", "review", "writing"]
Level = Literal["beginner", "advanced"]
Pattern = Literal["sequential", "parallel", "branching"]
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
]
#: The prefix of a sub-workflow id that names a part of the library (resolved when copying).
PART_PREFIX = "library-part:"

#: The judge of the built-in quality check; Sonnet keeps the examples affordable.
JUDGE_MODEL = "claude-sonnet-5-5"


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


class NodeSpec(_Strict):
    id: str
    type: Literal["start", "agent", "output", "condition", "approval", "subworkflow"]
    x: float
    y: float
    role: Role | None = None
    icon: str = "bot"
    model: str = "claude-sonnet-5-5"
    effort: Effort | None = "medium"
    tools: list[str] = Field(default_factory=list)
    max_tokens: int = 8000
    output_name: str = "Result"
    output_fields: list[FieldSpec] = Field(default_factory=list)
    criteria: list[str] = Field(default_factory=list)
    max_revisions: int = 1
    condition: ConditionSpec | None = None
    approval: ApprovalSpec | None = None
    #: The part this sub-workflow node runs.
    part: str | None = None
    #: Start node: the input form.
    form: list[InputSpec] = Field(default_factory=list)
    #: Result node: the files it writes.
    files: list[ReportFormat | FileSpec] = Field(default_factory=list)
    #: Agents: propose the result for knowledge (what it is); a person always decides.
    proposals: ContentKind | None = None
    #: Agents: persistent memory.
    memory: MemorySpec | None = None


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


class PartSpec(_Strict):
    """A small workflow used as a sub-workflow by templates; not an example of its own."""

    id: str
    nodes: list[NodeSpec]
    edges: list[Connection]

    @model_validator(mode="after")
    def _valid_graph(self) -> PartSpec:
        problems = _graph_problems(self.nodes, self.edges)
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
    nodes: list[NodeSpec]
    edges: list[Connection]
    samples: list[SampleSpec] = Field(default_factory=list)
    tests: list[CaseSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _valid_references(self) -> TemplateSpec:
        problems = _graph_problems(self.nodes, self.edges)
        fields = {field.name: field for node in self.nodes for field in node.form}
        nodes = {node.id for node in self.nodes}
        samples = {sample.id for sample in self.samples}
        for sample in self.samples:
            if sample.field not in fields or fields[sample.field].type != "file":
                problems.append(f"sample {sample.id} names no file field ({sample.field})")
        if len(samples) != len(self.samples) or len({case.id for case in self.tests}) != len(self.tests):
            problems.append("sample or test case ids are not unique")
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


class Guide(BaseModel):
    """What the gallery and the documentation explain about one example."""

    problem: str
    flow: str
    input: str
    result: str
    adapt: str


class StepTexts(_Strict):
    """Texts of a decision, approval or sub-workflow node."""

    name: str
    instructions: str = ""
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
    samples: dict[str, SampleTexts] = Field(default_factory=dict)
    tests: dict[str, CaseTexts] = Field(default_factory=dict)


class PartTexts(_Strict):
    name: str
    description: str
    start: str
    output: str
    agents: dict[str, NodeTexts]


class CommonTexts(_Strict):
    language: str
    answer: str
    transparency: str
    caution: str
    #: For agents that receive the files of a form's file fields.
    files: str


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
    rules: CommonTexts,
    sensitive: bool,
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
            files = (
                OutputNodeConfig(
                    files=[ResultFileSpec(format=spec.format, name=file_name, sanitize=spec.sanitize) for spec in specs]
                )
                if specs
                else None
            )
            nodes.append(Node(id=item.id, type="output", label=output_label, position=position, output=files))
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
                judge_model=JUDGE_MODEL,
            )
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
                    model=item.model,
                    system_prompt=_system_prompt(own.system, rules, sensitive=sensitive, files=item.id in with_files),
                    task_template=task(own.task),
                    tools=list(item.tools),
                    effort=item.effort,
                    max_tokens=item.max_tokens,
                    output=output,
                    quality=quality,
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


def build(template_id: str, language: str) -> WorkflowIn:
    """The workflow a template describes, in one language (a fresh object every time).

    Sub-workflow nodes name their part as ``library-part:<id>`` until a copy resolves them.
    """
    spec = structure(template_id)
    text = texts(template_id, language)
    nodes, edges = _build_nodes(
        spec.nodes,
        spec.edges,
        start_label=text.start,
        output_label=text.output,
        default_input=text.input,
        agents=text.agents,
        steps=text.steps,
        form=text.form,
        rules=common(language),
        sensitive=spec.sensitive,
        file_name=text.file_name,
    )
    return WorkflowIn(name=text.name, description=text.description, nodes=nodes, edges=edges)


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
    """The parts a template's sub-workflow nodes run."""
    return list(dict.fromkeys(node.part for node in structure(template_id).nodes if node.part))


def build_part(part_id: str, language: str, *, sensitive: bool = False) -> WorkflowIn:
    spec = part(part_id)
    text = part_texts(part_id, language)
    nodes, edges = _build_nodes(
        spec.nodes,
        spec.edges,
        start_label=text.start,
        output_label=text.output,
        default_input="",
        agents=text.agents,
        steps={},
        form={},
        rules=common(language),
        sensitive=sensitive,
    )
    return WorkflowIn(name=text.name, description=text.description, nodes=nodes, edges=edges)


def link_parts(workflow: WorkflowIn, copies: dict[str, tuple[str, int | None]]) -> WorkflowIn:
    """Point the sub-workflow nodes at the copies of their parts (part id -> workflow id, version)."""
    for node in workflow.nodes:
        if node.subworkflow is not None and node.subworkflow.workflow_id.startswith(PART_PREFIX):
            workflow_id, version = copies[node.subworkflow.workflow_id[len(PART_PREFIX) :]]
            node.subworkflow.workflow_id = workflow_id
            node.subworkflow.version = version
    return workflow


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
    #: The workflow exactly as a copy would get it; shown read-only.
    workflow: WorkflowIn


def _pattern(spec: TemplateSpec) -> Pattern:
    """Parallel when two agents can work at the same time: neither depends on the other."""
    if any(node.type == "condition" for node in spec.nodes):
        return "branching"
    agents = [node.id for node in spec.nodes if node.type == "agent"]
    successors: dict[str, list[str]] = {}
    for edge in spec.edges:
        if not _is_loop(edge):
            successors.setdefault(edge[0], []).append(edge[1])

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


def _features(spec: TemplateSpec) -> list[Feature]:
    agents = [node for node in spec.nodes if node.type == "agent"]
    found: list[Feature] = []
    if any(node.tools for node in agents):
        found.append("tools")
    if any(node.output_fields for node in agents):
        found.append("structured")
    if any(node.criteria for node in agents):
        found.append("judge")
    if any(node.role == "review" for node in agents):
        found.append("review")
    types = {node.type for node in spec.nodes}
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
    return found


def summary(template_id: str, language: str) -> TemplateSummary:
    spec = structure(template_id)
    text = texts(template_id, language)
    agents = [node for node in spec.nodes if node.type == "agent"]
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
        agents=len(agents),
        features=_features(spec),
        tools=sorted({tool for node in agents for tool in node.tools}),
    )


def summaries(language: str) -> list[TemplateSummary]:
    return [summary(template_id, language) for template_id in template_ids()]


def detail(template_id: str, language: str) -> TemplateDetail:
    spec = structure(template_id)
    text = texts(template_id, language)
    workflow = build(template_id, language)
    labels = {node.id: node.label for node in workflow.nodes}
    agents = []
    for item in spec.nodes:
        if item.type != "agent":
            continue
        own = text.agents[item.id]
        agents.append(
            TemplateAgent(
                node_id=item.id,
                name=own.name,
                description=own.description,
                role=item.role,
                model=item.model,
                tools=list(item.tools),
                structured=bool(item.output_fields),
                judge=bool(item.criteria),
                receives=[labels[edge[0]] for edge in spec.edges if edge[1] == item.id],
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
