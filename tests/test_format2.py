"""Template format 2: model tiers, teams, knowledge, integrations, limits and the copy path.

Library functions on their own (no model is called), then copies saved in a real workspace and run
on the runtime with a deterministic double: what the orchestrators decide is scripted, what the
engine does with the decisions (staffing, parallel teams, parameters, approvals inside teams,
limits) is the real behaviour.
"""

from __future__ import annotations

from typing import Any

from conftest import Host, Scenario, finish, instantiate, start_request
from nodestro_runtime.run_views import approvals_of_tree
from nodestro_runtime.schemas import LANGUAGES
import pytest

import nodestro_examples as library
from nodestro_examples import samples

IDS = library.template_ids()
TEAMS = {
    "business-idea": ["idea-market", "idea-economics", "idea-risks", "idea-regulation", "idea-operations"],
    "research-hypotheses": [
        "research-hypothesis-team",
        "research-statistics",
        "research-qualitative",
        "research-ethics",
    ],
    "construction-delay": [
        "construction-site",
        "construction-supply",
        "construction-claims",
        "construction-recovery",
    ],
}


# ---- models ------------------------------------------------------------------------------


def test_tiers_follow_the_workspace_provider() -> None:
    assert library.model_choice() == library.ModelChoice()
    assert library.model_choice("anthropic:claude-sonnet-5-5").of("strong") == "anthropic:claude-opus-5-5"
    other = library.model_choice("openai:gpt-test", "openai:gpt-test-large")
    assert (other.fast, other.standard, other.strong) == ("openai:gpt-test", "openai:gpt-test", "openai:gpt-test-large")
    # An assistant model of another provider is never mixed in.
    assert library.model_choice("openai:gpt-test", "anthropic:claude-opus-5-5").strong == "openai:gpt-test"


def test_a_copy_uses_the_models_of_its_workspace() -> None:
    other = library.model_choice("openai:gpt-test")
    for template_id in IDS:
        workflow = library.build(template_id, "en", models=other)
        for node in workflow.nodes:
            if node.agent is not None:
                assert node.agent.model == "openai:gpt-test", (template_id, node.id)
                assert not node.agent.server_tools
                if node.agent.quality.enabled:
                    assert node.agent.quality.judge_model == "openai:gpt-test"
            if node.orchestrator is not None:
                assert node.orchestrator.model == "openai:gpt-test"
        for part_id in library.part_ids(template_id):
            part = library.build_part(part_id, "en", models=other)
            assert {node.agent.model for node in part.nodes if node.agent} == {"openai:gpt-test"}


# ---- teams ---------------------------------------------------------------------------------


def test_orchestrated_examples_name_their_teams_and_limits() -> None:
    for template_id, teams in TEAMS.items():
        spec = library.structure(template_id)
        assert library.part_ids(template_id) == teams
        workflow = library.build(template_id, "de")
        [config] = [node.orchestrator for node in workflow.nodes if node.orchestrator is not None]
        members = [member.workflow_id for member in config.members]
        assert members == [f"{library.PART_PREFIX}{team}" for team in teams]
        # Every team is a small workflow with a clear description and capabilities for the orchestrator.
        for team in teams:
            part = library.build_part(team, "de")
            assert part.description.strip() and part.capabilities, team
        # Bounded: decisions, repetitions, budget and duration.
        assert config.max_decisions <= 8 and config.max_per_member == 2
        assert workflow.budget_usd == spec.budget_usd and workflow.limits.max_steps
        assert workflow.limits.max_duration_s and workflow.limits.max_duration_s <= 2400
        detail = library.detail(template_id, "en")
        assert detail.pattern == "adaptive" and detail.teams == len(teams)
        assert [team.part_id for team in detail.team_details] == teams
        assert any(agent.kind == "orchestrator" for agent in detail.agent_details)


