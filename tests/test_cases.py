"""The prepared test cases, decisions and approvals of the examples, executed on the runtime.

A test case becomes a test series of a copy (:func:`nodestro_examples.samples.suite_cases`); the
API runs its cases and evaluates the checks with :func:`nodestro_runtime.conditions.evaluate`. These
tests do the same without the API: every case of every template runs in every language with a
model double that answers like a model that solved the case (``SCENARIOS``: the reference values
of the prepared data). That proves the checks name existing results and hold for a correct
answer; the empty double proves they fail for a useless one. Real model quality is not tested here.
"""

from __future__ import annotations

from typing import Any

from conftest import Scenario, copy, finish, start_request
from nodestro_runtime.conditions import evaluate, parse_result
from nodestro_runtime.graph import data_sources
from nodestro_runtime.problems import NodestroError
from nodestro_runtime.reports import file_name
from nodestro_runtime.schemas import LANGUAGES, ConditionRule, RunIn, Workflow
from nodestro_runtime.workspace import Workspace
import pytest

import nodestro_examples as library
from nodestro_examples import samples

IDS = library.template_ids()
CASES = [(template_id, case.id) for template_id in IDS for case in library.structure(template_id).tests]

#: What a model that solved a case answers, where the checks look at it (node id -> fields or text).
SCENARIOS: dict[tuple[str, str], dict[str, Any]] = {
    # 665 of 14,400 planned minutes are 4.62 %; the quiet fortnight has 205 minutes (1.42 %).
    ("production-downtime", "above_target"): {"downtime": {"downtime_share_percent": 4.62}},
    ("production-downtime", "within_target"): {"downtime": {"downtime_share_percent": 1.42}},
    ("production-downtime", "log_file"): {"downtime": {"downtime_share_percent": 4.62}},
    ("quality-8d", "complaint_text"): {"problem": {"critical": True}},
    ("quality-8d", "complaint_files"): {"problem": {"critical": True}},
    ("customer-service", "calm_request"): {"triage": {"escalation": False}},
    ("code-review", "snippet"): {"fix": "def test_coupon_never_below_zero():\n    ..."},
    ("code-review", "project_zip"): {"fix": "def test_find_orders_is_parameterised():\n    ..."},
    ("contract-review", "balanced_contract"): {"checkpoints": {"critical_count": 0}},
    # Income 4,605 minus 4,142 spending (annual items per month) leaves 463; the March export 460.
    ("household-budget", "budget_text"): {"check": {"monthly_surplus": 463, "savings_potential": 150}},
    ("household-budget", "transactions_file"): {"check": {"monthly_surplus": 460, "savings_potential": 150}},
    ("business-idea", "idea"): {"jury": {"score": 6}},
    ("farm-planning", "farm_text"): {"review": {"total_margin_eur": 41210}},
    ("farm-planning", "field_file"): {"review": {"total_margin_eur": 41210}},
}


def stored_cases(workspace: Workspace, template_id: str, language: str, workflow: Workflow) -> list[dict[str, Any]]:
    def store(name: str, media_type: str, data: bytes) -> str:
        return workspace.inputs.add(data, name=name, media_type=media_type, origin="test").id

    return samples.suite_cases(template_id, language, workflow, store)


async def run_case(workspace: Workspace, workflow: Workflow, case: dict[str, Any]) -> Any:
    workspace.fake.learn(workflow)  # type: ignore[attr-defined]
    run = await workspace.run(workflow, RunIn(input=case["input"], values=case["values"]))
    # Approved without a comment: a comment becomes part of the run's result (see the README).
    return await finish(workspace, run, comment="")


def results(case: dict[str, Any], output: Any) -> list[bool | None]:
    parsed = parse_result(output)
    return [evaluate(ConditionRule.model_validate(check), parsed) for check in case["checks"]]


# ---- the test cases ---------------------------------------------------------------