def test_team_details_show_parameters_contracts_and_approvals() -> None:
    teams = {team.part_id: team for team in library.detail("research-hypotheses", "en").team_details}
    form = library.part_texts("research-statistics", "en").form
    assert teams["research-statistics"].parameters == [form[name].label for name in ("design", "alpha", "power")]
    construction = {team.part_id: team for team in library.detail("construction-delay", "en").team_details}
    assert construction["construction-claims"].approval
    assert not construction["construction-site"].approval
    assert "attributed_delay_days" in construction["construction-site"].contract


def test_copies_pin_their_parts_and_teams() -> None:
    class Recorder:
        def __init__(self) -> None:
            self.saved: list[Any] = []
            self.knowledge: list[tuple[str, str]] = []

        def save_workflow(self, workflow: Any) -> tuple[str, int | None]:
            self.saved.append(workflow)
            return f"wf_{len(self.saved)}", 1

        def add_knowledge(self, data: bytes, *, name: str, media_type: str, description: str, collection: str) -> str:
            self.knowledge.append((name, collection))
            return f"kn_{len(self.knowledge)}"

    host = Recorder()
    made = library.instantiate("construction-delay", "de", host)
    assert list(made.parts) == TEAMS["construction-delay"]
    [config] = [node.orchestrator for node in made.workflow.nodes if node.orchestrator is not None]
    assert [(member.workflow_id, member.version) for member in config.members] == [
        (f"wf_{index}", 1) for index in range(1, 5)
    ]
    assert host.knowledge == [] and made.connected == made.offline == []

    host = Recorder()
    made = library.instantiate("contract-review", "fr", host)
    assert host.saved == [] and len(host.knowledge) == 1
    _name, collection = host.knowledge[0]
    assert collection == library.common("fr").collection.replace("{name}", library.texts("contract-review", "fr").name)
    agent = next(node for node in made.workflow.nodes if node.id == "checkpoints")
    assert agent.agent is not None and agent.agent.knowledge.file_ids == ["kn_1"]


# ---- knowledge -----------------------------------------------------------------------------


@pytest.mark.parametrize("language", LANGUAGES)
def test_knowledge_files_are_synthetic_documents(language: str) -> None:
    from nodestro_runtime.file_formats import detect, extract

    for template_id in IDS:
        for item in library.structure(template_id).knowledge:
            name, media_type, data = samples.render_knowledge(template_id, item.id, language)
            assert samples.render_knowledge(template_id, item.id, language)[2] == data
            extracted = extract(name, data, spec=detect(name, data))
            assert extracted.chars > 400, (template_id, item.id)
            assert media_type and len(data) < 200_000


async def test_knowledge_is_stored_once_and_searched_with_citations(make_workspace: Any) -> None:
    workspace = make_workspace(Scenario())
    first, made = instantiate(workspace, "quality-8d", "en")
    _second, again = instantiate(workspace, "quality-8d", "en")
    # The same synthetic document keeps one knowledge file; both copies point at it.
    assert made.knowledge == again.knowledge
    [file_id] = made.knowledge.values()
    entry = workspace.knowledge.get(file_id)
    assert [item.id for item in workspace.knowledge.files()] == [file_id]
    # The search finds the precedent in the synthetic archive.
    assert workspace.knowledge.search("8D-2024-019", file_ids=[file_id])
    assert entry.collection == library.common("en").collection.replace("{name}", library.texts("quality-8d", "en").name)
    agent = next(node for node in first.nodes if node.id == "root_cause").agent
    assert agent is not None and agent.knowledge.file_ids == [file_id] and agent.knowledge.citations
    done = await finish(workspace, await workspace.run(first, start_request(first)))
    assert done.status == "succeeded", done.error


# ---- orchestration on the runtime ------------------------------------------------------


async def test_the_coordinator_staffs_a_team_and_works_in_parallel(make_workspace: Any) -> None:
    scenario = Scenario(
        decisions={
            "control": [
                {"action": "staff", "add": ["construction-site", "construction-supply"], "reason": "causes"},
                {
                    "action": "parallel",
                    "members": ["construction-site", "construction-supply"],
                    "tasks": ["Frost and design change", "Roof elements and electrician"],
                    "reason": "independent",
                },
                {"action": "finish", "answer": "Results of both teams.", "reason": "done"},
            ]
        }
    )
    workspace = make_workspace(scenario)
    workflow, made = instantiate(workspace, "construction-delay", "en")
    done = await finish(workspace, await workspace.run(workflow, start_request(workflow)))
    assert done.status == "succeeded", done.error
    record = done.nodes["control"].orchestration
    assert record is not None
    used = {made.parts[team][0] for team in ("construction-site", "construction-supply")}
    children = [workspace.runs.get(child) for child in done.nodes["control"].child_run_ids]
    assert {child.workflow_id for child in children if child} == used
    # The claims team (with its sign-off) was not needed and never ran.
    assert made.parts["construction-claims"][0] not in {child.workflow_id for child in children if child}
    steps = record["steps"]
    assert [step["decision"]["action"] for step in steps] == ["staff", "parallel", "finish"]
    assert all(not step["verdict"]["code"] for step in steps)


async def test_an_orchestrator_sets_the_parameters_of_a_team(make_workspace: Any) -> None:
    scenario = Scenario(
        decisions={
            "coordinator": [
                {"action": "delegate", "member": "research-hypothesis-team", "task": "Hypotheses", "reason": "first"},
                {
                    "action": "delegate",
                    "member": "research-statistics",
                    "task": "Sample size for the plate test",
                    "values": {"design": "Repeated measurements on the same units", "alpha": 0.01},
                    "reason": "measurable outcome",
                },
                {"action": "finish", "answer": "Hypotheses and sample size.", "reason": "done"},
            ]
        }
    )
    workspace = make_workspace(scenario)
    workflow, made = instantiate(workspace, "research-hypotheses", "en")
    done = await finish(workspace, await workspace.run(workflow, start_request(workflow)))
    assert done.status == "succeeded", done.error
    statistics = next(
        workspace.runs.get(child)
        for child in done.nodes["coordinator"].child_run_ids
        if getattr(workspace.runs.get(child), "workflow_id", None) == made.parts["research-statistics"][0]
    )
    assert statistics is not None
    prompt = statistics.nodes["expert"].prompt or ""
    assert "Repeated measurements on the same units" in prompt and "0.01" in prompt
    # The level the coordinator did not set keeps the team's default.
    assert "0.8" in prompt


async def test_a_rejected_sign_off_inside_the_claims_team_stops_the_run(make_workspace: Any) -> None:
    scenario = Scenario(
        decisions={
            "control": [
                {"action": "staff", "add": ["construction-claims"], "reason": "client-ordered design change"},
                {
                    "action": "delegate",
                    "member": "construction-claims",
                    "task": "Notice for the windows",
                    "reason": "x",
                },
                {"action": "finish", "answer": "-", "reason": "-"},
            ]
        }
    )
    workspace = make_workspace(scenario)
    workflow, _made = instantiate(workspace, "construction-delay", "en")
    run = await workspace.run(workflow, start_request(workflow))
    paused = await workspace.wait(run.id, timeout=60)
    assert paused.status == "paused" and paused.nodes["control"].status == "awaiting_approval"
    [pending] = approvals_of_tree(workspace.runs, paused)
    assert pending.node_id == "sign" and pending.root_run_id == run.id
    # Nothing is written while a person decides.
    assert workspace.files.list(run.id) == []
    workspace.decide(pending.run_id, "sign", "rejected", "The design change was never instructed in writing.")
    done = await workspace.wait(run.id, timeout=60)
    assert done.status != "succeeded"
    assert workspace.files.list(run.id) == []
    assert done.nodes["release"].status != "awaiting_approval"