def test_the_cases_are_complete_and_their_checks_name_existing_results() -> None:
    assert len(CASES) >= 45
    assert set(SCENARIOS) <= set(CASES)
    for template_id in IDS:
        spec = library.structure(template_id)
        workflow = library.build(template_id, "en")
        output = next(node.id for node in spec.nodes if node.type == "output")
        sources = data_sources(workflow, output)
        nodes = {node.id: node for node in spec.nodes}
        for case in spec.tests:
            assert case.checks, (template_id, case.id)
            for check in case.checks:
                node_id = check.node or (sources[0] if len(sources) == 1 else None)
                if node_id is None:
                    # Several results can arrive: without a node a check can only look at the whole result.
                    assert check.field == "", (template_id, case.id, check)
                    continue
                assert node_id in sources, (template_id, case.id, check)
                fields = {field.name for field in nodes[node_id].output_fields}
                assert check.field in fields | {""}, (template_id, case.id, check)
                assert ConditionRule(id="c", field=check.field, operator=check.operator, value=check.value)
            used = {sample for sample in case.samples}
            assert used <= {sample.id for sample in spec.samples}, (template_id, case.id)
        # Every sample file is used by at least one case.
        assert {sample.id for sample in spec.samples} <= {item for case in spec.tests for item in case.samples}


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize(("template_id", "case_id"), CASES)
async def test_every_case_passes_its_checks_for_a_correct_answer(
    make_workspace: Any, template_id: str, case_id: str, language: str
) -> None:
    workspace = make_workspace(Scenario(SCENARIOS.get((template_id, case_id))))
    workflow = copy(workspace, template_id, language)
    ids = [case.id for case in library.structure(template_id).tests]
    case = stored_cases(workspace, template_id, language, workflow)[ids.index(case_id)]
    assert case["name"].strip() and (case["input"].strip() or case["values"])
    for value in case["values"].values():
        if isinstance(value, list):
            # Sample files are stored once as input files of the copy and kept.
            assert all(workspace.inputs.get(file_id) is not None for file_id in value)
    done = await run_case(workspace, workflow, case)
    assert done.status == "succeeded", (template_id, case_id, language, done.error)
    assert results(case, done.output) == [True] * len(case["checks"]), (template_id, case_id, language, done.output)
    # The files of the case reach the agents that read the input.
    files = [item for value in case["values"].values() if isinstance(value, list) for item in value]
    for node in workflow.nodes:
        if files and node.agent is not None and "start" in data_sources(workflow, node.id):
            assert {item.file_id for item in done.nodes[node.id].files} == set(files), (template_id, node.id)


@pytest.mark.parametrize(("template_id", "case_id"), CASES)
async def test_no_case_passes_with_an_empty_answer(make_workspace: Any, template_id: str, case_id: str) -> None:
    """A check that also holds for an empty result proves nothing; every case has one that does not."""
    workspace = make_workspace(Scenario(empty=True))
    workflow = copy(workspace, template_id, "en")
    ids = [case.id for case in library.structure(template_id).tests]
    case = stored_cases(workspace, template_id, "en", workflow)[ids.index(case_id)]
    done = await run_case(workspace, workflow, case)
    assert done.status == "succeeded", (template_id, case_id, done.error)
    assert False in results(case, done.output), (template_id, case_id, done.output)


def test_copies_share_sample_files_between_cases(make_workspace: Any) -> None:
    workspace = make_workspace()
    workflow = copy(workspace, "real-estate", "de")
    stored: list[str] = []

    def store(name: str, media_type: str, data: bytes) -> str:
        stored.append(name)
        return workspace.inputs.add(data, name=name, media_type=media_type, origin="test").id

    samples.suite_cases("real-estate", "de", workflow, store)
    samples.suite_cases("quality-8d", "de", copy(workspace, "quality-8d", "de"), store)
    assert len(stored) == len(set(stored)) == 4


# ---- decisions -----------------------------------------------------------------------


def _hit_and_miss(operator: str, value: Any) -> tuple[Any, Any]:
    """A value that satisfies a rule and one that does not."""
    if operator == "is_true":
        return True, False
    if operator == "is_false":
        return False, True
    if operator == "gt":
        return value + 1, value
    raise AssertionError(f"no values for {operator}")  # pragma: no cover - a new kind of rule


DECISIONS = [
    (template_id, node.id) for template_id in IDS for node in library.structure(template_id).nodes if node.condition
]


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize(("template_id", "node_id"), DECISIONS)
async def test_every_decision_opens_its_branch_and_its_default(
    make_workspace: Any, template_id: str, node_id: str, language: str
) -> None:
    spec = library.structure(template_id)
    decision = next(node for node in spec.nodes if node.id == node_id).condition
    assert decision is not None and len(decision.rules) == 1 and decision.source
    rule = decision.rules[0]
    branch = [edge[1] for edge in spec.edges if edge[0] == node_id and edge[2:] == (rule.id,)]
    assert branch, (template_id, node_id)
    for value, expected in zip(_hit_and_miss(rule.operator, rule.value), (rule.id, "default"), strict=True):
        answers = {} if decision.source == "start" else {decision.source: {rule.field: value}}
        workspace = make_workspace(Scenario(answers))
        workflow = copy(workspace, template_id, language)
        workspace.fake.learn(workflow)
        request = start_request(workflow)
        if decision.source == "start":
            request.values[rule.field] = value
        done = await finish(workspace, await workspace.run(workflow, request))
        assert done.status == "succeeded", (template_id, language, expected, done.error)
        record = done.nodes[node_id].decision
        assert record is not None and record.branches == [expected], (template_id, language, record)
        statuses = {done.nodes[target].status for target in branch}
        assert statuses == ({"succeeded"} if expected == rule.id else {"skipped"}), (template_id, expected)
        # Agents after the branch are told when it did not run, instead of seeing a placeholder.
        for node in workflow.nodes:
            if node.agent is not None and done.nodes[node.id].status == "succeeded":
                assert "{{" not in (done.nodes[node.id].prompt or ""), (template_id, node.id)