async def test_the_decision_budget_ends_an_endless_coordinator(make_workspace: Any) -> None:
    looping = [{"action": "delegate", "member": "idea-market", "task": "Again", "reason": "more"}] * 20
    workspace = make_workspace(Scenario(decisions={"coach": looping}))
    workflow, _made = instantiate(workspace, "business-idea", "en")
    done = await finish(workspace, await workspace.run(workflow, start_request(workflow)))
    record = done.nodes["coach"].orchestration
    assert record is not None
    limit = next(node for node in library.structure("business-idea").nodes if node.orchestrator).orchestrator
    assert limit is not None
    # The same task twice is refused and the decision budget ends the loop: the step fails visibly
    # instead of running (and paying) forever, and nothing after it runs on a half result.
    assert len(record["steps"]) == limit.max_decisions
    assert len(done.nodes["coach"].child_run_ids) == 1
    assert {step["verdict"]["code"] for step in record["steps"][1:]} == {"orchestration.repeated"}
    assert done.status == "failed" and done.nodes["jury"].status == "blocked"


# ---- integrations -------------------------------------------------------------------------

ERP = {"list_suppliers": "mcp__erp_demo__list_suppliers", "supplier_scorecard": "mcp__erp_demo__supplier_scorecard"}


def offered(access: str = "read", approved: bool = True, skip: str = "") -> dict[str, library.ServerTool]:
    return {
        name: library.ServerTool(agent_name=agent, approved=approved, access=access)
        for name, agent in ERP.items()
        if name != skip
    }


def test_an_integration_needs_approved_read_only_tools() -> None:
    assert library.connect("supplier-comparison", "erp", offered()) == ERP
    with pytest.raises(library.IntegrationProblem) as missing:
        library.connect("supplier-comparison", "erp", offered(skip="supplier_scorecard"))
    assert missing.value.missing == ["supplier_scorecard"]
    with pytest.raises(library.IntegrationProblem) as unapproved:
        library.connect("supplier-comparison", "erp", offered(approved=False))
    assert unapproved.value.missing == ["list_suppliers", "supplier_scorecard"]
    for access in ("write", "destructive"):
        with pytest.raises(library.IntegrationProblem) as writing:
            library.connect("supplier-comparison", "erp", offered(access=access))
        assert writing.value.not_read_only == ["list_suppliers", "supplier_scorecard"]
    with pytest.raises(KeyError):
        library.connect("supplier-comparison", "shop", offered())


@pytest.mark.parametrize("language", LANGUAGES)
def test_connected_and_offline_copies_say_what_they_use(language: str) -> None:
    text = library.texts("supplier-comparison", language)
    offline = library.build("supplier-comparison", language)
    online = library.build("supplier-comparison", language, connections={"erp": ERP})
    risk_offline = next(node.agent for node in offline.nodes if node.id == "risk")
    risk_online = next(node.agent for node in online.nodes if node.id == "risk")
    assert risk_offline is not None and risk_online is not None
    assert not any(tool.startswith("mcp__") for tool in risk_offline.tools)
    assert set(ERP.values()) <= set(risk_online.tools)
    assert text.agents["risk"].offline.strip() in risk_offline.system_prompt
    assert text.agents["risk"].online.strip() in risk_online.system_prompt
    assert text.agents["risk"].online.strip() not in risk_offline.system_prompt
    # The copy's description says which mode it is in: offline never pretends a connection.
    assert text.integrations["erp"].offline.strip() in offline.description
    assert text.integrations["erp"].online.strip() in online.description
    detail = library.detail("supplier-comparison", language)
    assert [item.tools for item in detail.integrations] == [["list_suppliers", "supplier_scorecard"]]


def test_unknown_connections_are_refused() -> None:
    with pytest.raises(KeyError):
        library.instantiate("blog-article", "en", Host(None), connections={"erp": ERP})  # type: ignore[arg-type]