# ---- approvals -----------------------------------------------------------------------

APPROVALS = [
    (template_id, node.id)
    for template_id in IDS
    for node in library.structure(template_id).nodes
    if node.type == "approval"
]


@pytest.mark.parametrize(("template_id", "node_id"), APPROVALS)
async def test_an_approval_releases_the_result_files(make_workspace: Any, template_id: str, node_id: str) -> None:
    workspace = make_workspace()
    workflow = copy(workspace, template_id, "en")
    run = await workspace.run(workflow, start_request(workflow))
    paused = await workspace.wait(run.id, timeout=60)
    assert paused.status == "paused" and paused.nodes[node_id].status == "awaiting_approval"
    # Nothing is written while the result waits for a person.
    assert workspace.files.list(run.id) == []
    done = await finish(workspace, paused)
    assert done.status == "succeeded"
    output = next(node for node in workflow.nodes if node.type == "output")
    wanted = [spec.format for spec in output.output.files] if output.output else []
    written = workspace.files.list(run.id)
    assert sorted(entry.format for entry in written) == sorted(wanted)
    assert all(entry.error_code is None and entry.size > 0 for entry in written)


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize(("template_id", "node_id"), APPROVALS)
async def test_a_rejection_stops_or_revises_as_configured(
    make_workspace: Any, template_id: str, node_id: str, language: str
) -> None:
    spec = next(node for node in library.structure(template_id).nodes if node.id == node_id).approval
    assert spec is not None
    workspace = make_workspace()
    workflow = copy(workspace, template_id, language)
    run = await workspace.run(workflow, start_request(workflow))
    paused = await workspace.wait(run.id, timeout=60)
    assert paused.nodes[node_id].status == "awaiting_approval"
    if spec.require_comment_on_reject:
        with pytest.raises(NodestroError) as refused:
            workspace.decide(run.id, node_id, "rejected", "  ")
        assert refused.value.code == "approval.comment_required"
    comment = "Please name the delivery date."
    workspace.decide(run.id, node_id, "rejected", comment)
    done = await workspace.wait(run.id, timeout=60)
    edges = library.structure(template_id).edges
    loops = [edge[1] for edge in edges if edge[0] == node_id and edge[2:3] == ("rejected",) and len(edge) == 4]
    if loops:
        # A loop sends the drafts back: they are revised with the comment and wait for approval again.
        assert done.status == "paused" and done.nodes[node_id].status == "awaiting_approval"
        assert done.nodes[node_id].iteration == [1]
        for target in loops:
            assert done.nodes[target].iteration == [1] and comment in (done.nodes[target].prompt or "")
        workspace.decide(run.id, node_id, "approved", "")
        done = await workspace.wait(run.id, timeout=60)
        assert done.status == "succeeded", (template_id, done.error)
        return
    # A decided approval cannot be decided again.
    with pytest.raises(NodestroError):
        workspace.decide(run.id, node_id, "approved", "")
    revisers = [edge[1] for edge in edges if edge[0] == node_id and edge[2:] == ("rejected",)]
    if spec.on_reject == "stop":
        assert not revisers
        assert done.status != "succeeded" and done.error_code == "run.approval_rejected", (template_id, done.status)
        assert workspace.files.list(run.id) == []
    else:
        assert revisers and done.status == "succeeded"
        for target in revisers:
            assert done.nodes[target].status == "succeeded"
            assert comment in (done.nodes[target].prompt or "")


# ---- result files ----------------------------------------------------------------------

_MAGIC = {"pdf": b"%PDF-", "docx": b"PK\x03\x04", "xlsx": b"PK\x03\x04"}


@pytest.mark.parametrize("template_id", IDS)
async def test_result_files_are_written_in_the_configured_formats(make_workspace: Any, template_id: str) -> None:
    workspace = make_workspace()
    workflow = copy(workspace, template_id, "fr")
    done = await finish(workspace, await workspace.run(workflow, start_request(workflow)))
    assert done.status == "succeeded"
    output = next(node for node in workflow.nodes if node.type == "output")
    for entry in workspace.files.list(done.id):
        _info, data = workspace.files.content(done.id, entry.id)
        assert data.startswith(_MAGIC.get(entry.format, b"")), (template_id, entry.name)
        if entry.format in ("md", "html"):
            data.decode("utf-8")
        name = library.texts(template_id, "fr").file_name or library.texts(template_id, "fr").name
        assert entry.name == file_name(name, "result", entry.format), (template_id, entry.name)
    assert len(workspace.files.list(done.id)) == len(output.output.files if output.output else [])
